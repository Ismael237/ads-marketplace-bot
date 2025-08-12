from __future__ import annotations

from math import ceil
from typing import Literal
from decimal import Decimal
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database.database import get_db_session
from database.models import Transaction, TransactionType
from bot.utils import reply_ephemeral
from bot.keyboards import pagination_inline_keyboard, history_reply_keyboard
from bot import messages
import config

HistoryFilter = Literal["all", "deposits", "investments", "withdrawals"]


def _filter_to_title(filter_key: HistoryFilter) -> str:
    return {
        "all": "All Transactions",
        "deposits": "Deposits",
        "investments": "Investments",
        "withdrawals": "Withdrawals",
    }[filter_key]


def _apply_filter(q, filter_key: HistoryFilter):
    if filter_key == "all":
        return q
    if filter_key == "deposits":
        return q.filter(Transaction.type == TransactionType.deposit)
    if filter_key == "investments":
        # No explicit 'investment' type in TransactionType; use campaign_spend for advertiser spend
        return q.filter(Transaction.type == TransactionType.campaign_spend)
    if filter_key == "withdrawals":
        return q.filter(Transaction.type == TransactionType.withdrawal)
    return q


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_ephemeral(update, messages.history_intro(), reply_markup=history_reply_keyboard())


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_key: HistoryFilter, page: int = 1):
    user = update.effective_user
    if not user:
        return
    page_size = int(getattr(config, "HISTORY_PAGE_SIZE", 10))
    # Query user transactions
    with get_db_session() as db:
        base_q = db.query(Transaction).filter(Transaction.user_id == context.user_data.get("db_user_id", 0))
        # Fallback: try to resolve by telegram id if not cached
        if not context.user_data.get("db_user_id"):
            # Lazy lookup and cache
            from database.models import User  # local import to avoid cycle
            u = db.query(User).filter(User.telegram_id == str(user.id)).first()
            if not u:
                await reply_ephemeral(update, "Please /start first")
                return
            context.user_data["db_user_id"] = u.id
            base_q = db.query(Transaction).filter(Transaction.user_id == u.id)

        q = _apply_filter(base_q, filter_key)
        total = q.count()
        total_pages = max(1, ceil(total / page_size))
        page = max(1, min(page, total_pages))
        items = (
            q.order_by(Transaction.id.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
             .all()
        )

    # Build lines
    lines: list[str] = []
    for t in items:
        t_type = t.type.value if hasattr(t.type, 'value') else str(t.type)
        amount = Decimal(t.amount_trx)
        lines.append(f"{t_type} · {amount} TRX")

    text = messages.history_list(_filter_to_title(filter_key), lines)
    kb = pagination_inline_keyboard(page, total_pages, callback_prefix=f"history_{filter_key}")

    # If called from a message (not callback)
    if update.effective_message and not update.callback_query:
        await update.effective_message.reply_markdown_v2(text, reply_markup=kb)
        return

    # From callback: edit message
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)


async def history_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    # pattern: history_(all|deposits|investments|withdrawals)_page_<n>
    data = query.data
    try:
        prefix, _, page_str = data.rpartition("_page_")
        _, filter_key = prefix.split("history_", 1)
        page = int(page_str)
    except Exception:
        return
    await show_history(update, context, filter_key=filter_key, page=page)
