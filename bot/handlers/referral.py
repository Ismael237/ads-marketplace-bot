from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.utils import reply_ephemeral
from bot import messages
import config
from services.referral_service import ReferralService


async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ReferralService.get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        await reply_ephemeral(update, "Please /start first")
        return
    referral_count, total_earned = ReferralService.get_overview(user.id)
    text = messages.referral_overview(
        bot_username=context.bot.username,
        referral_code=user.referral_code,
        task_rate=config.SPONSOR_PARTICIPATION_COMMISSION_PERCENT,
        deposit_rate=config.SPONSOR_RECHARGE_COMMISSION_PERCENT,
        referral_count=referral_count,
        total_earned=total_earned,
    )
    await reply_ephemeral(update, text)
