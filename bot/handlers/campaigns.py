from __future__ import annotations

from decimal import Decimal
from telegram import Update
from telegram.ext import ContextTypes

from database.database import get_db_session
from database.models import User, Campaign
from services.campaign_service import CampaignService
from bot.keyboards import (
    SKIP_BTN,
    ads_reply_keyboard,
    campaign_manage_keyboard,
    cancel_create_campaign_keyboard,
    title_step_keyboard,
    create_campaign_confirm_inline_keyboard,
)
from bot.utils import reply_ephemeral
from bot import messages
from utils.logger import logger
from utils.validators import sanitize_telegram_username
import config


# ===== Campaign creation flow state keys =====
CREATE_CAMPAIGN_STATE_KEY = "create_campaign_state"
CREATE_CAMPAIGN_LINK_KEY = "create_campaign_link"
CREATE_CAMPAIGN_USERNAME_KEY = "create_campaign_username"
CREATE_CAMPAIGN_TITLE_KEY = "create_campaign_title"

# ===== My Ads Recharge flow keys =====
MYADS_RECHARGE_STATE_KEY = "myads_recharge_state"
MYADS_RECHARGE_CAMP_ID_KEY = "myads_recharge_camp_id"
MYADS_RECHARGE_AMOUNT_KEY = "myads_recharge_amount"


async def create_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    # One-shot: accept link + username [+ optional title], amount is fixed from config
    if len(args) >= 2:
        bot_link, bot_username = args[0], args[1]
        title = args[2] if len(args) >= 3 else None
        bot_username = sanitize_telegram_username(bot_username)
        amount_dec = Decimal(str(config.AMOUNT_PER_REFERRAL))
        with get_db_session() as db:
            user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
            if not user:
                await reply_ephemeral(update, "Please /start first")
                return
            svc = CampaignService(db)
            final_title = title or f"Campaign by @{user.username or 'user'}"
            camp = svc.create_campaign(
                owner=user,
                title=final_title,
                bot_link=bot_link,
                bot_username=bot_username or "",
                amount_per_referral=amount_dec,
            )
            await reply_ephemeral(update, messages.create_campaign_created(camp.id))
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


async def on_create_campaign_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get(CREATE_CAMPAIGN_STATE_KEY)
    text_in = (update.effective_message.text or "").strip()
    if state == "ask_link":
        username = _extract_username_from_input(text_in)
        if not username:
            await reply_ephemeral(update, messages.create_campaign_ask_link(), reply_markup=cancel_create_campaign_keyboard())
            return
        context.user_data[CREATE_CAMPAIGN_USERNAME_KEY] = username
        context.user_data[CREATE_CAMPAIGN_LINK_KEY] = text_in
        context.user_data[CREATE_CAMPAIGN_STATE_KEY] = "ask_forward"
        await reply_ephemeral(update, messages.create_campaign_ask_forward(username), reply_markup=cancel_create_campaign_keyboard())
        return
    elif state == "ask_title":
        if text_in == SKIP_BTN:
            # use default = bot_username
            username = context.user_data.get(CREATE_CAMPAIGN_USERNAME_KEY) or ""
            context.user_data[CREATE_CAMPAIGN_TITLE_KEY] = username
        else:
            context.user_data[CREATE_CAMPAIGN_TITLE_KEY] = text_in
        # show confirm
        bot_link = context.user_data.get(CREATE_CAMPAIGN_LINK_KEY) or ""
        bot_username = context.user_data.get(CREATE_CAMPAIGN_USERNAME_KEY) or ""
        title = context.user_data.get(CREATE_CAMPAIGN_TITLE_KEY) or bot_username
        amount_dec = Decimal(str(config.AMOUNT_PER_REFERRAL))
        context.user_data[CREATE_CAMPAIGN_STATE_KEY] = "confirm"
        await reply_ephemeral(
            update,
            messages.create_campaign_confirm(bot_link, bot_username, amount_dec, title),
            reply_markup=create_campaign_confirm_inline_keyboard(),
        )
        return


async def on_create_campaign_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only process if we are in ask_forward state
    state = context.user_data.get(CREATE_CAMPAIGN_STATE_KEY)
    if state != "ask_forward":
        return
    bot_username = context.user_data.get(CREATE_CAMPAIGN_USERNAME_KEY) or ""
    logger.info(f"Update message: {update.effective_message.forward_origin}")
    origin_username = _get_forward_origin_username(update.effective_message)
    if not origin_username or origin_username.lower() != bot_username.lower():
        await reply_ephemeral(update, messages.forward_not_from_expected())
        return
    # Move to title step
    context.user_data[CREATE_CAMPAIGN_STATE_KEY] = "ask_title"
    await reply_ephemeral(update, messages.create_campaign_ask_title(bot_username), reply_markup=title_step_keyboard())


async def on_create_campaign_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    if data == "create_campaign_cancel":
        for k in [CREATE_CAMPAIGN_STATE_KEY, CREATE_CAMPAIGN_LINK_KEY, CREATE_CAMPAIGN_USERNAME_KEY, CREATE_CAMPAIGN_TITLE_KEY]:
            context.user_data.pop(k, None)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_markdown_v2(messages.create_campaign_cancelled())
        return
    if data == "create_campaign_confirm":
        bot_link = context.user_data.get(CREATE_CAMPAIGN_LINK_KEY)
        bot_username = context.user_data.get(CREATE_CAMPAIGN_USERNAME_KEY)
        title = context.user_data.get(CREATE_CAMPAIGN_TITLE_KEY) or bot_username or ""
        if not bot_link or not bot_username:
            return
        amount_dec = Decimal(str(config.AMOUNT_PER_REFERRAL))
        with get_db_session() as db:
            user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
            if not user:
                return
            svc = CampaignService(db)
            camp = svc.create_campaign(
                owner=user,
                title=title,
                bot_link=bot_link,
                bot_username=bot_username,
                amount_per_referral=amount_dec,
            )
        # clear state
        for k in [CREATE_CAMPAIGN_STATE_KEY, CREATE_CAMPAIGN_LINK_KEY, CREATE_CAMPAIGN_USERNAME_KEY, CREATE_CAMPAIGN_TITLE_KEY]:
            context.user_data.pop(k, None)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_markdown_v2(messages.create_campaign_created(camp.id), reply_markup=ads_reply_keyboard())
        return


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
    nav.append(InlineKeyboardButton(f"{index+1}/{total}", callback_data="noop"))
    if index < total - 1:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"myads_next_{index+1}"))
    if nav:
        buttons.append(nav)
    return InlineKeyboardMarkup(buttons)


async def show_my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    # page is 1-based index for display; we'll map to 0-based index
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        if not user:
            await reply_ephemeral(update, "Please /start first")
            return
        q = db.query(Campaign).filter(Campaign.owner_id == user.id).order_by(Campaign.id.desc())
        items = q.all()
        if not items:
            await reply_ephemeral(update, "You have no ads yet\\.")
            return
        idx = max(0, min(len(items) - 1, page - 1))
        camp = items[idx]
        # Enforce: cannot be active if balance < amount_per_referral
        if camp.is_active and camp.balance < camp.amount_per_referral:
            camp.is_active = False
            db.commit()
        kb = _my_ads_inline_keyboard(idx, len(items), camp.id, bool(camp.is_active))
        text = messages.my_ad_overview(camp.title, camp.bot_username, camp.amount_per_referral, camp.balance, bool(camp.is_active))
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
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        if not user:
            return
        q = db.query(Campaign).filter(Campaign.owner_id == user.id).order_by(Campaign.id.desc())
        items = q.all()
        if not items:
            await query.message.reply_text("You have no ads yet.")
            return
        idx = max(0, min(len(items) - 1, idx))
        camp = items[idx]
        # Enforce: cannot be active if balance < amount_per_referral
        if camp.is_active and camp.balance < camp.amount_per_referral:
            camp.is_active = False
            db.commit()
        kb = _my_ads_inline_keyboard(idx, len(items), camp.id, bool(camp.is_active))
        text = messages.my_ad_overview(camp.title, camp.bot_username, camp.amount_per_referral, camp.balance, bool(camp.is_active))
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_markdown_v2(text, reply_markup=kb)


async def on_my_ads_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline actions: toggle active/pause and start recharge flow."""
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        if not user:
            return
        # Toggle active/pause
        if data.startswith("myads_toggle_"):
            try:
                camp_id = int(data.rsplit("_", 1)[1])
            except Exception:
                return
            camp = db.query(Campaign).get(camp_id)
            if not camp or camp.owner_id != user.id:
                return
            new_state = not bool(camp.is_active)
            # Prevent activating if insufficient balance
            if new_state and camp.balance < camp.amount_per_referral:
                await reply_ephemeral(
                    update,
                    "❌ *Cannot activate\\:* campaign balance is less than reward per referral\\.",
                    reply_markup=ads_reply_keyboard()
                )
                return
            else:
                camp.is_active = new_state
                db.commit()
            # refresh current index by inferring from message (fallback to 0)
            # For simplicity, re-fetch first page
            q = db.query(Campaign).filter(Campaign.owner_id == user.id).order_by(Campaign.id.desc())
            items = q.all()
            idx = 0
            for i, it in enumerate(items):
                if it.id == camp.id:
                    idx = i
                    break
            kb = _my_ads_inline_keyboard(idx, len(items), camp.id, bool(camp.is_active))
            text = messages.my_ad_overview(camp.title, camp.bot_username, camp.amount_per_referral, camp.balance, bool(camp.is_active))
            await reply_ephemeral(update, text, reply_markup=kb)
            return
        # Start recharge flow
        if data.startswith("myads_recharge_"):
            try:
                camp_id = int(data.rsplit("_", 1)[1])
            except Exception:
                return
            camp = db.query(Campaign).get(camp_id)
            if not camp or camp.owner_id != user.id:
                return
            context.user_data[MYADS_RECHARGE_STATE_KEY] = "ask_amount"
            context.user_data[MYADS_RECHARGE_CAMP_ID_KEY] = camp_id
            # Show ask + presets
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            presets = [
                [InlineKeyboardButton("+10 TRX", callback_data="myads_recharge_preset_10")],
                [InlineKeyboardButton("+50 TRX", callback_data="myads_recharge_preset_50")],
                [InlineKeyboardButton("+100 TRX", callback_data="myads_recharge_preset_100")],
                [InlineKeyboardButton("❌ Cancel", callback_data="myads_recharge_cancel")],
            ]
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_markdown_v2(messages.myads_recharge_ask_amount(), reply_markup=InlineKeyboardMarkup(presets))
            return


async def on_myads_recharge_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get(MYADS_RECHARGE_STATE_KEY)
    if state != "ask_amount":
        return
    text_in = (update.effective_message.text or "").strip()
    from decimal import Decimal as D
    try:
        amount = D(text_in)
        if amount <= 0:
            raise ValueError()
    except Exception:
        await reply_ephemeral(update, messages.myads_recharge_ask_amount())
        return
    context.user_data[MYADS_RECHARGE_AMOUNT_KEY] = amount
    # Confirm inline
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm", callback_data="myads_recharge_confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="myads_recharge_cancel")],
    ])
    await reply_ephemeral(update, messages.myads_recharge_confirm(amount), reply_markup=kb)


async def on_myads_recharge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    # Handle presets
    if data.startswith("myads_recharge_preset_"):
        preset = data.rsplit("_", 1)[1]
        try:
            amount = Decimal(preset)
        except Exception:
            return
        context.user_data[MYADS_RECHARGE_AMOUNT_KEY] = amount
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm", callback_data="myads_recharge_confirm")],
            [InlineKeyboardButton("❌ Cancel", callback_data="myads_recharge_cancel")],
        ])
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_markdown_v2(messages.myads_recharge_confirm(amount), reply_markup=kb)
        return
    if data == "myads_recharge_cancel":
        context.user_data.pop(MYADS_RECHARGE_STATE_KEY, None)
        context.user_data.pop(MYADS_RECHARGE_CAMP_ID_KEY, None)
        context.user_data.pop(MYADS_RECHARGE_AMOUNT_KEY, None)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_markdown_v2(messages.myads_recharge_cancelled())
        return
    if data == "myads_recharge_confirm":
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
        with get_db_session() as db:
            user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
            if not user:
                return
            camp = db.query(Campaign).get(int(camp_id))
            if not camp or camp.owner_id != user.id:
                return
            if user.ad_balance < amt:
                await query.message.reply_markdown_v2("Insufficient ad\\_balance")
                return
            user.ad_balance -= amt
            camp.balance += amt
            db.commit()
        context.user_data.pop(MYADS_RECHARGE_STATE_KEY, None)
        context.user_data.pop(MYADS_RECHARGE_CAMP_ID_KEY, None)
        context.user_data.pop(MYADS_RECHARGE_AMOUNT_KEY, None)
        await query.message.reply_markdown_v2(messages.myads_recharge_done(int(camp_id), amt))
        return


async def pause_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await reply_ephemeral(update, "Usage\\: /pause_campaign <campaign_id>")
        return
    with get_db_session() as db:
        camp = db.query(Campaign).get(int(args[0]))
        if not camp:
            await reply_ephemeral(update, "Campaign not found")
            return
        camp.is_active = False
        db.commit()
        await reply_ephemeral(update, f"Campaign {camp.id} paused")


async def resume_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await reply_ephemeral(update, "Usage: /resume_campaign <campaign_id>")
        return
    with get_db_session() as db:
        camp = db.query(Campaign).get(int(args[0]))
        if not camp:
            await reply_ephemeral(update, "Campaign not found")
            return
        camp.is_active = True
        db.commit()
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
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        if not user:
            await reply_ephemeral(update, "Please /start first")
            return
        camp = db.query(Campaign).get(int(camp_id))
        if not camp or camp.owner_id != user.id:
            await reply_ephemeral(update, "Campaign not found or not yours")
            return
        if user.ad_balance < amount:
            await reply_ephemeral(update, "Insufficient ad\\_balance")
            return
        user.ad_balance -= amount
        camp.balance += amount
        db.commit()
        await reply_ephemeral(update, f"Campaign {camp.id} recharged by {amount}")
