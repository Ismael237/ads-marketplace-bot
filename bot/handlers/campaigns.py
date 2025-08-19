from __future__ import annotations

from decimal import Decimal
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from services.campaign_service import CampaignService
from bot.keyboards import (
    RECHARGE_MAX_BTN,
    SKIP_BTN,
    ads_reply_keyboard,
    cancel_create_campaign_keyboard,
    title_step_keyboard,
    create_campaign_confirm_inline_keyboard,
    recharge_reply_keyboard,
    confirm_recharge_keyboard,
    CONFIRM_CREATE_CAMPAIGN_BTN,
    CANCEL_CREATE_CAMPAIGN_BTN,
)
from bot.utils import reply_ephemeral, safe_notify_user
from bot import messages
from services.wallet_service import WalletService
from utils.logger import logger
from utils.validators import sanitize_telegram_username
import config


# ===== Campaign creation flow state keys =====
CREATE_CAMPAIGN_STATE_KEY = "create_campaign_state"
CREATE_CAMPAIGN_LINK_KEY = "create_campaign_link"
CREATE_CAMPAIGN_USERNAME_KEY = "create_campaign_username"
CREATE_CAMPAIGN_TITLE_KEY = "create_campaign_title"
CREATE_CAMPAIGN_BOT_NAME_KEY = "create_campaign_bot_name"

# ===== My Ads Recharge flow keys =====
MYADS_RECHARGE_STATE_KEY = "myads_recharge_state"
MYADS_RECHARGE_CAMP_ID_KEY = "myads_recharge_camp_id"
MYADS_RECHARGE_AMOUNT_KEY = "myads_recharge_amount"


def _parse_amount_text(text: str):
    try:
        t = (text or "").upper().replace("TRX", "").replace(",", "").strip()
        return Decimal(t)
    except Exception:
        return None


async def create_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    # One-shot: accept link + username [+ optional title], amount is fixed from config
    if len(args) >= 2:
        bot_link, bot_username = args[0], args[1]
        title = args[2] if len(args) >= 3 else None
        bot_username = sanitize_telegram_username(bot_username)
        amount_dec = Decimal(str(config.AMOUNT_PER_REFERRAL))
        user = CampaignService.get_user_by_telegram_id(str(update.effective_user.id))
        if not user:
            await reply_ephemeral(update, "Please /start first")
            return
        final_title = title or f"Campaign by @{user.username or 'user'}"
        CampaignService.create_campaign(
            owner=user,
            title=final_title,
            bot_link=bot_link,
            bot_username=bot_username or "",
            amount_per_referral=amount_dec,
        )
        await reply_ephemeral(update, messages.create_campaign_created())
        # After successful creation, show user's ads list
        await show_my_ads(update, context)
        return
    # Assistant mode: ask for link/username first
    context.user_data[CREATE_CAMPAIGN_STATE_KEY] = "ask_link"
    await reply_ephemeral(update, messages.create_campaign_ask_link(), reply_markup=cancel_create_campaign_keyboard())


def _extract_username_from_input(text: str) -> str | None:
    t = (text or "").strip()
    if not t:
        return None
    if t.startswith("@"):
        return t[1:]
    # Try to parse t.me links
    lowered = t.lower()
    if "t.me/" in lowered:
        try:
            after = t.split("t.me/", 1)[1]
            user = after.split("?")[0].split("/")[0]
            return user.replace("@", "")
        except Exception:
            return None
    return None


def _get_forward_origin_username(msg) -> str | None:
    """Extract forward origin username across PTB versions."""
    if not msg:
        return None
    try:
        fo = getattr(msg, "forward_origin", None)
        if fo is not None:
            if getattr(fo, "type", None) == "user":
                sender_user = getattr(fo, "sender_user", None)
                if sender_user and getattr(sender_user, "username", None):
                    return sender_user.username
            elif getattr(fo, "type", None) == "chat":
                chat = getattr(fo, "chat", None)
                if chat and getattr(chat, "username", None):
                    return chat.username
    except Exception:
        logger.error("Failed to extract forward origin username")
    return None


def _get_forward_origin_title(msg) -> str | None:
    """Try to extract a human-friendly bot name (title/first_name) from forward origin."""
    if not msg:
        return None
    try:
        fo = getattr(msg, "forward_origin", None)
        if fo is not None:
            if getattr(fo, "type", None) == "user":
                sender_user = getattr(fo, "sender_user", None)
                if sender_user:
                    first = getattr(sender_user, "first_name", None) or ""
                    last = getattr(sender_user, "last_name", None) or ""
                    full = (f"{first} {last}").strip()
                    return full or getattr(sender_user, "username", None)
            elif getattr(fo, "type", None) == "chat":
                chat = getattr(fo, "chat", None)
                if chat:
                    title = getattr(chat, "title", None)
                    return title or getattr(chat, "username", None)
    except Exception:
        logger.error("Failed to extract forward origin title")
    return None

def _clear_create_campaign_state(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop(CREATE_CAMPAIGN_STATE_KEY, None)
    context.user_data.pop(CREATE_CAMPAIGN_LINK_KEY, None)
    context.user_data.pop(CREATE_CAMPAIGN_USERNAME_KEY, None)
    context.user_data.pop(CREATE_CAMPAIGN_TITLE_KEY, None)
    context.user_data.pop(CREATE_CAMPAIGN_BOT_NAME_KEY, None)

async def _skip_campaign_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_name = context.user_data.get(CREATE_CAMPAIGN_BOT_NAME_KEY)
    username = context.user_data.get(CREATE_CAMPAIGN_USERNAME_KEY) or ""
    context.user_data[CREATE_CAMPAIGN_TITLE_KEY] = bot_name or username

async def _cancel_create_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_create_campaign_state(context)
    await reply_ephemeral(update, messages.create_campaign_cancelled(), reply_markup=ads_reply_keyboard())

async def _confirm_create_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_link = context.user_data.get(CREATE_CAMPAIGN_LINK_KEY)
    bot_username = context.user_data.get(CREATE_CAMPAIGN_USERNAME_KEY)
    title = context.user_data.get(CREATE_CAMPAIGN_TITLE_KEY) or bot_username or ""
    if not bot_link or not bot_username:
        await reply_ephemeral(update, "Missing campaign data\\. Please start again with '➕ Create Ad'\\\.")
        return
    amount_dec = Decimal(str(config.AMOUNT_PER_REFERRAL))
    user = CampaignService.get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        await reply_ephemeral(update, "Please /start first")
        return
    camp = CampaignService.create_campaign(
        owner=user,
        title=title,
        bot_link=bot_link,
        bot_username=bot_username,
        amount_per_referral=amount_dec,
    )
    # clear state
    _clear_create_campaign_state(context)
    await reply_ephemeral(update, messages.create_campaign_created(), reply_markup=ads_reply_keyboard())
    # Show updated list of user's campaigns
    await show_my_ads(update, context)
    return


async def on_create_campaign_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get(CREATE_CAMPAIGN_STATE_KEY)
    text_in = (update.effective_message.text or "").strip()
    
    if text_in == CANCEL_CREATE_CAMPAIGN_BTN:
        await _cancel_create_campaign(update, context)
        return

    if state == "ask_link":
        username = _extract_username_from_input(text_in)
        if not username:
            await reply_ephemeral(update, messages.create_campaign_ask_link(), reply_markup=cancel_create_campaign_keyboard())
            return
        context.user_data[CREATE_CAMPAIGN_USERNAME_KEY] = username
        context.user_data[CREATE_CAMPAIGN_LINK_KEY] = text_in
        # Provisional display name shown to the user until we verify via forward
        provisional_name = f"@{username}"
        context.user_data[CREATE_CAMPAIGN_BOT_NAME_KEY] = provisional_name
        context.user_data[CREATE_CAMPAIGN_STATE_KEY] = "ask_forward"
        await reply_ephemeral(update, messages.create_campaign_ask_forward(text_in), reply_markup=cancel_create_campaign_keyboard(), disable_web_page_preview=True)
        return
    elif state == "ask_title":
        if text_in == SKIP_BTN:
            await _skip_campaign_title(update, context)
        else:
            context.user_data[CREATE_CAMPAIGN_TITLE_KEY] = text_in
        # show confirm
        bot_link = context.user_data.get(CREATE_CAMPAIGN_LINK_KEY) or ""
        bot_username = context.user_data.get(CREATE_CAMPAIGN_USERNAME_KEY) or ""
        title = context.user_data.get(CREATE_CAMPAIGN_TITLE_KEY) or (context.user_data.get(CREATE_CAMPAIGN_BOT_NAME_KEY) or bot_username)
        amount_dec = Decimal(str(config.AMOUNT_PER_REFERRAL))
        context.user_data[CREATE_CAMPAIGN_STATE_KEY] = "confirm"
        await reply_ephemeral(
            update,
            messages.create_campaign_confirm(bot_link, bot_username, amount_dec, title),
            reply_markup=create_campaign_confirm_inline_keyboard(),
        )
        return
    elif state == "confirm":
        # Reply keyboard confirm/cancel actions
        if text_in == CONFIRM_CREATE_CAMPAIGN_BTN:
            await _confirm_create_campaign(update, context)
            return


async def on_create_campaign_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only process if we are in ask_forward state
    state = context.user_data.get(CREATE_CAMPAIGN_STATE_KEY)
    if state != "ask_forward":
        return
    bot_username = context.user_data.get(CREATE_CAMPAIGN_USERNAME_KEY) or ""
    origin_username = _get_forward_origin_username(update.effective_message)
    if not origin_username or origin_username.lower() != bot_username.lower():
        await reply_ephemeral(update, messages.forward_not_from_expected())
        return
    # Move to title step
    context.user_data[CREATE_CAMPAIGN_STATE_KEY] = "ask_title"
    bot_name = _get_forward_origin_title(update.effective_message) or bot_username
    context.user_data[CREATE_CAMPAIGN_BOT_NAME_KEY] = bot_name
    await reply_ephemeral(update, messages.create_campaign_ask_title(bot_name), reply_markup=title_step_keyboard())


def _my_ads_inline_keyboard(index: int, total: int, camp_id: int, is_active: bool) -> 'InlineKeyboardMarkup':
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = []
    # Row: Toggle + Recharge
    toggle_text = "⏸️ Pause" if is_active else "▶️ Resume"
    buttons.append([
        InlineKeyboardButton(toggle_text, callback_data=f"myads_toggle_{camp_id}"),
        InlineKeyboardButton("🔋 Recharge", callback_data=f"myads_recharge_{camp_id}"),
    ])
    # Row: Navigation
    nav = []
    if index > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"myads_prev_{index-1}"))

    if index < total - 1:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"myads_next_{index+1}"))
    if nav:
        buttons.append(nav)
    return InlineKeyboardMarkup(buttons)


async def show_my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    # page is 1-based index for display; we'll map to 0-based index
    user = CampaignService.get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        await reply_ephemeral(update, "Please /start first")
        return
    items = CampaignService.list_user_campaigns_by_owner(user.id)
    if not items:
        await reply_ephemeral(update, "You have no ads yet\.")
        return
    idx = max(0, min(len(items) - 1, page - 1))
    camp = items[idx]
    # Enforce: cannot be active if balance < amount_per_referral
    camp = CampaignService.enforce_auto_pause_if_insufficient_balance(camp.id) or camp
    kb = _my_ads_inline_keyboard(idx, len(items), camp.id, bool(camp.is_active))
    text = messages.my_ad_overview(camp.title, camp.bot_username, camp.bot_link, camp.amount_per_referral, camp.balance, bool(camp.is_active), camp.referral_count, idx + 1, len(items))
    await reply_ephemeral(update, text, reply_markup=kb)


async def on_my_ads_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data  # myads_prev_{index} or myads_next_{index}
    try:
        _, _, idx_str = data.split("_", 2)
        idx = int(idx_str)
    except Exception:
        return
    # Fetch user ads and send the requested index
    user = CampaignService.get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        return
    items = CampaignService.list_user_campaigns_by_owner(user.id)
    if not items:
        await query.message.reply_text("You have no ads yet.")
        return
    idx = max(0, min(len(items) - 1, idx))
    camp = items[idx]
    # Enforce: cannot be active if balance < amount_per_referral
    camp = CampaignService.enforce_auto_pause_if_insufficient_balance(camp.id) or camp
    kb = _my_ads_inline_keyboard(idx, len(items), camp.id, bool(camp.is_active))
    text = messages.my_ad_overview(camp.title, camp.bot_username, camp.bot_link, camp.amount_per_referral, camp.balance, bool(camp.is_active), camp.referral_count, idx + 1, len(items))
    await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2)


async def on_my_ads_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline actions: toggle active/pause and start recharge flow."""
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    user = CampaignService.get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        return
    # Toggle active/pause
    if data.startswith("myads_toggle_"):
        try:
            camp_id = int(data.rsplit("_", 1)[1])
        except Exception:
            return
        camp, err = CampaignService.toggle_campaign(owner_id=user.id, campaign_id=camp_id)
        if err == "not_found" or not camp:
            return
        if err == "not_owner":
            return
        if err == "insufficient_balance":
            await reply_ephemeral(
                update,
                "❌ *Cannot activate:* campaign balance is less than reward per referral\.",
                reply_markup=ads_reply_keyboard()
            )
            return
        # refresh current index by inferring from items
        items = CampaignService.list_user_campaigns_by_owner(user.id)
        idx = 0
        for i, it in enumerate(items):
            if it.id == camp.id:
                idx = i
                break
        kb = _my_ads_inline_keyboard(idx, len(items), camp.id, bool(camp.is_active))
        text = messages.my_ad_overview(camp.title, camp.bot_username, camp.bot_link, camp.amount_per_referral, camp.balance, bool(camp.is_active), camp.referral_count, idx + 1, len(items))
        await reply_ephemeral(update, text, reply_markup=kb)
        return
    # Start recharge flow
    if data.startswith("myads_recharge_"):
        try:
            camp_id = int(data.rsplit("_", 1)[1])
        except Exception:
            return
        camp = CampaignService.get_campaign_by_id(camp_id)
        if not camp or camp.owner_id != user.id:
            return
        context.user_data[MYADS_RECHARGE_STATE_KEY] = "ask_amount"
        context.user_data[MYADS_RECHARGE_CAMP_ID_KEY] = camp_id
        await query.edit_message_reply_markup(reply_markup=None)
        await reply_ephemeral(update, messages.myads_recharge_ask_amount(user.ad_balance), reply_markup=recharge_reply_keyboard())
        return


async def on_myads_recharge_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get(MYADS_RECHARGE_STATE_KEY)
    if state != "ask_amount":
        return
    text_in = (update.effective_message.text or "").strip()
    user = WalletService.get_user_by_telegram_id(str(update.effective_user.id))
    min_recharge = Decimal(str(getattr(config, "MIN_RECHARGE_TRX", 1)))
    if not user:
        await reply_ephemeral(update, "Please /start first")
        return
    if text_in == RECHARGE_MAX_BTN:
        try:
            max_int = int(Decimal(user.ad_balance))
        except Exception:
            max_int = 0
        if max_int < int(min_recharge):
            await reply_ephemeral(update, messages.recharge_invalid_amount(), reply_markup=recharge_reply_keyboard())
            return
        amount = max_int
    else:
        amount = _parse_amount_text(text_in)
        if amount is None:
            await reply_ephemeral(update, messages.recharge_invalid_amount(), reply_markup=recharge_reply_keyboard())
            return

    # Optional: check against user's ad_balance now for better UX
    if user.ad_balance < Decimal(str(amount)):
        await reply_ephemeral(update, "Insufficient ad\\_balance\\. Enter a lower amount or cancel\\.")
        return
    context.user_data[MYADS_RECHARGE_AMOUNT_KEY] = amount
    # Ask for confirmation using reply keyboard
    await reply_ephemeral(update, messages.myads_recharge_confirm(amount), reply_markup=confirm_recharge_keyboard())


async def on_myads_recharge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    # Inline presets are no longer used; keep for backward compatibility if present
    if data.startswith("myads_recharge_preset_"):
        await query.edit_message_reply_markup(reply_markup=None)
        user = CampaignService.get_user_by_telegram_id(str(update.effective_user.id))
        if not user:
            return
        await query.message.reply_markdown_v2(messages.myads_recharge_ask_amount(user.ad_balance))
        return
    if data == "myads_recharge_cancel":
        context.user_data.pop(MYADS_RECHARGE_STATE_KEY, None)
        context.user_data.pop(MYADS_RECHARGE_CAMP_ID_KEY, None)
        context.user_data.pop(MYADS_RECHARGE_AMOUNT_KEY, None)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_markdown_v2(messages.myads_recharge_cancelled())
        return
    if data == "myads_recharge_confirm":
        # For legacy inline confirm, fall back to text-based confirm handler
        await on_myads_recharge_confirm_text(update, context)
        return


async def on_myads_recharge_confirm_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm recharge via reply keyboard text action."""
    camp_id = context.user_data.get(MYADS_RECHARGE_CAMP_ID_KEY)
    amount = context.user_data.get(MYADS_RECHARGE_AMOUNT_KEY)
    if not camp_id or not amount:
        return
    from decimal import Decimal as D
    try:
        amt = D(str(amount))
        if amt <= 0:
            raise ValueError()
    except Exception:
        return
    user = CampaignService.get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        return
    camp, err, was_activated = CampaignService.recharge_campaign(owner_id=user.id, campaign_id=int(camp_id), amount=amt)
    if err == "insufficient_balance":
        await reply_ephemeral(update, "Insufficient ad\_balance")
        return
    if err is not None or not camp:
        return
    # Clear state
    context.user_data.pop(MYADS_RECHARGE_STATE_KEY, None)
    context.user_data.pop(MYADS_RECHARGE_CAMP_ID_KEY, None)
    context.user_data.pop(MYADS_RECHARGE_AMOUNT_KEY, None)
    # Broadcast activation to all users if the recharge caused activation
    try:
        if was_activated:
            broadcast = messages.campaign_activated_broadcast()
            users = CampaignService.get_all_users(exclude_telegram_id=str(update.effective_user.id))
            for u in users:
                try:
                    tid = int(u.telegram_id)
                except Exception:
                    tid = u.telegram_id
                safe_notify_user(tid, broadcast)
    except Exception as e:
        logger.error(f"[Broadcast] Failed to notify users about activation of a campaign: {e}")
    # Refresh the campaign card view
    user = CampaignService.get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        return
    items = CampaignService.list_user_campaigns_by_owner(user.id)
    # find index of the recharged campaign
    idx = 0
    camp_obj = None
    for i, it in enumerate(items):
        if it.id == int(camp_id):
            idx = i
            camp_obj = it
            break
    if not camp_obj:
        return
    kb = _my_ads_inline_keyboard(idx, len(items), camp_obj.id, bool(camp_obj.is_active))
    text = messages.my_ad_overview(camp_obj.title, camp_obj.bot_username, camp_obj.bot_link, camp_obj.amount_per_referral, camp_obj.balance, bool(camp_obj.is_active), camp_obj.referral_count, idx + 1, len(items))
    await reply_ephemeral(update, "My Ads:", reply_markup=ads_reply_keyboard())
    await reply_ephemeral(update, text, reply_markup=kb)


async def pause_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await reply_ephemeral(update, "Usage: /pause_campaign <campaign_id>")
        return
    camp = CampaignService.pause_campaign_by_id(int(args[0]))
    if not camp:
        await reply_ephemeral(update, "Campaign not found")
        return
    await reply_ephemeral(update, f"Campaign {camp.id} paused")


async def resume_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await reply_ephemeral(update, "Usage: /resume_campaign <campaign_id>")
        return
    camp = CampaignService.resume_campaign_by_id(int(args[0]))
    if not camp:
        await reply_ephemeral(update, "Campaign not found")
        return
    await reply_ephemeral(update, f"Campaign {camp.id} resumed")


async def recharge_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if len(args) < 2:
        await reply_ephemeral(update, "Usage: /recharge_campaign <campaign_id> <amount_trx>")
        return
    camp_id, amount_str = args[0], args[1]
    from decimal import Decimal
    try:
        amount = Decimal(amount_str)
    except Exception:
        await reply_ephemeral(update, "Invalid amount")
        return
    user = CampaignService.get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        await reply_ephemeral(update, "Please /start first")
        return
    camp, err, was_activated = CampaignService.recharge_campaign(owner_id=user.id, campaign_id=int(camp_id), amount=amount)
    if err == "not_owner" or err == "not_found":
        await reply_ephemeral(update, "Campaign not found or not yours")
        return
    if err == "insufficient_balance":
        await reply_ephemeral(update, "Insufficient ad\\_balance")
        return
    await reply_ephemeral(update, f"Campaign {camp.id} recharged by {amount}")
    # Broadcast activation to all users if the recharge caused activation
    try:
        if was_activated:
            broadcast = messages.campaign_activated_broadcast()
            users = CampaignService.get_all_users()
            for u in users:
                try:
                    tid = int(u.telegram_id)
                except Exception:
                    tid = u.telegram_id
                safe_notify_user(tid, broadcast)
    except Exception as e:
        logger.error(f"[Broadcast] Failed to notify users about activation of campaign: {e}")
