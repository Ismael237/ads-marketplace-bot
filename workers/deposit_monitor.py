from __future__ import annotations

import time
from decimal import Decimal

from bot.keyboards import transaction_details_inline_keyboard
from database.database import get_db_session
from database.models import (
    UserWallet,
    Deposit,
    DepositStatus,
    User,
    Transaction,
    TransactionType,
    BalanceType,
)
from utils.crypto import decrypt_text
from utils.tron_client import get_trx_transactions, send_trx, get_main_wallet
from utils.helpers import get_utc_time, escape_markdown_v2, format_trx_escaped
from utils.logger import get_logger
from bot.utils import safe_notify_user
from config import DEPOSIT_TO_MAIN_WALLET_RATE, TELEGRAM_ADMIN_ID


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
    call_count = 0
    with get_db_session() as session:
        try:
            wallets = session.query(UserWallet).all()
            for wallet in wallets:
                call_count += 1
                if call_count % 10 == 0:  # Every 10th call
                    time.sleep(1.2)  # Sleep for 1.2 seconds
                txs = get_trx_transactions(wallet.address)
                for tx in txs:
                    exists = session.query(Deposit).filter_by(tx_hash=tx['txID']).first()
                    if not exists:
                        amount = Decimal(tx['amount']) / Decimal('1000000')
                        deposit = Deposit(
                            user_id=wallet.user_id,
                            wallet_id=wallet.id,
                            tx_hash=tx['txID'],
                            amount_trx=amount,
                            confirmations=tx.get('confirmations', 0),
                            status=DepositStatus.confirmed if tx.get('confirmations', 0) >= 19 else DepositStatus.pending,
                            created_at=get_utc_time(),
                            confirmed_at=get_utc_time() if tx.get('confirmations', 0) >= 19 else None
                        )
                        session.add(deposit)
                        if deposit.status == DepositStatus.confirmed:
                            user = session.query(User).get(wallet.user_id)
                            # Credit advertiser balance on deposit
                            user.ad_balance += amount
                            session.add(Transaction(
                                user_id=user.id,
                                type=TransactionType.deposit,
                                amount_trx=amount,
                                balance_type=BalanceType.ad_balance,
                                description=f"Deposit {tx['txID']}",
                                reference_id=tx['txID']
                            ))
                            session.commit()
                            logger.info(f"[Deposit] {amount} TRX credited to user {user.id} (tx {tx['txID']})")
                            # Telegram notification
                            msg = f"💰 *Deposit of {format_trx_escaped(amount)} TRX confirmed*\\.\n"
                            msg += f"TX\\: `{escape_markdown_v2(tx['txID'])}`"
                            safe_notify_user(user.telegram_id, msg, reply_markup=transaction_details_inline_keyboard(tx['txID']))

                            forward_deposit_to_main_wallet(wallet, amount, tx['txID'])
            session.commit()
        except Exception as e:
            logger.error(f"[Deposit] Error: {e}")
            try:
                # best-effort notification if we have context
                if 'user' in locals() and 'amount' in locals():
                    msg = f"❌ *Deposit of {format_trx_escaped(amount)} TRX failed*\\.\nError\\: {escape_markdown_v2(str(e))}"
                    safe_notify_user(user.telegram_id, msg)
            except Exception:
                pass
            session.rollback()


def run_deposit_monitor():
    try:
        monitor_deposits()
    except Exception as exc:
        logger.error(f"run_deposit_monitor failed: {exc}")