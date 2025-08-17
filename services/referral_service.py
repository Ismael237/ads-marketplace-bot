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
