from __future__ import annotations

from decimal import Decimal
from sqlalchemy.orm import Session

from database.models import User, ReferralCommission, CommissionType


class ReferralService:
    def __init__(self, db: Session):
        self.db = db

    def pay_task_commission(
        self,
        sponsor: User,
        referred_user: User,
        amount_trx: Decimal,
        percentage: Decimal,
        participation_id: int,
    ) -> ReferralCommission:
        commission_amount = (amount_trx * percentage).quantize(Decimal("0.000001"))
        rc = ReferralCommission.create(
            self.db,
            user_id=sponsor.id,
            referred_user_id=referred_user.id,
            participation_id=participation_id,
            deposit_id=None,
            type=CommissionType.task_completion,
            amount_trx=commission_amount,
            percentage=percentage,
        )
        sponsor.earn_balance += commission_amount
        sponsor.save(self.db)
        return rc

    def pay_deposit_commission(
        self,
        sponsor: User,
        referred_user: User,
        amount_trx: Decimal,
        percentage: Decimal,
        deposit_id: int,
    ):
        commission_amount = (amount_trx * percentage).quantize(Decimal("0.000001"))
        rc = ReferralCommission.create(
            self.db,
            user_id=sponsor.id,
            referred_user_id=referred_user.id,
            participation_id=None,
            deposit_id=deposit_id,
            type=CommissionType.deposit,
            amount_trx=commission_amount,
            percentage=percentage,
        )
        sponsor.earn_balance += commission_amount
        sponsor.save(self.db)
        return rc


