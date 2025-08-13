from telegram import Update
from telegram.constants import ParseMode
from utils.logger import get_logger
import asyncio
from telegram import Bot, ReplyKeyboardMarkup
from config import TELEGRAM_BOT_TOKEN
from utils.helpers import escape_markdown_v2


logger = get_logger("bot.utils")


async def reply_ephemeral(update: Update, text: str, reply_markup: ReplyKeyboardMarkup = None, disable_web_page_preview: bool = False):
    if update.effective_message:
        await update.effective_message.reply_markdown_v2(text, reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)


def get_user_identity(update: Update):
    user = update.effective_user
    if not user:
        return None
    return {
        "telegram_id": str(user.id),
        "username": user.username or None,
    }


# Initialize Telegram Bot for notifications
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def notify_user(telegram_id: str, message: str, reply_markup: ReplyKeyboardMarkup = None) -> None:
    """Send a Markdown-v2 formatted message to the given Telegram user, if possible."""
    if not telegram_id:
        return
    try:
        await bot.send_message(chat_id=telegram_id, text=(message), parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"[Notify] Failed to send message to {telegram_id}: {e}")

def safe_notify_user(telegram_id: int, message: str, reply_markup: ReplyKeyboardMarkup = None):
    try:
        # Python ≥3.7: create a new loop if none exists (e.g. in thread)
        loop = asyncio.get_event_loop()
    except RuntimeError as e:
        if "There is no current event loop" in str(e):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            raise

    try:
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                notify_user(telegram_id, message, reply_markup), loop
            )
        else:
            loop.run_until_complete(notify_user(telegram_id, message, reply_markup))
    except Exception as e:
        # log this error instead of retrying recursively
        logger.error(f"[Notify] Failed to notify {telegram_id}: {e}")