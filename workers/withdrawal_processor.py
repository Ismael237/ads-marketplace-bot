from __future__ import annotations

from decimal import Decimal

from bot.keyboards import transaction_details_inline_keyboard
from utils.tron_client import send_trx
from utils.helpers import escape_markdown_v2, format_trx_escaped
from utils.logger import get_logger
from bot.utils import safe_notify_user
from config import TRON_PRIVATE_KEY, WITHDRAWAL_FEE_RATE
from services.wallet_service import WalletService

logger = get_logger("withdrawal_processor")


def process_withdrawals():
    logger.info("[Worker] Processing pending withdrawals started.")
    try:
        withdrawals = WalletService.fetch_pending_withdrawals()
        for wd in withdrawals:
            user = WalletService.get_user_by_id(wd.user_id)
            if not user:
                continue
            # Balance was already deducted at request time; here we just attempt sending and mark status
            tx_hash = None
            try:
                fee_rate = Decimal(str(WITHDRAWAL_FEE_RATE))
                amount_fee = Decimal(wd.amount_trx) * fee_rate
                amount_to_send = (Decimal(wd.amount_trx) - amount_fee).quantize(Decimal('0.000001'))
                tx_hash = send_trx(TRON_PRIVATE_KEY, wd.to_address, amount_to_send)
                WalletService.mark_withdrawal_completed(wd.id, tx_hash)
                logger.info(f"[Withdrawal] {wd.amount_trx} TRX({amount_to_send} TRX) sent to {wd.to_address} (user {user.id}, tx {tx_hash})")
                # Telegram notification
                msg = f"✅ *Withdrawal of {format_trx_escaped(wd.amount_trx)} TRX processed successfully\\.*\n"
                msg += f"TX\\: `{escape_markdown_v2(tx_hash)}`"
                safe_notify_user(user.telegram_id, msg, reply_markup=transaction_details_inline_keyboard(tx_hash))
            except Exception as e:
                WalletService.mark_withdrawal_failed(wd.id, str(e))
                logger.error(f"[Withdrawal] TRX send error: {e}")
                msg = f"❌ *Withdrawal of {format_trx_escaped(wd.amount_trx)} failed\\.*\n"
                if tx_hash:
                    msg += f"TX\\: `{escape_markdown_v2(tx_hash)}`\n"
                msg += f"Error\\: {escape_markdown_v2(str(e))}\n"
                safe_notify_user(user.telegram_id, msg)
    except Exception as e:
        logger.error(f"[Withdrawal] Error: {e}")
        try:
            if 'wd' in locals() and 'user' in locals():
                msg = f"❌ *Withdrawal of {format_trx_escaped(wd.amount_trx)} failed\\.*\nError\\: {escape_markdown_v2(str(e))}\\.\n"
                safe_notify_user(user.telegram_id, msg)
        except Exception:
            pass


def run_withdrawal_processor():
    try:
        process_withdrawals()
    except Exception as exc:
        logger.error(f"run_withdrawal_processor failed: {exc}")