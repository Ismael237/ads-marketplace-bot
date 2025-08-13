from __future__ import annotations

from decimal import Decimal
from telegram import Update
from telegram.ext import ContextTypes

from database.database import get_db_session
from database.models import User, Withdrawal, WithdrawalStatus, Transaction, TransactionType, BalanceType
from services.wallet_service import WalletService
from bot.utils import reply_ephemeral
from bot.keyboards import main_reply_keyboard, withdraw_reply_keyboard, cancel_withdraw_keyboard, withdraw_confirm_inline_keyboard, CANCEL_WITHDRAW_BTN
from bot import messages
from utils.validators import is_valid_tron_address
import config


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        if not user:
            await reply_ephemeral(update, "Please /start first")
            return
        ws = WalletService(db)
        address = ws.get_user_wallet_address(user)
        text = messages.deposit_instructions(address)
        await reply_ephemeral(update, text)


WITHDRAW_STATE_KEY = "withdraw_state"
WITHDRAW_AMOUNT_KEY = "withdraw_amount"
WITHDRAW_ADDRESS_KEY = "withdraw_address"


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if len(args) < 2:
        # Start guided flow
        context.user_data[WITHDRAW_STATE_KEY] = "ask_amount"
        with get_db_session() as db:
            user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
            if not user:
                await reply_ephemeral(update, "Please /start first")
                return
            await reply_ephemeral(
                update,
                messages.withdraw_ask_amount(config.MIN_WITHDRAWAL_TRX, user.earn_balance),
                reply_markup=withdraw_reply_keyboard(),
            )
        return
    amount_str, to_address = args[0], args[1]
    try:
        amount = Decimal(amount_str)
    except Exception:
        await reply_ephemeral(update, "Invalid amount")
        return
    if amount < Decimal(str(config.MIN_WITHDRAWAL_TRX)):
        await reply_ephemeral(update, f"Minimum withdrawal is {config.MIN_WITHDRAWAL_TRX} TRX")
        return
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        if not user:
            await reply_ephemeral(update, "Please /start first")
            return
        if user.earn_balance < amount:
            await reply_ephemeral(update, "Insufficient earn_balance")
            return
        user.earn_balance -= amount
        db.commit()
        w = Withdrawal.create(
            db,
            user_id=user.id,
            amount_trx=amount,
            to_address=to_address,
            status=WithdrawalStatus.pending,
        )
        Transaction.create(
            db,
            user_id=user.id,
            type=TransactionType.withdrawal,
            amount_trx=amount,
            balance_type=BalanceType.earn_balance,
            reference_id=str(w.id),
            description="Withdrawal requested",
        )
        await reply_ephemeral(update, f"Withdrawal request created id={w.id}")


def _parse_amount_text(text: str) -> Decimal | None:
    try:
        t = text.upper().replace("TRX", "").replace(",", "").strip()
        return Decimal(t)
    except Exception:
        return None


async def on_withdraw_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get(WITHDRAW_STATE_KEY)
    text_in = (update.effective_message.text or "").strip()
    if text_in == CANCEL_WITHDRAW_BTN:
        context.user_data.pop(WITHDRAW_STATE_KEY, None)
        context.user_data.pop(WITHDRAW_AMOUNT_KEY, None)
        context.user_data.pop(WITHDRAW_ADDRESS_KEY, None)
        await reply_ephemeral(update, messages.withdraw_cancelled())
        return
    if state == "ask_amount":
        amount = _parse_amount_text(text_in)
        if not amount or amount < Decimal(str(config.MIN_WITHDRAWAL_TRX)):
            with get_db_session() as db:
                user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
                if not user:
                    await reply_ephemeral(update, "Please /start first")
                    return
                await reply_ephemeral(
                    update,
                    messages.withdraw_ask_amount(config.MIN_WITHDRAWAL_TRX, user.earn_balance),
                    reply_markup=withdraw_reply_keyboard(),
                )
            return
        context.user_data[WITHDRAW_AMOUNT_KEY] = amount
        context.user_data[WITHDRAW_STATE_KEY] = "ask_address"
        await reply_ephemeral(update, messages.withdraw_ask_address(amount), reply_markup=cancel_withdraw_keyboard())
        return
    elif state == "ask_address":
        to_address = text_in
        if not is_valid_tron_address(to_address):
            await reply_ephemeral(update, messages.withdraw_ask_address(context.user_data.get(WITHDRAW_AMOUNT_KEY)), reply_markup=cancel_withdraw_keyboard())
            return
        context.user_data[WITHDRAW_ADDRESS_KEY] = to_address
        context.user_data[WITHDRAW_STATE_KEY] = "confirm"
        amount = context.user_data[WITHDRAW_AMOUNT_KEY]
        text = messages.withdraw_confirm(amount, to_address, Decimal(str(config.WITHDRAWAL_FEE_RATE)))
        await reply_ephemeral(update, text, reply_markup=withdraw_confirm_inline_keyboard())
        return


async def on_withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    if data == "withdraw_cancel":
        context.user_data.pop(WITHDRAW_STATE_KEY, None)
        context.user_data.pop(WITHDRAW_AMOUNT_KEY, None)
        context.user_data.pop(WITHDRAW_ADDRESS_KEY, None)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_markdown_v2(messages.withdraw_cancelled(), reply_markup=main_reply_keyboard())
        return
    if data == "withdraw_confirm":
        amount = context.user_data.get(WITHDRAW_AMOUNT_KEY)
        to_address = context.user_data.get(WITHDRAW_ADDRESS_KEY)
        if not amount or not to_address:
            return
        with get_db_session() as db:
            user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
            if not user:
                return
            if user.earn_balance < amount:
                await query.message.reply_markdown_v2("Insufficient earn\\_balance")
                return
            user.earn_balance -= amount
            db.commit()
            w = Withdrawal.create(
                db,
                user_id=user.id,
                amount_trx=amount,
                to_address=to_address,
                status=WithdrawalStatus.pending,
            )
            w_id = w.id
            Transaction.create(
                db,
                user_id=user.id,
                type=TransactionType.withdrawal,
                amount_trx=amount,
                balance_type=BalanceType.earn_balance,
                reference_id=str(w_id),
                description="Withdrawal requested",
            )
        context.user_data.pop(WITHDRAW_STATE_KEY, None)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_markdown_v2(f"Withdrawal request created id\\={w_id}", reply_markup=main_reply_keyboard())
        return


async def on_copy_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    # data format: copy:<address>
    _, address = query.data.split(":", 1)
    await query.message.reply_markdown_v2(messages.deposit_copied(address))

