from decimal import Decimal
from typing import Optional
import config
from utils.helpers import escape_markdown_v2, generate_share_link, get_separator, format_trx_escaped


def _esc(text: str) -> str:
    """Escape dynamic text for MarkdownV2 with double backslashes as requested."""
    if text is None:
        return ""
    once = escape_markdown_v2(str(text))
    return once


def welcome(bot_username: str) -> str:
    sep = get_separator()
    return (
        "🎉 Welcome to the Campaign Marketplace Bot\n"
        f"{sep}\n"
        "🧭 Use the menu below to browse campaigns, deposit TRX, withdraw earnings, and manage referrals\\.\n\n"
        f"🆘 Need help? Contact @{_esc(config.TELEGRAM_ADMIN_USERNAME) if config.TELEGRAM_ADMIN_USERNAME else 'admin'}"
    )


def deposit_instructions(address: str) -> str:
    sep = get_separator()
    return (
        "💰 Deposit TRX\n"
        f"{sep}\n"
        "Click to copy your deposit address:\n\n"
        f"`{_esc(address)}`\n\n"
        "⏳ Your balance is credited after automatic confirmations\\."
    )


def deposit_copied(address: str) -> str:
    return (
        "📋 Copy the address below:\n"
        f"`{_esc(address)}`"
    )


def withdraw_ask_amount(min_withdrawal: Decimal, current_earn_balance: Decimal) -> str:
    sep = get_separator()
    return (
        "🏧 Withdraw TRX\n"
        f"{sep}\n"
        f"Minimum: `{format_trx_escaped(min_withdrawal)} TRX`\n"
        f"Your balance: `{format_trx_escaped(current_earn_balance)} TRX`\n"
        "Select an amount or enter a custom amount \\(e\\.g\\. 12\\.5\\):"
    )


def withdraw_ask_address(amount: Decimal) -> str:
    return (
        "📮 Enter the destination TRON address \\(starts with T\\):\n"
        f"Amount: `{format_trx_escaped(amount)} TRX`"
    )


def withdraw_confirm(amount: Decimal, to_address: str, fee_rate: Optional[Decimal] = None) -> str:
    sep = get_separator()
    fee_txt = ""
    if fee_rate is not None and fee_rate > 0:
        fee_txt = f"\nFee: `{format_trx_escaped(Decimal(amount) * Decimal(fee_rate))} TRX`"
    return (
        "✅ Please confirm your withdrawal:\n"
        f"{sep}\n"
        f"Amount: `{format_trx_escaped(amount)} TRX`\n"
        f"To: `{_esc(to_address)}`\n"
        f"{fee_txt}"
    )


def withdraw_cancelled() -> str:
    return "❌ Withdrawal cancelled\\."


def browse_campaign(camp_title: str, amount_per_referral: Decimal) -> str:
    sep = get_separator()
    return (
        "📣 Campaign\n"
        f"{sep}\n"
        f"Title: `{_esc(camp_title)}`\n"
        f"Reward per task: `{format_trx_escaped(amount_per_referral)} TRX`\n\n"
        "1️⃣ Tap Message Bot to start\\.\n"
        "2️⃣ Forward a recent message back here to participate\\.\n"
    )


def forward_not_from_expected() -> str:
    return "⚠️ The forwarded message is not from the expected bot\\."


def forward_context_missing() -> str:
    return (
        "⚠️ No campaign in context\\.\n"
        "Please browse a campaign from the menu, tap Message Bot, then forward a recent message here\."
    )


def participation_validated(amount: Decimal) -> str:
    return f"🎉 Task validated\\! Earned `{format_trx_escaped(amount)} TRX`"


def campaign_insufficient_balance() -> str:
    return "⛔ The campaign has insufficient balance\\."


def referral_overview(bot_username: str, referral_code: str, task_rate: float, deposit_rate: float, referral_count: int, total_earned: Decimal) -> str:
    sep = get_separator()
    link = generate_share_link(bot_username, referral_code)
    task_rate = _esc(task_rate)
    deposit_rate = _esc(deposit_rate)
    return (
        "👥 Referral Program\n"
        f"{sep}\n"
        f"Your referral link\\(click to copy\\):\n\n"
        f"`{_esc(link)}`\n\n"
        f"Stats:\n"
        f"• Referrals: `{referral_count}`\n"
        f"• Total earned: `{format_trx_escaped(total_earned)} TRX`\n\n"
        f"Commissions:\n"
        f"• Tasks: `{task_rate}%`\n"
        f"• Ads spending: `{deposit_rate}%`"
    )


def report_choose_reason() -> str:
    return "🚩 Choose a reason to report this campaign:"


def report_saved() -> str:
    return "✅ Report submitted\\. Thank you for your feedback\\."


def balance_overview(earn_balance: Decimal, ad_balance: Decimal) -> str:
    sep = get_separator()
    return (
        "💳 Balance\n"
        f"{sep}\n"
        f"Earnings: `{format_trx_escaped(earn_balance)} TRX`\n"
        f"Advertising: `{format_trx_escaped(ad_balance)} TRX`"
    )


def history_intro() -> str:
    sep = get_separator()
    return (
        "📜 History\n"
        f"{sep}\n"
        "Choose a filter below to view your transactions\\."
    )


def history_list(title: str, lines: list[str]) -> str:
    sep = get_separator()
    body = "\n".join(_esc(line) for line in lines) if lines else "No entries yet\\."
    return (
        f"📜 { _esc(title) }\n"
        f"{sep}\n"
        f"{body}"
    )


def settings_info(admin_username: Optional[str]) -> str:
    sep = get_separator()
    admin = f"@{_esc(admin_username)}" if admin_username else "N/A"
    return (
        "⚙️ Settings\n"
        f"{sep}\n"
        f"Support: {admin}\n"
        "About: Campaign Marketplace Bot on TRON"
    )


# ==================== Campaign Creation (Multi-step) ====================
def create_campaign_ask_link() -> str:
    sep = get_separator()
    return (
        "🆕 Create Campaign\n"
        f"{sep}\n"
        "Send the target bot link or username\n"
        "Examples: `https://t\.me/MyBot?start\=referral_code`\n\n"
        "You can cancel anytime\\."
    )


def create_campaign_ask_forward(bot_link: str) -> str:
    return (
        "📨 Please forward a recent message from the target bot here to verify it works\n"
        "Bot link:\n"
        f"{_esc(bot_link)}"
    )


def create_campaign_ask_title(default_title: str) -> str:
    sep = get_separator()
    return (
        "📝 Enter a campaign title, or tap Skip to use the default title\n"
        f"{sep}\n"
        f"Default: `{_esc(default_title)}`"
    )


def create_campaign_confirm(bot_link: str, bot_username: str, amount_per_referral: Decimal, title: str) -> str:
    sep = get_separator()
    return (
        "✅ Confirm Campaign\n"
        f"{sep}\n"
        f"Title: `{_esc(title)}`\n"
        f"Bot: `@{_esc(bot_username)}`\n"
        f"Link: `{_esc(bot_link)}`\n"
        f"Reward per referral: `{format_trx_escaped(amount_per_referral)} TRX`\n\n"
        "Tap the Confirm or Cancel button below\\."
    )


def create_campaign_cancelled() -> str:
    return "❌ Campaign creation cancelled\\."


def create_campaign_created() -> str:
    sep = get_separator()
    return (
        "🎉 Campaign Created Successfully\n"
        f"{sep}\n"
        "⚡️ Click the Recharge button to add funds and activate your campaign\\!"
    )


# ==================== Campaign Editing ====================

def edit_campaign_ask_title() -> str:
    """Prompt user to enter a new campaign title"""
    return (
        "✏️ *Edit Campaign Title*\n\n"
        "Please enter the new title for your campaign:"
    )


def edit_campaign_title_updated() -> str:
    """Notification when campaign title is successfully updated"""
    return "✅ *Title Updated*\n\nYour campaign title has been updated successfully!"


def edit_campaign_ask_bot_link() -> str:
    """Prompt user to enter a new bot link"""
    return (
        "🔗 *Update Bot Link*\n\n"
        "Please send me the new bot link (e.g., https://t.me/yourbot or @yourbot):\n\n"
        "⚠️ The bot must be public and you must be able to forward messages from it."
    )


def edit_campaign_ask_forward_verification(bot_username: str) -> str:
    """Ask user to forward a message from the bot for verification"""
    return (
        f"🔍 *Verification Required*\n\n"
        f"Please forward a message from @{bot_username} to verify ownership.\n\n"
        f"1. Open the bot you want to link\n"
        f"2. Send any message to the bot\n"
        f"3. Forward that message here"
    )


def edit_campaign_bot_link_updated() -> str:
    """Notification when bot link is successfully updated"""
    return "✅ *Bot Link Updated*\n\nYour bot link has been updated successfully!"


def edit_campaign_invalid_bot_username() -> str:
    """Error message for invalid bot username format"""
    return (
        "❌ *Invalid Bot Username*\n\n"
        "Please provide a valid bot link or username. It should be in the format:\n"
        "• `https://t.me/yourbot`\n"
        "• `@yourbot`\n"
        "• or just `yourbot`"
    )


def edit_campaign_forward_verification_failed() -> str:
    """Error message when forward verification fails"""
    return (
        "❌ *Verification Failed*\n\n"
        "The forwarded message must be from the bot you're trying to link. "
        "Please make sure to forward a message directly from that bot."
    )


def edit_campaign_forward_not_from_bot() -> str:
    """Error message when forwarded message is not from a bot"""
    return (
        "❌ *Not a Bot*\n\n"
        "The forwarded message must be from a bot account, not a regular user. "
        "Please try again with a message from a bot."
    )


def edit_campaign_session_expired() -> str:
    """Error message when edit session expires"""
    return "❌ Session expired. Please try the edit operation again."


# ==================== My Ads (Owner view) ====================
def my_ad_overview(title: str, bot_username: str, bot_link: str, amount_per_referral: Decimal, balance: Decimal, is_active: bool, referral_count: int, idx: int, total: int) -> str:
    sep = get_separator()
    status_emoji = "🟢" if is_active else "⏸️"
    status_text = "Active" if is_active else "Paused"
    return (
        f"📢 My Ad \\({idx}/{total}\\)\n"
        f"{sep}\n"
        f"Title: `{_esc(title)}`\n"
        f"Bot: `@{_esc(bot_username)}`\n"
        f"Link: `{_esc(bot_link)}`\n"
        f"Reward per referral: `{format_trx_escaped(amount_per_referral)} TRX`\n"
        f"Balance: `{format_trx_escaped(balance)} TRX`\n"
        f"Referrals: `{referral_count}`\n"
        f"Status: {status_emoji} {status_text}"
    )


def myads_recharge_ask_amount(current_ad_balance: Decimal) -> str:
    return (
        f"Your ad balance: `{format_trx_escaped(current_ad_balance)} TRX`\n"
        "You can cancel anytime\.\n"
        "🔋 Enter amount to recharge this ad, or choose a preset below:"
    )


def myads_recharge_confirm(amount: Decimal) -> str:
    return (
        "✅ Confirm Recharge\n"
        f"Amount: `{format_trx_escaped(amount)} TRX`"
    )


def myads_recharge_done(amount: Decimal) -> str:
    return (
        f"✅ Recharged campaign by `{format_trx_escaped(amount)} TRX`"
    )


def myads_recharge_cancelled() -> str:
    return "❌ Recharge cancelled\."


# ==================== Broadcasts ====================
def campaign_activated_broadcast() -> str:
    """Stylish, engaging message to notify all users when a campaign gets recharged and activated."""
    sep = get_separator()
    return (
        "🚀 New campaign activated\\!\n"
        f"{sep}\n"
        "Participate now and earn TRX\\! 🤑\n"
        "Browse campaigns from the menu to start\."
    )


# ==================== Participation Validation Messages ====================
def campaign_not_active() -> str:
    return "⚠️ This campaign is currently inactive and cannot be participated in\."


def campaign_owner_cannot_participate() -> str:
    return "🚫 You cannot participate in your own campaigns\."


def campaign_already_validated_today() -> str:
    return "⏰ You have already validated this campaign today\. Please try again tomorrow\."


def campaign_participation_blocked() -> str:
    return "🔒 You cannot participate in this campaign at the moment\. Please try a different campaign\."


# ==================== Internal Transfer (earn -> ad) ====================
def transfer_ask_amount(current_earn_balance: Decimal, fee_rate: float) -> str:
    sep = get_separator()
    return (
        "💫 Transfer to Advertising Balance\n"
        f"{sep}\n"
        f"Available: `{format_trx_escaped(current_earn_balance)} TRX`\n"
        f"Transfer Fee: `{_esc(fee_rate * 100)}%`\n"
        "Minimum Transfer: `1 TRX`\n"
        f"{sep}\n"
        "🔢 Enter amount or use quick options below\.\n"
        "ℹ️ *Note:* Whole numbers only"
    )


def transfer_confirm(amount: Decimal, fee_rate: float) -> str:
    from decimal import Decimal as D
    sep = get_separator()
    amt = D(str(amount))
    fee = (amt * D(str(fee_rate)))
    net = amt - fee
    return (
        "💱 *Transfer Confirmation*\n"
        f"{sep}\n"
        f"💰 Amount: `{format_trx_escaped(amt)} TRX`\n" 
        f"📝 Fee: `{format_trx_escaped(fee)} TRX`\n"
        f"✨ Net to ads: `{format_trx_escaped(net)} TRX`\n\n"
        "⚠️ _This operation cannot be undone_"
    )


def transfer_done(amount: Decimal, new_earn_balance: Decimal, new_ad_balance: Decimal) -> str:
    sep = get_separator()
    return (
        "✨ Transfer Complete\\!\n"
        f"{sep}\n"
        f"✅ Moved: `{format_trx_escaped(amount)} TRX`\n"
        f"💰 Earnings: `{format_trx_escaped(new_earn_balance)} TRX`\n" 
        f"📢 Ads: `{format_trx_escaped(new_ad_balance)} TRX`"
    )


def transfer_cancelled() -> str:
    return "❌ Transfer cancelled\\."


def transfer_invalid_amount() -> str:
    return "⚠️ Invalid amount\\. Please enter an integer amount of at least 1 TRX\\."


def recharge_invalid_amount() -> str:
    return "⚠️ Invalid amount\\. Please enter an amount of at least 1 TRX\\."


def transfer_insufficient_balance() -> str:
    return "⛔ Insufficient earnings balance for this transfer\\."


# ==================== Menu & Info Messages ====================
def help_message() -> str:
    sep = get_separator()
    min_dep = format_trx_escaped(Decimal(str(config.MIN_DEPOSIT_TRX))) if hasattr(config, "MIN_DEPOSIT_TRX") else "1"
    min_wd = format_trx_escaped(Decimal(str(config.MIN_WITHDRAWAL_TRX))) if hasattr(config, "MIN_WITHDRAWAL_TRX") else "1"
    part_comm = _esc(int(getattr(config, "SPONSOR_PARTICIPATION_COMMISSION_PERCENT", 5)))
    ad_comm = _esc(int(getattr(config, "SPONSOR_RECHARGE_COMMISSION_PERCENT", 10)))
    return (
        "🆘 Help\n"
        f"{sep}\n"
        "Here\'s what you can do:\n"
        "• 📣 Browse campaigns and complete tasks to earn TRX\.\n"
        "• 💰 Deposit TRX to fund your ads balance\.\n"
        "• 🧾 Create, recharge, pause/resume your ad campaigns\.\n"
        "• 🏧 Withdraw your earnings to any TRON wallet\.\n"
        "• 👥 Invite friends and earn referral commissions\.\n\n"
        f"Minimums: Deposit `{min_dep} TRX`, Withdraw `{min_wd} TRX`\n"
        f"Referrals: `{part_comm}%` on tasks, `{ad_comm}%` on ad spending\n\n"
        "Tip: Use the menu buttons below to navigate\."
    )


def support_message(admin_username: Optional[str]) -> str:
    sep = get_separator()
    admin = f"@{_esc(admin_username)}" if admin_username else (f"@{_esc(config.TELEGRAM_ADMIN_USERNAME)}" if getattr(config, "TELEGRAM_ADMIN_USERNAME", None) else "admin")
    return (
        "🛟 Support\n"
        f"{sep}\n"
        f"Need help or found a bug\? Contact {admin}\n\n"
        "Please include:\n"
        "• What you were trying to do\n"
        "• Any error message\n"
        "• Screenshots if possible"
    )


def about_message() -> str:
    sep = get_separator()
    return (
        "ℹ️ About\n"
        f"{sep}\n"
        "Campaign Marketplace Bot on TRON\.\n"
        "• ⚡ Fast earnings and instant participation flow\n"
        "• 🔒 Secure balances \(earn vs\. ads\) and encrypted keys\n"
        "• 🔗 TRON only \(native TRX\)\n"
    )


def qa_message() -> str:
    sep = get_separator()
    min_dep = format_trx_escaped(Decimal(str(config.MIN_DEPOSIT_TRX))) if hasattr(config, "MIN_DEPOSIT_TRX") else "1"
    min_wd = format_trx_escaped(Decimal(str(config.MIN_WITHDRAWAL_TRX))) if hasattr(config, "MIN_WITHDRAWAL_TRX") else "1"
    return (
        "❓ Frequently Asked Questions\n"
        f"{sep}\n"
        "💰 Earning TRX:\n"
        "• Browse active campaigns\n" 
        "• Message the target bot\n"
        "• Forward a recent message here\n\n"
        "📢 Creating Campaigns:\n"
        "• Deposit TRX to your ad balance\n"
        "• Use /create\\_campaign command\n" 
        "• Set reward per participant\n\n"
        "⏱️ Processing Times:\n"
        "• Deposits: ~2 minutes\n"
        "• Withdrawals: ~2 minutes\n\n"
        "💫 Key Details:\n"
        f"• Min Deposit: `{min_dep} TRX`\n"
        f"• Min Withdrawal: `{min_wd} TRX`\n"
        "• Campaign owners cannot participate in own ads"
    )


def referral_info_message() -> str:
    sep = get_separator()
    task_comm = _esc(int(getattr(config, "SPONSOR_PARTICIPATION_COMMISSION_PERCENT", 5)))
    spend_comm = _esc(int(getattr(config, "SPONSOR_RECHARGE_COMMISSION_PERCENT", 10)))
    return (
        "👥 Referral Program\n"
        f"{sep}\n"
        "Earn commissions from users you invite:\n"
        f"• `{task_comm}%` of their task rewards\n"
        f"• `{spend_comm}%` of their ad spending\n\n"
        "Get your personal link in the Referral menu and start sharing\."
    )


def main_menu_intro() -> str:
    sep = get_separator()
    return (
        "🏠 Main Menu\n"
        f"{sep}\n"
        "Choose an option below to get started\.\n"
        "• 📣 Browse campaigns\n"
        "• 💳 Balance & Wallet\n"
        "• 📢 My Ads\n"
        "• 👥 Referrals\n"
        "• ⚙️ Settings / Help"
    )


# ==================== Notifications ====================
def sponsor_new_referral_notification(display_label: Optional[str]) -> str:
    sep = get_separator()
    user_display = _esc(display_label) if display_label else "a new user"
    return (
        "🎉 New Referral Joined\n"
        f"{sep}\n"
        f"You just gained a new downline: {user_display}\n\n"
        "Track your referral stats from the Referrals menu\."
    )
