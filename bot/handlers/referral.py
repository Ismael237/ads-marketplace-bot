from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database.database import get_db_session
from database.models import User
from bot.utils import reply_ephemeral
from bot import messages
import config


async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        if not user:
            await reply_ephemeral(update, "Please /start first")
            return
        text = messages.referral_overview(
            bot_username=context.bot.username,
            referral_code=user.referral_code,
            task_rate=config.REFERRAL_COMMISSION_RATE,
            deposit_rate=config.DEPOSIT_COMMISSION_RATE,
        )
        await reply_ephemeral(update, text)
