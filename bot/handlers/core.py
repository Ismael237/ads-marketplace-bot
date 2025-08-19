from __future__ import annotations

from telegram.ext import ContextTypes

from services.referral_service import ReferralService
from bot.keyboards import main_reply_keyboard
from bot import messages
from bot.utils import reply_ephemeral, safe_notify_user
from database.database import get_db_session
from database.models import User


async def start(update, context: ContextTypes.DEFAULT_TYPE):
    # Ensure user exists (creates with optional sponsor from referral code)
    sponsor_ref = context.args[0] if context.args else None
    # Check if this is a new user before ensuring creation
    existed = ReferralService.get_user_by_telegram_id(str(update.effective_user.id)) is not None
    ReferralService.ensure_user(
        telegram_id=str(update.effective_user.id),
        username=update.effective_user.username or None,
        sponsor_referral_code=sponsor_ref,
    )
    # If newly created and linked to a sponsor, notify the sponsor
    if not existed:
        # Reload user to access sponsor_id
        user = ReferralService.get_user_by_telegram_id(str(update.effective_user.id))
        if user and getattr(user, "sponsor_id", None):
            with get_db_session() as db:
                sponsor = db.query(User).get(int(user.sponsor_id))
                if sponsor and sponsor.telegram_id:
                    username = update.effective_user.username
                    first_name = getattr(update.effective_user, "first_name", None)
                    display_label = f"@{username}" if username else (first_name or None)
                    notif = messages.sponsor_new_referral_notification(display_label)
                    safe_notify_user(sponsor.telegram_id, notif)
    await reply_ephemeral(update, messages.welcome(context.bot.username), reply_markup=main_reply_keyboard())
