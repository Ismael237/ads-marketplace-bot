from __future__ import annotations

from decimal import Decimal
from telegram import Update
from telegram.ext import ContextTypes

from services.wallet_service import WalletService
from bot.utils import reply_ephemeral
from bot.keyboards import (
    main_reply_keyboard,
    wallet_reply_keyboard,
    withdraw_reply_keyboard,
    cancel_withdraw_keyboard,
    withdraw_confirm_inline_keyboard,
    CANCEL_WITHDRAW_BTN,
    transfer_reply_keyboard,
    confirm_transfer_keyboard,
    CANCEL_TRANSFER_BTN,
    CONFIRM_TRANSFER_BTN,
    TRANSFER_MAX_BTN,
)
from bot import messages
from utils.validators import is_valid_tron_address
import config


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = WalletService.get_user_wallet_address_by_telegram(str(update.effective_user.id))
    if not address:
        await reply_ephemeral(update, "Please /start first")
        return
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
        user = WalletService.get_user_by_telegram_id(str(update.effective_user.id))
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
    user = WalletService.get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        await reply_ephemeral(update, "Please /start first")
        return
    w, err = WalletService.create_withdrawal(user_id=user.id, amount=amount, to_address=to_address)
    if err == "not_found":
        await reply_ephemeral(update, "Please /start first")
        return
    if err == "insufficient_balance":
        await reply_ephemeral(update, "Insufficient earn_balance")
        return
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
        await reply_ephemeral(update, messages.withdraw_cancelled(), reply_markup=main_reply_keyboard())
        return
    if state == "ask_amount":
        amount = _parse_amount_text(text_in)
        if not amount or amount < Decimal(str(config.MIN_WITHDRAWAL_TRX)):
            user = WalletService.get_user_by_telegram_id(str(update.effective_user.id))
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
        user = WalletService.get_user_by_telegram_id(str(update.effective_user.id))
        if not user:
            return
        w, err = WalletService.create_withdrawal(user_id=user.id, amount=amount, to_address=to_address)
        if err == "insufficient_balance":
            await query.message.reply_markdown_v2("Insufficient earn_balance")
            return
        if err == "not_found" or not w:
            return
        w_id = w.id
        context.user_data.pop(WITHDRAW_STATE_KEY, None)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_markdown_v2(f"Withdrawal request created id={w_id}", reply_markup=main_reply_keyboard())
        return


async def on_copy_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    # data format: copy:<address>
    _, address = query.data.split(":", 1)
    await query.message.reply_markdown_v2(messages.deposit_copied(address))


# ===== Internal Transfer (earn_balance -> ad_balance) =====
TRANSFER_STATE_KEY = "transfer_state"
TRANSFER_AMOUNT_KEY = "transfer_amount"


def _parse_positive_int_amount_text(text: str) -> int | None:
    try:
        t = (text or "").upper().replace("TRX", "").replace(",", "").strip()
        if not t:
            return None
        # integer only
        if not t.isdigit():
            return None
        val = int(t)
        if val < int(config.MIN_TRANSFER_TRX):
            return None
        return val
    except Exception:
        return None


async def start_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = WalletService.get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        await reply_ephemeral(update, "Please /start first")
        return
    context.user_data[TRANSFER_STATE_KEY] = "ask_amount"
    await reply_ephemeral(
        update,
        messages.transfer_ask_amount(user.earn_balance, float(config.TRANSFER_FEE_RATE)),
        reply_markup=transfer_reply_keyboard(),
    )


async def on_transfer_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get(TRANSFER_STATE_KEY)
    text_in = (update.effective_message.text or "").strip()
    if text_in == CANCEL_TRANSFER_BTN:
        context.user_data.pop(TRANSFER_STATE_KEY, None)
        context.user_data.pop(TRANSFER_AMOUNT_KEY, None)
        await reply_ephemeral(update, messages.transfer_cancelled(), reply_markup=wallet_reply_keyboard())
        return
    if state == "ask_amount":
        user = WalletService.get_user_by_telegram_id(str(update.effective_user.id))
        if not user:
            await reply_ephemeral(update, "Please /start first")
            return
        if text_in == TRANSFER_MAX_BTN:
            # Use floor of earn_balance to integer
            try:
                max_int = int(Decimal(user.earn_balance))
            except Exception:
                max_int = 0
            if max_int < int(config.MIN_TRANSFER_TRX):
                await reply_ephemeral(update, messages.transfer_invalid_amount(), reply_markup=transfer_reply_keyboard())
                return
            amount_int = max_int
        else:
            amount_int = _parse_positive_int_amount_text(text_in)
            if amount_int is None:
                await reply_ephemeral(update, messages.transfer_invalid_amount(), reply_markup=transfer_reply_keyboard())
                return
        # Validate available balance (gross)
        if Decimal(str(amount_int)) > Decimal(user.earn_balance):
            await reply_ephemeral(update, messages.transfer_insufficient_balance(), reply_markup=transfer_reply_keyboard())
            return
        context.user_data[TRANSFER_AMOUNT_KEY] = int(amount_int)
        context.user_data[TRANSFER_STATE_KEY] = "confirm"
        await reply_ephemeral(
            update,
            messages.transfer_confirm(Decimal(amount_int), float(config.TRANSFER_FEE_RATE)),
            reply_markup=confirm_transfer_keyboard(),
        )
        return
    elif state == "confirm":
        if text_in == CONFIRM_TRANSFER_BTN:
            user = WalletService.get_user_by_telegram_id(str(update.effective_user.id))
            if not user:
                await reply_ephemeral(update, "Please /start first")
                return
            amount_int = context.user_data.get(TRANSFER_AMOUNT_KEY)
            if not amount_int:
                return
            gross = Decimal(int(amount_int))
            fee_rate = Decimal(str(config.TRANSFER_FEE_RATE))
            new_user, err = WalletService.internal_transfer_earn_to_ad(user.id, gross, fee_rate)
            if err == "insufficient_balance":
                await reply_ephemeral(update, messages.transfer_insufficient_balance())
                return
            if err == "not_found" or not new_user:
                await reply_ephemeral(update, "Please /start first")
                return
            context.user_data.pop(TRANSFER_STATE_KEY, None)
            context.user_data.pop(TRANSFER_AMOUNT_KEY, None)
            await reply_ephemeral(update, messages.transfer_done(gross, new_user.earn_balance, new_user.ad_balance), reply_markup=wallet_reply_keyboard())
            return
