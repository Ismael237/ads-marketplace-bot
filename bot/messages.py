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
        "Click to copy your deposit address\\:\n\n"
        f"`{_esc(address)}`\n\n"
        "⏳ Your balance is credited after automatic confirmations\\."
    )


def deposit_copied(address: str) -> str:
    return (
        "📋 Copy the address below\\:\n"
        f"`{_esc(address)}`"
    )


def withdraw_ask_amount(min_withdrawal: Decimal, current_earn_balance: Decimal) -> str:
    sep = get_separator()
    return (
        "🏧 Withdraw TRX\n"
        f"{sep}\n"
        f"Minimum\\: `{format_trx_escaped(min_withdrawal)} TRX`\n"
        f"Your balance\\: `{format_trx_escaped(current_earn_balance)} TRX`\n"
        "Select an amount or enter a custom amount \\(e\\.g\\. 12\\.5\\)\\:"
    )


def withdraw_ask_address(amount: Decimal) -> str:
    return (
        "📮 Enter the destination TRON address \\(starts with T\\)\\:\n"
        f"Amount\\: `{format_trx_escaped(amount)} TRX`"
    )


def withdraw_confirm(amount: Decimal, to_address: str, fee_rate: Optional[Decimal] = None) -> str:
    sep = get_separator()
    fee_txt = ""
    if fee_rate is not None and fee_rate > 0:
        fee_txt = f"\nFee\\: `{format_trx_escaped(Decimal(amount) * Decimal(fee_rate))} TRX`"
    return (
        "✅ Please confirm your withdrawal\\:\n"
        f"{sep}\n"
        f"Amount\\: `{format_trx_escaped(amount)} TRX`\n"
        f"To\\: `{_esc(to_address)}`\n"
        f"{fee_txt}"
    )


def withdraw_cancelled() -> str:
    return "❌ Withdrawal cancelled\\."


def browse_campaign(camp_title: str, amount_per_referral: Decimal) -> str:
    sep = get_separator()
    return (
        "📣 Campaign\n"
        f"{sep}\n"
        f"Title\\: `{_esc(camp_title)}`\n"
        f"Reward per task\\: `{format_trx_escaped(amount_per_referral)} TRX`\n\n"
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
        f"Your referral link\\(click to copy\\)\\:\n\n"
        f"`{_esc(link)}`\n\n"
        f"Stats\\:\n"
        f"• Referrals\\: `{referral_count}`\n"
        f"• Total earned\\: `{format_trx_escaped(total_earned)} TRX`\n\n"
        f"Commissions\\:\n"
        f"• Tasks\\: `{task_rate}%`\n"
        f"• Ads spending\\: `{deposit_rate}%`"
    )


def report_choose_reason() -> str:
    return "🚩 Choose a reason to report this campaign\\:"


def report_saved() -> str:
    return "✅ Report submitted\\. Thank you for your feedback\\."


def balance_overview(earn_balance: Decimal, ad_balance: Decimal) -> str:
    sep = get_separator()
    return (
        "💳 Balance\n"
        f"{sep}\n"
        f"Earnings\\: `{format_trx_escaped(earn_balance)} TRX`\n"
        f"Advertising\\: `{format_trx_escaped(ad_balance)} TRX`"
    )


def history_intro() -> str:
    sep = get_separator()
    return (
        "📜 History\n"
        f"{sep}\n"
        "Choose a filter below to view your transactions\."
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
        f"Support\\: {admin}\n"
        "About\\: Campaign Marketplace Bot on TRON"
    )


# ==================== Campaign Creation (Multi-step) ====================
def create_campaign_ask_link() -> str:
    sep = get_separator()
    return (
        "🆕 Create Campaign\n"
        f"{sep}\n"
        "Send the target bot link or username\n"
        "Examples\\: `https\\://t\.me/MyBot` or `@MyBot`\n\n"
        "You can cancel anytime\."
    )


def create_campaign_ask_forward(bot_link: str) -> str:
    return (
        "📨 Please forward a recent message from the target bot here to verify it works\n"
        "Bot link\\:\n"
        f"{_esc(bot_link)}"
    )


def create_campaign_ask_title(default_title: str) -> str:
    sep = get_separator()
    return (
        "📝 Enter a campaign title, or tap Skip to use the default title\n"
        f"{sep}\n"
        f"Default\\: `{_esc(default_title)}`"
    )


def create_campaign_confirm(bot_link: str, bot_username: str, amount_per_referral: Decimal, title: str) -> str:
    sep = get_separator()
    return (
        "✅ Confirm Campaign\n"
        f"{sep}\n"
        f"Title\\: `{_esc(title)}`\n"
        f"Bot\\: `@{_esc(bot_username)}`\n"
        f"Link\\: `{_esc(bot_link)}`\n"
        f"Reward per referral\\: `{format_trx_escaped(amount_per_referral)} TRX`\n\n"
        "Tap the Confirm or Cancel button below\\."
    )


def create_campaign_cancelled() -> str:
    return "❌ Campaign creation cancelled\."


def create_campaign_created(campaign_id: int) -> str:
    return f"🎉 Campaign created with id `{_esc(campaign_id)}`"


# ==================== My Ads (Owner view) ====================
def my_ad_overview(title: str, bot_username: str, bot_link: str, amount_per_referral: Decimal, balance: Decimal, is_active: bool, referral_count: int, idx: int, total: int) -> str:
    sep = get_separator()
    status_emoji = "🟢" if is_active else "⏸️"
    status_text = "Active" if is_active else "Paused"
    return (
        f"📢 My Ad \\({idx}/{total}\\)\n"
        f"{sep}\n"
        f"Title\\: `{_esc(title)}`\n"
        f"Bot\\: `@{_esc(bot_username)}`\n"
        f"Link\\: `{_esc(bot_link)}`\n"
        f"Reward per referral\\: `{format_trx_escaped(amount_per_referral)} TRX`\n"
        f"Balance\\: `{format_trx_escaped(balance)} TRX`\n"
        f"Referrals\\: `{referral_count}`\n"
        f"Status\\: {status_emoji} {status_text}"
    )


def myads_recharge_ask_amount(current_ad_balance: Decimal) -> str:
    return (
        f"Your ad balance\\: `{format_trx_escaped(current_ad_balance)} TRX`\n"
        "You can cancel anytime\.\n"
        "🔋 Enter amount to recharge this ad, or choose a preset below\\:"
    )


def myads_recharge_confirm(amount: Decimal) -> str:
    return (
        "✅ Confirm Recharge\n"
        f"Amount\\: `{format_trx_escaped(amount)} TRX`"
    )


def myads_recharge_done(campaign_id: int, amount: Decimal) -> str:
    return (
        f"✅ Recharged campaign `{_esc(campaign_id)}` by `{format_trx_escaped(amount)} TRX`"
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
