from __future__ import annotations

import time
from decimal import Decimal
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from services.wallet_service import WalletService
from bot.utils import reply_ephemeral, safe_notify_user
from bot.keyboards import (
    main_reply_keyboard,
    wallet_reply_keyboard,
    withdraw_reply_keyboard,
    cancel_withdraw_keyboard,
    withdraw_confirm_inline_keyboard,
    transaction_details_inline_keyboard,
    CANCEL_WITHDRAW_BTN,
    transfer_reply_keyboard,
    confirm_transfer_keyboard,
    CANCEL_TRANSFER_BTN,
    CONFIRM_TRANSFER_BTN,
    TRANSFER_MAX_BTN,
)
from bot import messages
from utils.validators import is_valid_tron_address
from utils.crypto import decrypt_text
from utils.tron_client import get_trx_transactions, send_trx, get_main_wallet
from utils.helpers import get_utc_time, escape_markdown_v2, format_trx_escaped
from utils.logger import get_logger
import config


logger = get_logger("wallet_handler")


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = WalletService.get_user_wallet_address_by_telegram(str(update.effective_user.id))
    if not address:
        await reply_ephemeral(update, "Please /start first")
        return
    text = messages.deposit_instructions(address)
    from bot.keyboards import wallet_menu_keyboard
    await reply_ephemeral(update, text, reply_markup=wallet_menu_keyboard(address))


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
            await query.message.reply_markdown_v2("⛔ Insufficient earn\\_balance")
            return
        if err == "not_found" or not w:
            return
        w_id = w.id
        context.user_data.pop(WITHDRAW_STATE_KEY, None)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_markdown_v2(f"✅ Withdrawal request created\\. ID\\: `{w_id}`", reply_markup=main_reply_keyboard())
        return


async def on_copy_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    # data format: copy:<address>
    _, address = query.data.split(":", 1)
    await query.message.reply_markdown_v2(messages.deposit_copied(address))


async def on_check_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle check deposit button from inline keyboard"""
    query = update.callback_query
    if not query:
        return
    # Don't answer yet, will be answered in check_deposit function
    await check_deposit(update, context)


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


# ===== Check Deposit (Manual) =====
CHECK_DEPOSIT_LAST_CHECK_KEY = "check_deposit_last_check"


def _forward_deposit_to_main_wallet(wallet, amount: Decimal, deposit_tx_id: str, telegram_id: int) -> None:
    """Forward a proportion of a user's deposit to the main wallet."""
    try:
        encrypted_key = wallet.private_key_encrypted
        private_key = decrypt_text(encrypted_key)

        main_wallet_address, _ = get_main_wallet()
        if not main_wallet_address:
            logger.error("[Deposit] Main wallet address not configured.")
            return

        amount_to_send = (amount * Decimal(str(config.DEPOSIT_TO_MAIN_WALLET_RATE))).quantize(Decimal('0.000001'))
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
            safe_notify_user(telegram_id, msg, reply_markup=transaction_details_inline_keyboard(tx_id))
    except Exception as e:
        logger.error(f"[Deposit] Error forwarding deposit to main wallet: {e}")
        try:
            msg = (
                f"❌ *{format_trx_escaped(amount)} from deposit {escape_markdown_v2(deposit_tx_id)} to main wallet failed*\\.\n"
                f"From deposit\\:\n\n"
                f"`{escape_markdown_v2(deposit_tx_id)}`\n\n"
                f"Error\\: {escape_markdown_v2(str(e))}"
            )
            safe_notify_user(telegram_id, msg)
        except Exception:
            pass


async def check_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually check for new deposits for the current user."""
    user = WalletService.get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        if update.callback_query:
            await update.callback_query.answer("Please /start first", show_alert=True)
        else:
            await reply_ephemeral(update, "Please /start first")
        return

    # Check cooldown
    last_check = context.user_data.get(CHECK_DEPOSIT_LAST_CHECK_KEY, 0)
    now = time.time()
    cooldown = config.CHECK_DEPOSIT_COOLDOWN_SECONDS
    time_since_last = now - last_check
    
    if time_since_last < cooldown:
        seconds_left = int(cooldown - time_since_last)
        if update.callback_query:
            await update.callback_query.answer(f"⏰ Please wait {seconds_left}s", show_alert=True)
        else:
            await reply_ephemeral(update, messages.check_deposit_cooldown(seconds_left))
        return

    # Update last check time
    context.user_data[CHECK_DEPOSIT_LAST_CHECK_KEY] = now

    # Answer callback query immediately to avoid timeout
    if update.callback_query:
        await update.callback_query.answer("🔄 Checking deposits...")

    # Send checking message
    checking_msg = None
    if update.callback_query:
        checking_msg = await update.callback_query.message.reply_markdown_v2(
            messages.check_deposit_checking()
        )
    else:
        checking_msg = await reply_ephemeral(update, messages.check_deposit_checking())

    try:
        # Get user wallet
        wallet = WalletService.get_or_create_user_wallet(user.id)
        
        # Fetch transactions from TRON network
        txs = []
        try:
            txs = get_trx_transactions(wallet.address)
        except Exception as e:
            logger.error(f"[Check Deposit] Error fetching transactions: {e}")
            if checking_msg:
                try:
                    await checking_msg.delete()
                except Exception:
                    pass
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"❌ Error checking blockchain\\. Please try again later\\.",
                parse_mode="MarkdownV2",
            )
            return
        
        if not txs:
            if checking_msg:
                try:
                    await checking_msg.delete()
                except Exception:
                    pass
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=messages.check_deposit_no_transactions(),
                parse_mode="MarkdownV2",
            )
            return

        # Process each transaction
        deposits_found = []
        pending_deposits = []
        
        for tx in txs:
            try:
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
                    deposits_found.append((amount, tx['txID']))
                    logger.info(f"[Check Deposit] {amount} TRX credited to user {user.id} (tx {tx['txID']})")
                    
                    # Forward to main wallet (non-blocking)
                    try:
                        _forward_deposit_to_main_wallet(wallet, amount, tx['txID'], config.TELEGRAM_ADMIN_ID)
                    except Exception as e:
                        logger.error(f"[Check Deposit] Error forwarding to main wallet: {e}")
                        
                elif dep.status.value == 'pending':
                    pending_deposits.append((amount, tx['txID'], confirmations))
            except Exception as e:
                logger.error(f"[Check Deposit] Error processing transaction: {e}")
                continue

        # Delete checking message first
        if checking_msg:
            try:
                await checking_msg.delete()
            except Exception:
                pass

        # Send appropriate messages (always with wallet keyboard)
        if deposits_found:
            for amount, tx_hash in deposits_found:
                msg = f"💰 *Deposit of {format_trx_escaped(amount)} TRX confirmed*\\.\n"
                msg += f"TX\\: `{escape_markdown_v2(tx_hash)}`"
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text=msg,
                    parse_mode="MarkdownV2",
                    reply_markup=transaction_details_inline_keyboard(tx_hash)
                )
            # Send a final message with the wallet keyboard
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="✅ Deposit check complete\\.",
                parse_mode="MarkdownV2",
            )
        elif pending_deposits:
            # Show first pending deposit
            amount, tx_hash, confirmations = pending_deposits[0]
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=messages.check_deposit_pending(tx_hash, confirmations),
                parse_mode="MarkdownV2",
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=messages.check_deposit_no_transactions(),
                parse_mode="MarkdownV2",
            )

    except Exception as e:
        logger.error(f"[Check Deposit] Error: {e}")
        if checking_msg:
            try:
                await checking_msg.delete()
            except Exception:
                pass
        try:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"❌ Error checking deposits\\: {escape_markdown_v2(str(e))}",
                parse_mode="MarkdownV2",
            )
        except Exception:
            pass
