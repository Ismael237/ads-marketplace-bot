from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from sqlalchemy import func

from database.database import get_db_session
from database.models import User, ReferralCommission
from bot.utils import reply_ephemeral
from bot import messages
import config


async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        if not user:
            await reply_ephemeral(update, "Please /start first")
            return
        # Compute referral stats
        referral_count = db.query(User).filter(User.sponsor_id == user.id).count()
        total_earned = db.query(func.coalesce(func.sum(ReferralCommission.amount_trx), 0)).filter(ReferralCommission.user_id == user.id).scalar()
        text = messages.referral_overview(
            bot_username=context.bot.username,
            referral_code=user.referral_code,
            task_rate=config.SPONSOR_PARTICIPATION_COMMISSION_PERCENT,
            deposit_rate=config.SPONSOR_RECHARGE_COMMISSION_PERCENT,
            referral_count=referral_count,
            total_earned=total_earned,
        )
        await reply_ephemeral(update, text)
