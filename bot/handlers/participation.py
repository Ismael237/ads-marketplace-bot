from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from services.participation_service import ParticipationService
from services.campaign_service import CampaignService
from bot.keyboards import campaigns_browse_keyboard, report_reasons_keyboard
from bot.utils import reply_ephemeral, safe_notify_user
from bot import messages
from utils.helpers import get_utc_date, get_utc_time, escape_markdown_v2, format_trx_escaped
from decimal import Decimal
import config


def _generate_campaign_view(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int = 0):
    """Build the text and keyboard for browsing campaigns at a given index.
    Returns a tuple (ok, payload) where:
      - ok is True and payload is dict(text, kb, index) on success
      - ok is False and payload is an error text to show
    """
    try:
        tg_id = str(update.effective_user.id) if update and update.effective_user else None
    except AttributeError:
        tg_id = None
    campaigns = ParticipationService.get_active_campaigns_for_browsing(tg_id)
    if not campaigns:
        return False, "No active campaigns"
    if index >= len(campaigns):
        msg = "You've reached the end of the campaign list\.\n"
        msg += "There are no more active campaigns available\.\n"
        return False, msg
    camp = campaigns[index]
    # Validate required attributes
    if not getattr(camp, 'bot_link', None):
        return False, "Campaign bot link is not available"
    if getattr(camp, 'amount_per_referral', None) is None:
        return False, "Campaign amount per referral is not set"
    # Build keyboard and text
    kb = campaigns_browse_keyboard(camp.bot_link, camp.id)
    apr = camp.amount_per_referral
    user_pct = Decimal(str(getattr(config, "PARTICIPATION_USER_REWARD_PERCENT", 75))) / Decimal("100")
    user_reward = Decimal(str(apr * user_pct)).quantize(Decimal("0.000001"))
    title = getattr(camp, 'title', 'Untitled Campaign')
    text = messages.browse_campaign(title, user_reward)
    return True, {"text": text, "kb": kb, "index": index}


async def _send_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int = 0):
    ok, payload = _generate_campaign_view(update, context, index)
    if not ok:
        await reply_ephemeral(update, payload)
        return
    context.user_data["browse_index"] = payload["index"]
    await reply_ephemeral(update, payload["text"], reply_markup=payload["kb"])


async def browse_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_campaign(update, context, index=0)


def _get_forward_origin_username(msg) -> str | None:
    """Extract forward origin username across PTB versions."""
    if not msg:
        return None
    # PTB <=20
    try:
        u = getattr(msg, "forward_from", None)
        if u and getattr(u, "username", None):
            return u.username
    except Exception:
        pass
    try:
        ch = getattr(msg, "forward_from_chat", None)
        if ch and getattr(ch, "username", None):
            return ch.username
    except Exception:
        pass
    # PTB >=21
    try:
        fo = getattr(msg, "forward_origin", None)
        if fo is not None:
            sender_user = getattr(fo, "sender_user", None)
            if sender_user and getattr(sender_user, "username", None):
                return sender_user.username
            chat = getattr(fo, "chat", None)
            if chat and getattr(chat, "username", None):
                return chat.username
    except Exception:
        pass
    return None


async def forward_validator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user = ParticipationService.get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        return
    part = None
    camp = None
    # Validate forward source
    origin_username = _get_forward_origin_username(update.message)
    # If no pending participation, try to infer campaign from forward origin
    if origin_username:
        camp = ParticipationService.find_campaign_by_forward_origin_for_user(str(update.effective_user.id), origin_username)
        if camp:
            # Centralized rule check with explicit reason
            allowed, reason = CampaignService.can_user_participate(camp, user)
            if not allowed:
                if reason == "inactive":
                    await reply_ephemeral(update, messages.campaign_not_active())
                elif reason == "owner":
                    await reply_ephemeral(update, messages.campaign_owner_cannot_participate())
                elif reason == "validated_today":
                    await reply_ephemeral(update, messages.campaign_already_validated_today())
                else:
                    # generic fallback (e.g. existing pending/validated, blocked, etc.)
                    await reply_ephemeral(update, messages.campaign_participation_blocked())
                return
            else:
                part = ParticipationService.start_participation(camp.id, user.id)

    if part is None:
        return
    if camp is None:
        camp = ParticipationService.get_campaign_by_id(part.campaign_id)

    if not origin_username or origin_username.lower() != (camp.bot_username or "").lower():
        await reply_ephemeral(update, messages.forward_not_from_expected())
        ParticipationService.mark_participation_failed(part.id)
        return
    ParticipationService.set_forward_and_generate_link(part.id, str(update.message.message_id))
    # Immediately process validation and payments (MVP):
    user_reward, err = ParticipationService.validate_and_payout(part.id)
    if err == 'insufficient_balance':
        await reply_ephemeral(update, messages.campaign_insufficient_balance())
        return
    if err == 'not_found' or not user_reward:
        return

    # Sponsor notification and admin notification (informational only)
    apr = camp.amount_per_referral or Decimal("0")
    sponsor_pct = Decimal(str(getattr(config, "SPONSOR_PARTICIPATION_COMMISSION_PERCENT", 5))) / Decimal("100")
    sponsor_commission = (apr * sponsor_pct).quantize(Decimal("0.000001"))
    if getattr(user, 'sponsor_id', None) and sponsor_commission > 0:
        sponsor = CampaignService.get_user_by_telegram_id(str(getattr(user, 'sponsor_id', ''))) or None
        # If user model's sponsor_id stores numeric user.id, fetch by id instead of telegram
        sponsor = sponsor or None
        try:
            # Try fetch by ID when telegram lookup fails
            from database.database import get_db_session as _g
            from database.models import User as _U
            with _g() as _db:
                sponsor = sponsor or _db.query(_U).get(int(user.sponsor_id))
        except Exception:
            sponsor = sponsor
        if sponsor and getattr(sponsor, 'telegram_id', None):
            try:
                spons_tid = int(sponsor.telegram_id)
            except Exception:
                spons_tid = sponsor.telegram_id
            username = user.username or "user"
            msg = (
                f"🎉 *Commission Received*\n"
                f"You have received {escape_markdown_v2(str(int(sponsor_pct * 100)))}% on a validated participation by @"
                f"{escape_markdown_v2(username)}\n"
                f"Amount\: {format_trx_escaped(sponsor_commission)} TRX"
            )
            safe_notify_user(spons_tid, msg)

    admin_remainder = (apr - user_reward - (sponsor_commission if getattr(user, 'sponsor_id', None) else Decimal("0"))).quantize(Decimal("0.000001"))
    if admin_remainder > 0:
        msg = (
            f"🎉 *Admin Commission Received*\n"
            f"Amount\: {format_trx_escaped(admin_remainder)} TRX"
        )
        safe_notify_user(config.TELEGRAM_ADMIN_ID, msg)

    await reply_ephemeral(update, messages.participation_validated(user_reward))


async def on_campaign_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    index = context.user_data.get("browse_index", 0) + 1
    ok, payload = _generate_campaign_view(update, context, index)
    if not ok:
        # Edit current message to show end/no-campaign notice and remove keyboard
        try:
            await query.edit_message_text(payload, parse_mode=ParseMode.MARKDOWN_V2)
        except Exception:
            await reply_ephemeral(update, payload)
        return
    context.user_data["browse_index"] = payload["index"]
    # Edit current message in place instead of sending a new one
    await query.edit_message_text(
        payload["text"],
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=payload["kb"],
        disable_web_page_preview=True,
    )


async def on_campaign_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data  # format: campaign_report:<campaign_id>
    try:
        _, cid = data.split(":", 1)
        campaign_id = int(cid)
    except Exception:
        return
    text = messages.report_choose_reason()
    kb = report_reasons_keyboard(campaign_id)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_markdown_v2(text, reply_markup=kb)


async def on_report_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    # format: report_reason:<reason>:<campaign_id>
    try:
        _, reason, cid = query.data.split(":", 2)
        campaign_id = int(cid)
    except Exception:
        return
    ok = ParticipationService.create_report(campaign_id, str(update.effective_user.id), reason)
    if not ok:
        return
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_markdown_v2(messages.report_saved())
