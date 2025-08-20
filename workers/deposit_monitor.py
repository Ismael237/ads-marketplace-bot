from __future__ import annotations

import time
from decimal import Decimal

from bot.keyboards import transaction_details_inline_keyboard
from database.models import UserWallet
from utils.crypto import decrypt_text
from utils.tron_client import get_trx_transactions, send_trx, get_main_wallet
from utils.helpers import get_utc_time, escape_markdown_v2, format_trx_escaped
from utils.logger import get_logger
from bot.utils import safe_notify_user
from config import DEPOSIT_TO_MAIN_WALLET_RATE, TELEGRAM_ADMIN_ID
from services.wallet_service import WalletService

logger = get_logger("deposit_monitor")


def forward_deposit_to_main_wallet(wallet: UserWallet, amount: Decimal, deposit_tx_id: str) -> None:
    """Forward a proportion of a user's deposit to the main wallet."""
    try:
        encrypted_key = wallet.private_key_encrypted
        # Decrypt the private key and convert to hex string expected by tron_client
        private_key = decrypt_text(encrypted_key)

        main_wallet_address, _ = get_main_wallet()
        if not main_wallet_address:
            logger.error("[Deposit] Main wallet address not configured.")
            return

        # Calculate amount to forward according to configurable rate
        amount_to_send = (amount * Decimal(str(DEPOSIT_TO_MAIN_WALLET_RATE))).quantize(Decimal('0.000001'))
        if amount_to_send <= 0:
            logger.warning("[Deposit] Calculated amount to send to main wallet is zero, skipping.")
            return
        tx_id = send_trx(private_key, main_wallet_address, amount_to_send)
        if tx_id:
            logger.info(f"[Deposit] {amount_to_send} TRX sent to main wallet {main_wallet_address} (tx {tx_id})")
            msg = (
                f"✅ *Forwarded {format_trx_escaped(amount_to_send)} TRX\\.*\n"
                f"From deposit\\:\n\n" 
                f"`{escape_markdown_v2(deposit_tx_id)}`\n\n"
                f"to main wallet\\.\n\n"
                f"TX\\: `{escape_markdown_v2(tx_id)}`"
            )
            safe_notify_user(TELEGRAM_ADMIN_ID, msg, reply_markup=transaction_details_inline_keyboard(tx_id))
    except Exception as e:
        logger.error(f"[Deposit] Error forwarding deposit to main wallet: {e}")
        try:
            msg = (
                f"❌ *{format_trx_escaped(amount)} from deposit {escape_markdown_v2(deposit_tx_id)} to main wallet failed*\\.\n"
                f"From deposit\\:\n\n"
                f"`{escape_markdown_v2(deposit_tx_id)}`\n\n"
                f"Error\\: {escape_markdown_v2(str(e))}"
            )
            safe_notify_user(TELEGRAM_ADMIN_ID, msg)
        except Exception:
            pass


def monitor_deposits():
    logger.info("[Worker] Monitoring TRON deposits started.")
    try:
        wallets = WalletService.list_wallets()
        for wallet in wallets:
            time.sleep(0.2)
            txs = get_trx_transactions(wallet.address)
            for tx in txs:
                amount = Decimal(tx['amount']) / Decimal('1000000')
                confirmations = tx.get('confirmations', 0)
                dep, credited_now = WalletService.upsert_deposit_and_credit_if_confirmed(
                    user_id=wallet.user_id,
                    wallet_id=wallet.id,
                    tx_hash=tx['txID'],
                    amount_trx=amount,
                    confirmations=confirmations,
                    now=get_utc_time(),
                )
                if credited_now:
                    user = WalletService.get_user_by_id(wallet.user_id)
                    if user:
                        logger.info(f"[Deposit] {amount} TRX credited to user {user.id} (tx {tx['txID']})")
                        msg = f"💰 *Deposit of {format_trx_escaped(amount)} TRX confirmed*\\.\n"
                        msg += f"TX\\: `{escape_markdown_v2(tx['txID'])}`"
                        safe_notify_user(user.telegram_id, msg, reply_markup=transaction_details_inline_keyboard(tx['txID']))

                        forward_deposit_to_main_wallet(wallet, amount, tx['txID'])
    except Exception as e:
        logger.error(f"[Deposit] Error: {e}")
        try:
            # best-effort notification if we have context
            if 'user' in locals() and 'amount' in locals():
                msg = f"❌ *Deposit of {format_trx_escaped(amount)} TRX failed*\\.\nError\\: {escape_markdown_v2(str(e))}"
                safe_notify_user(user.telegram_id, msg)
        except Exception:
            pass


def run_deposit_monitor():
    try:
        monitor_deposits()
    except Exception as exc:
        logger.error(f"run_deposit_monitor failed: {exc}")