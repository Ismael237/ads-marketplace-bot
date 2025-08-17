from __future__ import annotations

from telegram.ext import ContextTypes

from services.referral_service import ReferralService
from bot.keyboards import main_reply_keyboard
from bot import messages
from bot.utils import reply_ephemeral


async def start(update, context: ContextTypes.DEFAULT_TYPE):
    # Ensure user exists (creates with optional sponsor from referral code)
    sponsor_ref = context.args[0] if context.args else None
    ReferralService.ensure_user(
        telegram_id=str(update.effective_user.id),
        username=update.effective_user.username or None,
        sponsor_referral_code=sponsor_ref,
    )
    await reply_ephemeral(update, messages.welcome(context.bot.username), reply_markup=main_reply_keyboard())
