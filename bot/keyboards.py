from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
import config

# ==================== CONSTANTS ====================
# Main Menu Buttons (MVP)
BROWSE_BTN = "📣 Browse"
BALANCE_BTN = "💳 Balance"
MY_ADS_BTN = "📢 My Ads"
DEPOSIT_BTN = "💰 Deposit"
WITHDRAW_BTN = "🏧 Withdraw"
REFERRAL_BTN = "👥 Referral"
HISTORY_BTN = "📜 History"
SETTINGS_BTN = "⚙️ Settings"
WALLET_BTN = "💼 Wallet"

# Navigation Buttons
MAIN_MENU_BTN = "🏠 Main Menu"
BACK_BTN = "🔙 Back"
CANCEL_BTN = "❌ Cancel"
CANCEL_WITHDRAW_BTN = "❌ Cancel Withdrawal"
CANCEL_RECHARGE_BTN = "❌ Cancel Recharge"
SKIP_BTN = "⏭️ Skip"
CANCEL_CREATE_CAMPAIGN_BTN = "❌ Cancel Creation"

# Balance Submenu Buttons
VIEW_BALANCE_BTN = "💰 View Balance"
RECENT_ACTIVITY_BTN = "📊 Recent Activity"

# Withdraw Buttons
WITHDRAW_50_BTN = "50 TRX"
WITHDRAW_100_BTN = "100 TRX"
WITHDRAW_500_BTN = "500 TRX"
WITHDRAW_1000_BTN = "1,000 TRX"
WITHDRAW_5000_BTN = "5,000 TRX"

# Recharge Buttons
RECHARGE_10_BTN = "10 TRX"
RECHARGE_50_BTN = "50 TRX"
RECHARGE_100_BTN = "100 TRX"
CONFIRM_RECHARGE_BTN = "✅ Confirm Recharge"

# History Buttons
ALL_TRANSACTIONS_BTN = "📋 All Transactions"
DEPOSITS_ONLY_BTN = "📥 Deposits Only"
INVESTMENTS_ONLY_BTN = "📈 Investments Only"
WITHDRAWALS_ONLY_BTN = "📤 Withdrawals Only"

# Settings Buttons
HELP_BTN = "❓ Help"
SUPPORT_BTN = "🆘 Support"
ABOUT_BTN = "ℹ️ About"
Q_A_BTN = "🤔 Q&A"
REFERRAL_INFO_BTN = "👥 Referral Info"
ADS_CREATE_BTN = "➕ Create Ad"
ADS_LIST_BTN = "📑 List My Ads"

# ==================== REPLY KEYBOARDS ====================

def main_reply_keyboard():
    """Main menu keyboard with primary bot functions (persistent)."""
    keyboard = [
        [BROWSE_BTN, BALANCE_BTN],
        [MY_ADS_BTN],
        [WALLET_BTN, REFERRAL_BTN],
        [SETTINGS_BTN],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def cancel_create_campaign_keyboard():
    """Cancel campaign creation keyboard"""
    keyboard = [
        [CANCEL_CREATE_CAMPAIGN_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def withdraw_reply_keyboard():
    """Withdraw submenu with predefined amounts"""
    keyboard = [
        [WITHDRAW_50_BTN],
        [WITHDRAW_100_BTN, WITHDRAW_500_BTN],
        [WITHDRAW_1000_BTN, WITHDRAW_5000_BTN],
        [MAIN_MENU_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def cancel_withdraw_keyboard():
    """Cancel withdrawal keyboard"""
    keyboard = [
        [CANCEL_WITHDRAW_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def cancel_recharge_keyboard():
    """Cancel recharge keyboard"""
    keyboard = [
        [CANCEL_RECHARGE_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def history_reply_keyboard():
    """History submenu keyboard"""
    keyboard = [
        [ALL_TRANSACTIONS_BTN],
        [DEPOSITS_ONLY_BTN, WITHDRAWALS_ONLY_BTN],
        [MAIN_MENU_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def recharge_reply_keyboard():
    """Recharge submenu with predefined amounts"""
    keyboard = [
        [RECHARGE_10_BTN],
        [RECHARGE_50_BTN, RECHARGE_100_BTN],
        [CANCEL_RECHARGE_BTN],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def confirm_recharge_keyboard():
    """Show confirm/cancel for recharge"""
    keyboard = [
        [CONFIRM_RECHARGE_BTN],
        [CANCEL_RECHARGE_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def settings_reply_keyboard():
    """Settings submenu keyboard"""
    keyboard = [
        [HELP_BTN, SUPPORT_BTN],
        [ABOUT_BTN, Q_A_BTN],
        [REFERRAL_INFO_BTN],
        [MAIN_MENU_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def wallet_reply_keyboard():
    """Wallet submenu keyboard: Deposit, Withdraw, History"""
    keyboard = [
        [DEPOSIT_BTN, WITHDRAW_BTN],
        [HISTORY_BTN],
        [MAIN_MENU_BTN],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def ads_reply_keyboard():
    """Ads submenu keyboard"""
    keyboard = [
        [ADS_CREATE_BTN, ADS_LIST_BTN],
        [MAIN_MENU_BTN],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def transaction_details_inline_keyboard(tx_hash=None):
    """Inline keyboard for transaction details"""
    keyboard = []
    
    if tx_hash:
        keyboard.append([InlineKeyboardButton("🔍 View on Blockchain", url=f"{config.TRON_EXPLORER_URL}/#/transaction/{tx_hash}")])
    
    return InlineKeyboardMarkup(keyboard)

def pagination_inline_keyboard(current_page, total_pages, callback_prefix):
    """Generic pagination keyboard"""
    keyboard = []
    
    # Navigation row
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"{callback_prefix}_page_{current_page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data="current_page"))
    
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"{callback_prefix}_page_{current_page+1}"))
    
    keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(keyboard)

def campaigns_browse_keyboard(bot_link: str, campaign_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text="🤖 Message Bot", url=bot_link),
        ],
        [
            InlineKeyboardButton(text="🚨 Report", callback_data=f"campaign_report:{campaign_id}"),
            InlineKeyboardButton(text="⏭️ Skip", callback_data="campaign_skip"),
        ],
    ])


def withdraw_button():
    return InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")

def referral_info_inline_keyboard():
    """Creates an inline keyboard with a button to show referral system info"""
    keyboard = [
        [
            InlineKeyboardButton(
                "❓ How It Works",
                callback_data="referral_info"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def campaign_manage_keyboard(is_active: bool):
    if is_active:
        btn = InlineKeyboardButton(text="Pause", callback_data="campaign_pause")
    else:
        btn = InlineKeyboardButton(text="Resume", callback_data="campaign_resume")
    return InlineKeyboardMarkup([[btn]])


def title_step_keyboard():
    """Title step keyboard with Skip and Cancel"""
    keyboard = [
        [SKIP_BTN],
        [CANCEL_CREATE_CAMPAIGN_BTN],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def wallet_menu_keyboard(deposit_address: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text="Copy Deposit Address", callback_data=f"copy:{deposit_address}")]
    ])


def report_reasons_keyboard(campaign_id: int):
    """Inline keyboard to choose a report reason for a campaign."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text="Bot inactive", callback_data=f"report_reason:bot_inactive:{campaign_id}")],
        [InlineKeyboardButton(text="Spam", callback_data=f"report_reason:spam:{campaign_id}")],
        [InlineKeyboardButton(text="Dead link", callback_data=f"report_reason:dead_link:{campaign_id}")],
        [InlineKeyboardButton(text="Other", callback_data=f"report_reason:other:{campaign_id}")],
    ])


def withdraw_confirm_inline_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text="✅ Confirm Withdrawal", callback_data="withdraw_confirm")],
        [InlineKeyboardButton(text="❌ Cancel Withdrawal", callback_data="withdraw_cancel")],
    ])


def create_campaign_confirm_inline_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text="✅ Confirm", callback_data="create_campaign_confirm")],
        [InlineKeyboardButton(text="❌ Cancel Creation", callback_data="create_campaign_cancel")],
    ])


