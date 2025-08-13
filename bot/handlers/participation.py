from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from database.database import get_db_session
from database.models import (
    User,
    Campaign,
    CampaignParticipation,
    ParticipationStatus,
    Transaction,
    TransactionType,
    BalanceType,
    CampaignReport,
    ReportReason,
)
from sqlalchemy import func
from services.referral_service import ReferralService
import config
from decimal import Decimal
from services.campaign_service import CampaignService
from bot.keyboards import campaigns_browse_keyboard, report_reasons_keyboard
from bot.utils import reply_ephemeral, safe_notify_user
from bot import messages
from sqlalchemy import func
from utils.helpers import get_utc_date, get_utc_time, escape_markdown_v2, format_trx_escaped


async def _send_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int = 0):
    with get_db_session() as db:
        q = db.query(Campaign).filter(Campaign.is_active == True).order_by(Campaign.id.desc())
        # Exclude campaigns owned by the current user (owners cannot participate in their own campaigns)
        try:
            tg_id = str(update.effective_user.id) if update and update.effective_user else None
        except Exception:
            tg_id = None
        if tg_id:
            current_user = db.query(User).filter(User.telegram_id == tg_id).first()
            if current_user:
                q = q.filter(Campaign.owner_id != current_user.id)
                # Exclude campaigns already validated today by the current user (once per day rule)
                today = get_utc_date()
                validated_today_subq = (
                    db.query(CampaignParticipation.campaign_id)
                    .filter(
                        CampaignParticipation.user_id == current_user.id,
                        CampaignParticipation.status == ParticipationStatus.validated,
                        func.date(CampaignParticipation.validated_at) == today,
                    )
                )
                q = q.filter(~Campaign.id.in_(validated_today_subq))
        campaigns = q.all()
        if not campaigns:
            await reply_ephemeral(update, "No active campaigns")
            return
        if index >= len(campaigns):
            msg = "You've reached the end of the campaign list.\n"
            msg += "There are no more active campaigns available.\n"
            await reply_ephemeral(update, msg)
            return
        camp = campaigns[index]
        context.user_data["browse_index"] = index
        kb = campaigns_browse_keyboard(camp.bot_link, camp.id)
        apr = camp.amount_per_referral
        # Compute payouts
        user_pct = Decimal(str(getattr(config, "PARTICIPATION_USER_REWARD_PERCENT", 75))) / Decimal("100")
        user_reward = Decimal(str(apr * user_pct)).quantize(Decimal("0.000001"))
        text = messages.browse_campaign(camp.title, camp.bot_username, user_reward)
        await reply_ephemeral(update, text, reply_markup=kb)


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
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        if not user:
            return
        # pick the latest pending participation for this user
        part = (
            db.query(CampaignParticipation)
            .filter(
                CampaignParticipation.user_id == user.id,
                CampaignParticipation.status == ParticipationStatus.pending,
            )
            .order_by(CampaignParticipation.id.desc())
            .first()
        )
        camp = None
        # Validate forward source
        origin_username = _get_forward_origin_username(update.message)
        # If no pending participation, try to infer campaign from forward origin
        if part is None and origin_username:
            camp = (
                db.query(Campaign)
                .filter(Campaign.bot_username.ilike(origin_username))
                .first()
            )
            if camp:
                svc = CampaignService(db)
                # Check if user can participate with detailed error messages
                if not camp.is_active:
                    await reply_ephemeral(update, messages.campaign_not_active())
                    return
                elif camp.owner_id == user.id:
                    await reply_ephemeral(update, messages.campaign_owner_cannot_participate())
                    return
                elif not svc.can_user_participate(camp, user):
                    # Check specific reason for blocking
                    today = get_utc_date()
                    validated_today = (
                        db.query(CampaignParticipation)
                        .filter(
                            CampaignParticipation.campaign_id == camp.id,
                            CampaignParticipation.user_id == user.id,
                            CampaignParticipation.status == ParticipationStatus.validated,
                            func.date(CampaignParticipation.validated_at) == today,
                        )
                        .first()
                    )
                    if validated_today:
                        await reply_ephemeral(update, messages.campaign_already_validated_today())
                    else:
                        await reply_ephemeral(update, messages.campaign_participation_blocked())
                    return
                else:
                    part = svc.start_participation(camp, user)

        if part is None:
            return
        if camp is None:
            camp = db.query(Campaign).get(part.campaign_id)

        if not origin_username or origin_username.lower() != (camp.bot_username or "").lower():
            await reply_ephemeral(update, messages.forward_not_from_expected())
            part.status = ParticipationStatus.failed
            db.commit()
            return
        svc = CampaignService(db)
        svc.set_forward_and_generate_link(part, str(update.message.message_id))
        # Immediately process validation and payments (MVP):
        part.status = ParticipationStatus.validated
        part.validated_at = get_utc_time()
        db.commit()
        camp.amount_per_referral = camp.amount_per_referral or Decimal("0")
        if camp.balance >= camp.amount_per_referral:
            apr = camp.amount_per_referral
            # Compute payouts
            user_pct = Decimal(str(getattr(config, "PARTICIPATION_USER_REWARD_PERCENT", 75))) / Decimal("100")
            sponsor_pct = Decimal(str(getattr(config, "SPONSOR_PARTICIPATION_COMMISSION_PERCENT", 5))) / Decimal("100")
            user_reward = Decimal(str(apr * user_pct)).quantize(Decimal("0.000001"))
            sponsor_commission = Decimal(str(apr * sponsor_pct)).quantize(Decimal("0.000001"))

            # Deduct full APR from campaign balance to keep economic semantics
            camp.balance -= apr
            user.earn_balance += user_reward
            camp.referral_count += 1
            Transaction.create(
                db,
                user_id=user.id,
                type=TransactionType.task_reward,
                amount_trx=user_reward,
                balance_type=BalanceType.earn_balance,
                reference_id=str(part.id),
                description="Task reward validated",
            )


            # Sponsor commission (5% by default) + notify sponsor
            actual_sponsor_commission = Decimal("0")
            if user.sponsor_id:
                sponsor = db.query(User).filter(User.id == user.sponsor_id).first()
                if sponsor and sponsor_commission > 0:
                    ReferralService(db).pay_task_commission(
                        sponsor=sponsor,
                        referred_user=user,
                        amount_trx=apr,
                        percentage=sponsor_pct,
                        participation_id=part.id,
                    )
                    actual_sponsor_commission = sponsor_commission
                    # Notify sponsor
                    try:
                        spons_tid = int(sponsor.telegram_id)
                    except Exception:
                        spons_tid = sponsor.telegram_id
                    username = user.username or "user"
                    msg = (
                        f"🎉 *Commission Received*\n"
                        f"You have received {escape_markdown_v2(str(int(sponsor_pct * 100)))}% on a validated participation by @"
                        f"{escape_markdown_v2(username)}\n"
                        f"Amount\\: {format_trx_escaped(sponsor_commission)} TRX"
                    )
                    safe_notify_user(spons_tid, msg)

            # Credit admin with the remainder (APR - user_reward - actual_sponsor_commission)
            admin_remainder = (apr - user_reward - actual_sponsor_commission).quantize(Decimal("0.000001"))
            if admin_remainder > 0:
                admin_user = db.query(User).filter(User.telegram_id == str(config.TELEGRAM_ADMIN_ID)).first()
                if admin_user:
                    admin_user.earn_balance += admin_remainder
                    Transaction.create(
                        db,
                        user_id=admin_user.id,
                        type=TransactionType.task_reward,
                        amount_trx=admin_remainder,
                        balance_type=BalanceType.earn_balance,
                        reference_id=str(part.id),
                        description="Admin remainder from task reward",
                    )
                    msg = (
                        f"🎉 *Commission Received*\n"
                        f"Amount\\: {format_trx_escaped(admin_remainder)} TRX"
                    )
                    safe_notify_user(TELEGRAM_ADMIN_ID, msg)
            db.commit()
            await reply_ephemeral(update, messages.participation_validated(user_reward))
        else:
            await reply_ephemeral(update, messages.campaign_insufficient_balance())


async def on_campaign_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        # Delete the old message (the one with the inline button)
        try:
            await query.message.delete()
        except Exception:
            # If deletion fails, just continue
            pass
    index = context.user_data.get("browse_index", 0) + 1
    # Use message's chat to send next
    await _send_campaign(update, context, index=index)


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
        reason_enum = ReportReason[reason]
    except Exception:
        return
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        if not user:
            return
        CampaignReport.create(db, campaign_id=campaign_id, reporter_id=user.id, reason=reason_enum, description=None)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_markdown_v2(messages.report_saved())

