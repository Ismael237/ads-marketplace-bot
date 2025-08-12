from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from database.database import get_db_session
from database.models import User
from bot.utils import reply_ephemeral
from bot import messages
import config

from bot.keyboards import (
    BROWSE_BTN,
    BALANCE_BTN,
    CANCEL_CREATE_CAMPAIGN_BTN,
    MY_ADS_BTN,
    CANCEL_WITHDRAW_BTN,
    DEPOSIT_BTN,
    WITHDRAW_BTN,
    REFERRAL_BTN,
    SETTINGS_BTN,
    HISTORY_BTN,
    WALLET_BTN,
    HELP_BTN,
    SUPPORT_BTN,
    ABOUT_BTN,
    Q_A_BTN,
    REFERRAL_INFO_BTN,
    MAIN_MENU_BTN,
    ADS_CREATE_BTN,
    ADS_LIST_BTN,
    ALL_TRANSACTIONS_BTN,
    DEPOSITS_ONLY_BTN,
    INVESTMENTS_ONLY_BTN,
    WITHDRAWALS_ONLY_BTN,
    history_reply_keyboard,
    settings_reply_keyboard,
    main_reply_keyboard,
    ads_reply_keyboard,
    withdraw_reply_keyboard,
    wallet_reply_keyboard,
)

from bot.handlers.participation import browse_bots
from bot.handlers.wallet import (
    WITHDRAW_ADDRESS_KEY,
    WITHDRAW_AMOUNT_KEY,
    deposit as wallet_deposit,
    on_withdraw_callback,
    withdraw as wallet_withdraw,
    on_withdraw_text,
    WITHDRAW_STATE_KEY,
)
from bot.handlers.campaigns import (
    CREATE_CAMPAIGN_LINK_KEY,
    CREATE_CAMPAIGN_STATE_KEY,
    CREATE_CAMPAIGN_TITLE_KEY,
    CREATE_CAMPAIGN_USERNAME_KEY,
    on_create_campaign_text,
    create_campaign as create_campaign_handler,
    show_my_ads,
    on_myads_recharge_text,
    MYADS_RECHARGE_STATE_KEY,
)
from bot.handlers.referral import referral as referral_handler
from bot.handlers.history import history as history_handler, show_history


async def on_browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await browse_bots(update, context)


async def on_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        if not user:
            await reply_ephemeral(update, "Please /start first")
            return
        text = messages.balance_overview(user.earn_balance, user.ad_balance)
        await reply_ephemeral(update, text)


async def on_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await wallet_deposit(update, context)


async def on_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.args = []
    await wallet_withdraw(update, context)


async def on_cancel_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop(WITHDRAW_STATE_KEY, None)
    context.user_data.pop(WITHDRAW_AMOUNT_KEY, None)
    context.user_data.pop(WITHDRAW_ADDRESS_KEY, None)
    await reply_ephemeral(update, messages.withdraw_cancelled(), reply_markup=main_reply_keyboard())


async def on_cancel_create_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop(CREATE_CAMPAIGN_STATE_KEY, None)
    context.user_data.pop(CREATE_CAMPAIGN_LINK_KEY, None)
    context.user_data.pop(CREATE_CAMPAIGN_USERNAME_KEY, None)
    context.user_data.pop(CREATE_CAMPAIGN_TITLE_KEY, None)
    await reply_ephemeral(update, messages.create_campaign_cancelled(), reply_markup=ads_reply_keyboard())


async def on_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await referral_handler(update, context)


async def on_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_ephemeral(
        update,
        messages.settings_info(config.TELEGRAM_ADMIN_USERNAME),
        reply_markup=settings_reply_keyboard(),
    )


async def on_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_ephemeral(update, messages.history_intro(), reply_markup=history_reply_keyboard())


async def on_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_ephemeral(update, "Help\\: Use the menu to browse campaigns, deposit TRX, withdraw earnings, and manage referrals\\.")


async def on_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_ephemeral(update, f"Support\\: Contact @{config.TELEGRAM_ADMIN_USERNAME or 'admin'}")


async def on_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_ephemeral(update, "About\\: Campaign Marketplace Bot on TRON\\.")


async def on_qa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_ephemeral(update, "Q&A\\: Coming soon\\.")


async def on_referral_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_ephemeral(update, "Referral Info\\: Earn commissions from your invited users\\.")


async def on_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_ephemeral(update, "Choose an option\\:", reply_markup=main_reply_keyboard())


async def handle_menu_selection(update, context):
    # Route My Ads recharge free-text amount entry if flow is active
    if context.user_data.get(MYADS_RECHARGE_STATE_KEY) == "ask_amount":
        await on_myads_recharge_text(update, context)
        return
    text = (update.message.text or "").strip()

    # If user is in withdraw flow, delegate text to wallet flow
    # Route campaign creation first
    if context.user_data.get("create_campaign_state"):
        await on_create_campaign_text(update, context)
        return
    if context.user_data.get(WITHDRAW_STATE_KEY):
        await on_withdraw_text(update, context)
        return

    if text == BROWSE_BTN:
        await on_browse(update, context)
    elif text == BALANCE_BTN:
        await on_balance(update, context)
    elif text == DEPOSIT_BTN:
        await on_deposit(update, context)
    elif text == WITHDRAW_BTN:
        await on_withdraw(update, context)
    elif text == REFERRAL_BTN:
        await on_referral(update, context)
    elif text == SETTINGS_BTN:
        await on_settings(update, context)
    elif text == WALLET_BTN:
        await reply_ephemeral(update, "Wallet:", reply_markup=wallet_reply_keyboard())
    elif text == HISTORY_BTN:
        await on_history(update, context)
    elif text == MY_ADS_BTN:
        await reply_ephemeral(update, "My Ads:", reply_markup=ads_reply_keyboard())
    elif text == ADS_CREATE_BTN:
        # start assistant mode
        context.args = []
        await create_campaign_handler(update, context)
    elif text == ADS_LIST_BTN:
        await show_my_ads(update, context, page=1)
    elif text == CANCEL_CREATE_CAMPAIGN_BTN:
        await on_cancel_create_campaign(update, context)
    elif text == HELP_BTN:
        await on_help(update, context)
    elif text == SUPPORT_BTN:
        await on_support(update, context)
    elif text == ABOUT_BTN:
        await on_about(update, context)
    elif text == Q_A_BTN:
        await on_qa(update, context)
    elif text == REFERRAL_INFO_BTN:
        await on_referral_info(update, context)
    elif text == CANCEL_WITHDRAW_BTN:
        await on_cancel_withdraw(update, context)
    elif text == MAIN_MENU_BTN:
        await on_main_menu(update, context)
    # History filters via reply keyboard
    elif text in {ALL_TRANSACTIONS_BTN, DEPOSITS_ONLY_BTN, INVESTMENTS_ONLY_BTN, WITHDRAWALS_ONLY_BTN}:
        mapping = {
            ALL_TRANSACTIONS_BTN: "all",
            DEPOSITS_ONLY_BTN: "deposits",
            INVESTMENTS_ONLY_BTN: "investments",
            WITHDRAWALS_ONLY_BTN: "withdrawals",
        }
        await show_history(update, context, mapping[text], page=1)
    else:
        await reply_ephemeral(update, "Unknown command\\. Please use the menu\\.", reply_markup=main_reply_keyboard())

# Error handler
async def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning(f'Update "{update}" caused error "{context.error}"')
    try:
        await update.message.reply_text('An error occurred. Please try again or contact support.')
    except:
        try:
            await update.callback_query.message.reply_text('An error occurred. Please try again or contact support.')
        except:
            pass