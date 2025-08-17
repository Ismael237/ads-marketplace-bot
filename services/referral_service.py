from __future__ import annotations

from decimal import Decimal
from typing import Tuple

from sqlalchemy import func

from database.database import get_db_session
from database.models import (
    User,
    ReferralCommission,
    CommissionType,
    CommissionStatus,
)
from utils.helpers import generate_referral_code


class ReferralService:
    @staticmethod
    def get_user_by_telegram_id(telegram_id: str) -> User | None:
        with get_db_session() as db:
            return db.query(User).filter(User.telegram_id == str(telegram_id)).first()

    @staticmethod
    def get_overview(user_id: int) -> Tuple[int, Decimal]:
        """Return (referral_count, total_earned) for a given user_id."""
        with get_db_session() as db:
            referral_count = db.query(User).filter(User.sponsor_id == int(user_id)).count()
            total_earned = (
                db.query(func.coalesce(func.sum(ReferralCommission.amount_trx), 0))
                .filter(ReferralCommission.user_id == int(user_id))
                .scalar()
            )
            return referral_count, Decimal(str(total_earned))

    @staticmethod
    def pay_task_commission(
        sponsor_id: int,
        referred_user_id: int,
        amount_trx: Decimal,
        percentage: Decimal,
        participation_id: int,
    ) -> ReferralCommission:
        """Create a task-completion referral commission and credit sponsor's balance."""
        with get_db_session() as db:
            sponsor = db.query(User).get(int(sponsor_id))
            if not sponsor:
                raise ValueError("sponsor_not_found")
            commission_amount = (amount_trx * percentage).quantize(Decimal("0.000001"))
            rc = ReferralCommission(
                user_id=sponsor.id,
                referred_user_id=int(referred_user_id),
                participation_id=int(participation_id),
                deposit_id=None,
                type=CommissionType.task_completion,
                status=CommissionStatus.paid,
                amount_trx=commission_amount,
                percentage=percentage,
            )
            db.add(rc)
            sponsor.earn_balance = (sponsor.earn_balance or Decimal("0")) + commission_amount
            db.commit()
            db.refresh(rc)
            return rc

    @staticmethod
    def ensure_user(telegram_id: str, username: str | None = None, sponsor_referral_code: str | None = None) -> User:
        """Get or create a user. If creating, set sponsor by referral code when provided.
        Returns the persisted User.
        """
        with get_db_session() as db:
            # Try existing
            user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
            if user:
                # Optionally update username if changed
                new_username = username or None
                if new_username is not None and new_username != user.username:
                    user.username = new_username
                    db.commit()
                    db.refresh(user)
                return user

            sponsor_id = None
            if sponsor_referral_code:
                sponsor = db.query(User).filter(User.referral_code == sponsor_referral_code).first()
                if sponsor:
                    sponsor_id = sponsor.id

            # Create new user
            user = User.create(
                db,
                telegram_id=str(telegram_id),
                username=username or None,
                referral_code=generate_referral_code(),
                sponsor_id=sponsor_id,
            )
            return user
