"""
Database and utility helper functions for Bot Marketplace
Provides common utility functions and database helpers
"""
from datetime import datetime, timezone
import secrets
import string
from typing import Optional
from sqlalchemy.orm import Session
import random
import re

def generate_referral_code(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def generate_share_link(bot_username, referral_code):
    return f"https://t.me/{bot_username}?start={referral_code}"


def escape_markdown_v2(text: str) -> str:
    escape_chars = r'\\`*_\[\]()~>#+=|{}.!-'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


def get_utc_time():
    return datetime.now(timezone.utc)


def get_utc_date():
    return get_utc_time().date()


def get_separator():
    return "─" * 20

def generate_referral_code(length: int = 8) -> str:
    """Generate a unique referral code"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


def generate_validation_link(length: int = 32) -> str:
    """Generate a unique validation link token"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


def validate_tron_address(address: str) -> bool:
    """
    Validate TRON address format
    TRON addresses start with 'T' and are 34 characters long
    """
    if not address or len(address) != 34:
        return False
    
    if not address.startswith('T'):
        return False
    
    # Basic character validation (base58)
    valid_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return all(c in valid_chars for c in address)


def format_trx_amount(amount: float, decimals: int = 6) -> str:
    """Format TRX amount for display"""
    return f"{amount:.{decimals}f} TRX"


def calculate_commission(amount: float, rate: float) -> float:
    """Calculate commission amount based on rate"""
    return round(amount * rate, 6)


def is_valid_telegram_id(telegram_id: str) -> bool:
    """Validate Telegram ID format"""
    try:
        int(telegram_id)
        return len(telegram_id) >= 5 and len(telegram_id) <= 15
    except ValueError:
        return False


def sanitize_username(username: str) -> Optional[str]:
    """Sanitize and validate Telegram username"""
    if not username:
        return None
    
    # Remove @ if present
    username = username.lstrip('@')
    
    # Telegram username validation
    if len(username) < 5 or len(username) > 32:
        return None
    
    # Only alphanumeric and underscores allowed
    if not username.replace('_', '').isalnum():
        return None
    
    return username


def paginate_query(query, page: int = 1, per_page: int = 10):
    """
    Paginate SQLAlchemy query
    Returns paginated results and metadata
    """
    if page < 1:
        page = 1
    
    if per_page < 1 or per_page > 100:
        per_page = 10
    
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': page * per_page < total
    }


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default: int = 0) -> int:
    """Safely convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class DatabaseHelper:
    """Helper class for common database operations"""
    
    @staticmethod
    def get_or_create(db: Session, model, defaults=None, **kwargs):
        """Get existing object or create new one"""
        instance = db.query(model).filter_by(**kwargs).first()
        if instance:
            return instance, False
        else:
            params = dict((k, v) for k, v in kwargs.items())
            params.update(defaults or {})
            instance = model(**params)
            db.add(instance)
            db.commit()
            db.refresh(instance)
            return instance, True
    
    @staticmethod
    def bulk_create(db: Session, model, data_list):
        """Bulk create multiple objects"""
        objects = [model(**data) for data in data_list]
        db.bulk_save_objects(objects)
        db.commit()
        return objects
    
    @staticmethod
    def update_or_create(db: Session, model, defaults=None, **kwargs):
        """Update existing object or create new one"""
        instance = db.query(model).filter_by(**kwargs).first()
        if instance:
            for key, value in (defaults or {}).items():
                setattr(instance, key, value)
            db.commit()
            db.refresh(instance)
            return instance, False
        else:
            params = dict((k, v) for k, v in kwargs.items())
            params.update(defaults or {})
            instance = model(**params)
            db.add(instance)
            db.commit()
            db.refresh(instance)
            return instance, True
