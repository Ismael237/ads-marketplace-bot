from __future__ import annotations

from typing import Literal
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database.models import TransactionType
from bot.utils import reply_ephemeral
from bot.keyboards import pagination_inline_keyboard, history_reply_keyboard
from bot import messages
import config
from utils.helpers import escape_markdown_v2, get_separator, format_trx_escaped
from services.wallet_service import WalletService
from services.referral_service import ReferralService

HistoryFilter = Literal["all", "deposits", "ads", "withdrawals"]


def _filter_to_title(filter_key: HistoryFilter) -> str:
    return {
        "all": "All Transactions",
        "deposits": "Deposits",
        "ads": "ads",
        "withdrawals": "Withdrawals",
    }[filter_key]


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_ephemeral(update, messages.history_intro(), reply_markup=history_reply_keyboard())


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_key: HistoryFilter, page: int = 1):
    user = update.effective_user
    if not user:
        return
    page_size = int(getattr(config, "HISTORY_PAGE_SIZE", 3))

    # Resolve DB user id via service and fetch paginated transactions
    db_user_id = context.user_data.get("db_user_id")
    if not db_user_id:
        db_user = ReferralService.get_user_by_telegram_id(str(user.id))
        if not db_user:
            await reply_ephemeral(update, "Please /start first")
            return
        db_user_id = db_user.id
        context.user_data["db_user_id"] = db_user_id

    items, total_pages, page = WalletService.get_transactions_for_user(
        user_id=int(db_user_id),
        filter_key=filter_key,
        page=page,
        page_size=page_size,
    )

    # Render and send/edit page
    await _send_transactions_page(
        update=update,
        context=context,
        transactions=items,
        page=page,
        total_pages=total_pages,
        filter_key=filter_key,
    )


async def history_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    # pattern: history_(all|deposits|ads|withdrawals)_page_<n>
    data = query.data
    try:
        prefix, _, page_str = data.rpartition("_page_")
        _, filter_key = prefix.split("history_", 1)
        page = int(page_str)
    except Exception:
        return
    await show_history(update, context, filter_key=filter_key, page=page)


def _format_date(dt) -> str:
    """Format datetime for display and escape for MarkdownV2."""
    try:
        s = dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        s = str(dt)
    return escape_markdown_v2(s)


async def _send_transactions_page(update, context, transactions, page: int, total_pages: int, filter_key: str):
    """Render and send/edit a page of the user's transactions with emojis and MarkdownV2."""
    separator = get_separator()

    # Header
    title = _filter_to_title(filter_key)
    text_lines = [
        f"📝 *{escape_markdown_v2(title)}* \\(Page {page}/{total_pages}\\)\n",
        f"{separator}\n",
    ]

    emoji_map = {
        TransactionType.deposit.value: "➕",
        TransactionType.withdrawal.value: "➖",
        TransactionType.campaign_spend.value: "💼",
        TransactionType.task_reward.value: "💸",
        TransactionType.referral_commission.value: "🎁",
    }

    if not transactions:
        text_lines.append("No entries yet\\.")
    else:
        for tx in transactions:
            t_type_val = tx.type.value if hasattr(tx.type, "value") else str(tx.type)
            type_emoji = emoji_map.get(str(t_type_val), "🔹")
            amount_txt = format_trx_escaped(tx.amount_trx)
            date_txt = _format_date(getattr(tx, "created_at", ""))
            desc = getattr(tx, "description", None)
            if desc:
                desc = escape_markdown_v2(str(desc))

            text_lines.extend([
                f"  {type_emoji} *Type*\\: {escape_markdown_v2(str(t_type_val).replace('_', ' ').title())}\n",
                f"  📅 *Date*\\: `{date_txt}`\n",
                f"  💵 *Amount*\\: {amount_txt} TRX\n",
            ])
            if desc:
                text_lines.append(f"  📝 *Note*\\: _{desc}_\n")
            text_lines.append(f"{separator}\n")

    new_text = "".join(text_lines)
    keyboard = pagination_inline_keyboard(page, total_pages, f"history_{filter_key}")

    # Send or edit message
    if update.message:
        await update.message.reply_markdown_v2(new_text, reply_markup=keyboard)
    else:
        query = update.callback_query
        await query.edit_message_text(new_text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard)
