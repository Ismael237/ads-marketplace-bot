from __future__ import annotations

from telegram.ext import ContextTypes, CommandHandler

from database.database import get_db_session
from database.models import User
from utils.helpers import generate_referral_code
from bot.keyboards import main_reply_keyboard
from bot import messages
from bot.utils import reply_ephemeral


async def start(update, context: ContextTypes.DEFAULT_TYPE):
    # Create user if not exists
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        if not user:
            # Sponsor handling via /start <referral_code>
            sponsor_id = None
            if context.args:
                ref = context.args[0]
                sponsor = db.query(User).filter(User.referral_code == ref).first()
                if sponsor:
                    sponsor_id = sponsor.id
            user = User.create(
                db,
                telegram_id=str(update.effective_user.id),
                username=update.effective_user.username or None,
                referral_code=generate_referral_code(),
                sponsor_id=sponsor_id,
            )
    await reply_ephemeral(update, messages.welcome(context.bot.username), reply_markup=main_reply_keyboard())
