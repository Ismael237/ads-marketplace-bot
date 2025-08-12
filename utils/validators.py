"""
Validators for user input and TRON-specific data.
"""
import re
from typing import Optional


def is_valid_tron_address(address: str) -> bool:
    """
    Validate TRON address format
    TRON addresses start with 'T' and are 34 characters long
    """
    if not address or len(address) != 34:
        return False

    if not address.startswith("T"):
        return False

    valid_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return all(c in valid_chars for c in address)
    

def is_valid_telegram_id(telegram_id: str) -> bool:
    """Validate Telegram ID format"""
    try:
        int(telegram_id)
        return len(telegram_id) >= 5 and len(telegram_id) <= 15
    except ValueError:
        return False


def sanitize_telegram_username(username: Optional[str]) -> Optional[str]:
    """
    Sanitize and validate Telegram username
    """
    if not username:
        return None
    username = username.lstrip("@")
    if len(username) < 5 or len(username) > 32:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_]+", username):
        return None
    return username


