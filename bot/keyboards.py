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
INFO_BTN = "ℹ️ Info"
FUND_BTN = "💰 Funds"

# Navigation Buttons
MAIN_MENU_BTN = "🏠 Main Menu"
BACK_BTN = "🔙 Back"
CANCEL_BTN = "❌ Cancel"
CANCEL_WITHDRAW_BTN = "❌ Cancel Withdrawal"
CANCEL_RECHARGE_BTN = "❌ Cancel Recharge"
SKIP_BTN = "⏭️ Skip"
CANCEL_CREATE_CAMPAIGN_BTN = "❌ Cancel Creation"
CONFIRM_RECHARGE_BTN = "✅ Confirm Recharge"
CONFIRM_CREATE_CAMPAIGN_BTN = "✅ Confirm Campaign"
CONFIRM_TRANSFER_BTN = "✅ Confirm Transfer"
CANCEL_TRANSFER_BTN = "❌ Cancel Transfer"

# Balance Submenu Buttons
VIEW_BALANCE_BTN = "💰 View Balance"
RECENT_ACTIVITY_BTN = "📊 Recent Activity"
CHECK_DEPOSIT_BTN = "🔄 Check Deposit"

# Withdraw Buttons
WITHDRAW_50_BTN = "50 TRX"
WITHDRAW_100_BTN = "100 TRX"
WITHDRAW_500_BTN = "500 TRX"
WITHDRAW_1000_BTN = "1,000 TRX"
WITHDRAW_5000_BTN = "5,000 TRX"

# Recharge Buttons
RECHARGE_1_BTN = "1 TRX"
RECHARGE_5_BTN = "5 TRX"
RECHARGE_10_BTN = "10 TRX"
RECHARGE_25_BTN = "25 TRX"
RECHARGE_50_BTN = "50 TRX"
RECHARGE_100_BTN = "100 TRX"
RECHARGE_MAX_BTN = "MAX"

# History Buttons
ALL_TRANSACTIONS_BTN = "📋 All Transactions"
DEPOSITS_ONLY_BTN = "📥 Deposits Only"
ADS_ONLY_BTN = "📈 Ads Only"
WITHDRAWALS_ONLY_BTN = "📤 Withdrawals Only"
TRANSFERS_ONLY_BTN = "🔁 Transfers Only"

# Transfer Buttons
TRANSFER_BTN = "🔁 Transfer to Ads"
TRANSFER_1_BTN = "1 TRX"
TRANSFER_5_BTN = "5 TRX"
TRANSFER_10_BTN = "10 TRX"
TRANSFER_25_BTN = "25 TRX"
TRANSFER_MAX_BTN = "MAX"

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
        [BROWSE_BTN, MY_ADS_BTN],
        [FUND_BTN, DEPOSIT_BTN, BALANCE_BTN],
        [REFERRAL_BTN, INFO_BTN],
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
        [ADS_ONLY_BTN, TRANSFERS_ONLY_BTN],
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
        [RECHARGE_1_BTN, RECHARGE_5_BTN, RECHARGE_10_BTN],
        [RECHARGE_25_BTN, RECHARGE_50_BTN, RECHARGE_100_BTN, RECHARGE_MAX_BTN],
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

def confirm_transfer_keyboard():
    """Show confirm/cancel for internal transfer"""
    keyboard = [
        [CONFIRM_TRANSFER_BTN],
        [CANCEL_TRANSFER_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def settings_reply_keyboard():
    """Settings submenu keyboard"""
    keyboard = [
        [REFERRAL_INFO_BTN, HELP_BTN],
        [SUPPORT_BTN, ABOUT_BTN, Q_A_BTN],
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
        [DEPOSIT_BTN],
        [WITHDRAW_BTN, BALANCE_BTN, HISTORY_BTN],
        [TRANSFER_BTN, CHECK_DEPOSIT_BTN],
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


def campaign_manage_keyboard(is_active: bool, camp_id: int):
    """Create keyboard for campaign management with toggle and edit options"""
    buttons = [
        [
            InlineKeyboardButton("⏸️ Pause" if is_active else "▶️ Resume", 
                              callback_data=f"campaign_toggle"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"campaign_edit_{camp_id}")
        ],
        [InlineKeyboardButton("🔙 Back to My Ads", callback_data="back_to_my_ads")]
    ]
    return InlineKeyboardMarkup(buttons)


def title_step_keyboard(is_edit_flow: bool = False):
    """Title step keyboard with Skip and Cancel for both create and edit flows"""
    keyboard = [
        [SKIP_BTN] if not is_edit_flow else [],
        [CANCEL_BTN]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )


def edit_campaign_keyboard(camp_id: int):
    """Inline keyboard for campaign edit options"""
    buttons = [
        [InlineKeyboardButton("✏️ Edit Title", callback_data=f"edit_title_{camp_id}")],
        [InlineKeyboardButton("🔗 Edit Bot Link", callback_data=f"edit_botlink_{camp_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"back_to_campaign_{camp_id}")]
    ]
    return InlineKeyboardMarkup(buttons)


def cancel_edit_keyboard(camp_id: int):
    """Inline keyboard to cancel editing and return to campaign view"""
    buttons = [
        [InlineKeyboardButton("❌ Cancel", callback_data=f"back_to_campaign_{camp_id}")]
    ]
    return InlineKeyboardMarkup(buttons)


def wallet_menu_keyboard(deposit_address: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text="Copy Deposit Address", callback_data=f"copy:{deposit_address}")],
        [InlineKeyboardButton(text="🔄 Check Deposit", callback_data="check_deposit")]
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
    """Reply keyboard for confirming or canceling campaign creation."""
    keyboard = [
        [CONFIRM_CREATE_CAMPAIGN_BTN],
        [CANCEL_CREATE_CAMPAIGN_BTN],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def transfer_reply_keyboard():
    """Transfer submenu with predefined amounts"""
    keyboard = [
        [TRANSFER_1_BTN, TRANSFER_5_BTN],
        [TRANSFER_10_BTN, TRANSFER_25_BTN, TRANSFER_MAX_BTN],
        [CANCEL_TRANSFER_BTN],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )
