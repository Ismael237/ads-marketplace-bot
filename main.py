from __future__ import annotations

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor as APSchedulerThreadPoolExecutor
import atexit

import config
from utils.logger import get_logger
from database.database import init_database
from bot.handlers.campaigns import (
    create_campaign,
    pause_campaign,
    resume_campaign,
    recharge_campaign,
    on_create_campaign_callback,
    on_create_campaign_forward,
    on_my_ads_pagination,
    CREATE_CAMPAIGN_STATE_KEY,
    on_my_ads_actions,
    on_myads_recharge_callback,
    on_myads_recharge_text,
)
from bot.handlers.participation import browse_bots, forward_validator, on_campaign_skip, on_campaign_report, on_report_reason
from bot.handlers.wallet import deposit as wallet_deposit, on_copy_address, on_withdraw_callback, withdraw as wallet_withdraw
from bot.handlers.history import history, history_pagination
from bot.handlers.referral import referral as referral_handler
from bot.handlers.menu import handle_menu_selection
from bot.handlers.core import start
from workers.deposit_monitor import run_deposit_monitor
from workers.withdrawal_processor import run_withdrawal_processor


logger = get_logger("main")


async def route_forwarded(update, context):
    """Route forwarded messages to the correct flow depending on requester state."""
    state = context.user_data.get(CREATE_CAMPAIGN_STATE_KEY)
    try:
        if state == "ask_forward":
            await on_create_campaign_forward(update, context)
        else:
            await forward_validator(update, context)
    except Exception as e:
        logger.exception(f"Error in route_forwarded: {e}")
        # Fallback to participation handler to avoid losing the event
        try:
            await forward_validator(update, context)
        except Exception:
            pass


def running_application() -> Application:
    # 
    init_database()
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    # Core commands
    app.add_handler(CommandHandler("start", start))

    # Feature handlers
    app.add_handler(CommandHandler("create_campaign", create_campaign))
    app.add_handler(CommandHandler("pause_campaign", pause_campaign))
    app.add_handler(CommandHandler("resume_campaign", resume_campaign))
    app.add_handler(CommandHandler("recharge_campaign", recharge_campaign))

    # Participation handlers
    app.add_handler(CommandHandler("browse_bots", browse_bots))
    # Forwarded messages router
    app.add_handler(MessageHandler(filters.FORWARDED, route_forwarded))
    app.add_handler(CallbackQueryHandler(on_campaign_skip, pattern=r"^campaign_skip$"))
    app.add_handler(CallbackQueryHandler(on_campaign_report, pattern=r"^campaign_report:\d+$"))
    app.add_handler(CallbackQueryHandler(on_report_reason, pattern=r"^report_reason:(bot_inactive|spam|dead_link|other):\d+$"))
    
    # Wallet handlers
    app.add_handler(CommandHandler("deposit", wallet_deposit))
    app.add_handler(CommandHandler("withdraw", wallet_withdraw))
    app.add_handler(CallbackQueryHandler(on_withdraw_callback, pattern=r"^withdraw_(confirm|cancel)$"))
    app.add_handler(CallbackQueryHandler(on_copy_address, pattern=r"^copy:.+"))

    # Campaign creation inline callbacks
    app.add_handler(CallbackQueryHandler(on_create_campaign_callback, pattern=r"^create_campaign_(confirm|cancel)$"))
    # My Ads pagination
    app.add_handler(CallbackQueryHandler(on_my_ads_pagination, pattern=r"^myads_(prev|next)_\d+$"))
    # My Ads owner actions
    app.add_handler(CallbackQueryHandler(on_my_ads_actions, pattern=r"^myads_(toggle|recharge)_\d+$"))
    app.add_handler(CallbackQueryHandler(on_myads_recharge_callback, pattern=r"^myads_recharge_(preset_\d+|confirm|cancel)$"))

    # Pagination for history
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CallbackQueryHandler(history_pagination, pattern=r"^history_(?:all|deposits|investments|withdrawals)_page_\d+$"))
    
    # Referral handlers
    app.add_handler(CommandHandler("referral", referral_handler))
    
    # Menu handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_selection))

    logger.info("Bot is running...")
    app.run_polling()

def start_scheduler():
    jobstores = {'default': SQLAlchemyJobStore(url=config.DATABASE_URL)}
    executors = {'default': APSchedulerThreadPoolExecutor(5)}
    scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, timezone='UTC')
    # cron job
    scheduler.add_job(run_deposit_monitor, 'interval', minutes=1, id='monitor_deposits', replace_existing=True)
    scheduler.add_job(run_withdrawal_processor, 'interval', minutes=1, id='process_withdrawals', replace_existing=True)
    scheduler.start()
    logger.info("[Scheduler] APScheduler started with persistent jobs.")
    atexit.register(lambda: scheduler.shutdown())
    return scheduler 


def main():
    start_scheduler()
    running_application()


if __name__ == "__main__":
    main()


