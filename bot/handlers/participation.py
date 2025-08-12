from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

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
from services.referral_service import ReferralService
import config
from decimal import Decimal
from services.campaign_service import CampaignService
from bot.keyboards import campaigns_browse_keyboard, report_reasons_keyboard
from bot.utils import reply_ephemeral
from bot import messages


async def _send_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int = 0):
    with get_db_session() as db:
        q = db.query(Campaign).filter(Campaign.is_active == True).order_by(Campaign.id.desc())
        campaigns = q.all()
        if not campaigns:
            await reply_ephemeral(update, "No active campaigns")
            return
        if index >= len(campaigns):
            index = 0
        camp = campaigns[index]
        context.user_data["browse_index"] = index
        kb = campaigns_browse_keyboard(camp.bot_link, camp.id)
        text = messages.browse_campaign(camp.title, camp.bot_username, camp.amount_per_referral)
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
                # ensure user can participate once
                if svc.can_user_participate(camp, user):
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
        db.commit()
        camp.amount_per_referral = camp.amount_per_referral or Decimal("0")
        if camp.balance >= camp.amount_per_referral:
            camp.balance -= camp.amount_per_referral
            user.earn_balance += camp.amount_per_referral
            camp.referral_count += 1
            Transaction.create(
                db,
                user_id=user.id,
                type=TransactionType.task_reward,
                amount_trx=camp.amount_per_referral,
                balance_type=BalanceType.earn_balance,
                reference_id=str(part.id),
                description="Task reward validated",
            )
            # Sponsor commission
            if user.sponsor_id:
                sponsor = db.query(User).filter(User.id == user.sponsor_id).first()
                if sponsor:
                    ReferralService(db).pay_task_commission(
                        sponsor=sponsor,
                        referred_user=user,
                        amount_trx=camp.amount_per_referral,
                        percentage=Decimal(str(config.REFERRAL_COMMISSION_RATE)),
                        participation_id=part.id,
                    )
            db.commit()
            await reply_ephemeral(update, messages.participation_validated(camp.amount_per_referral))
        else:
            await reply_ephemeral(update, messages.campaign_insufficient_balance())


async def on_campaign_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
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


def get_handlers():
    return [

    ]


