from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import func, select

from database.database import get_db_session
from database.models import (
    User,
    Campaign,
    CampaignParticipation,
    ParticipationStatus,
    Transaction,
    TransactionType,
    BalanceType,
)
from utils.helpers import get_utc_date, get_utc_time
from services.campaign_service import CampaignService
from services.referral_service import ReferralService
import config


class ParticipationService:
    # ===== Basic helpers =====
    @staticmethod
    def get_user_by_telegram_id(telegram_id: str) -> Optional[User]:
        return CampaignService.get_user_by_telegram_id(telegram_id)

    @staticmethod
    def get_campaign_by_id(campaign_id: int) -> Optional[Campaign]:
        return CampaignService.get_campaign_by_id(campaign_id)

    # ===== Browsing =====
    @staticmethod
    def get_active_campaigns_for_browsing(telegram_id: Optional[str]) -> List[Campaign]:
        with get_db_session() as db:
            q = db.query(Campaign).filter(Campaign.is_active == True).order_by(Campaign.id.desc())
            if telegram_id:
                current_user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
                if current_user:
                    q = q.filter(Campaign.owner_id != current_user.id)
                    today = get_utc_date()
                    validated_today_subq = (
                        select(CampaignParticipation.campaign_id)
                        .where(
                            CampaignParticipation.user_id == current_user.id,
                            CampaignParticipation.status == ParticipationStatus.validated,
                            func.date(CampaignParticipation.validated_at) == today,
                        )
                    )
                    q = q.filter(~Campaign.id.in_(validated_today_subq))
            return q.all()

    @staticmethod
    def find_campaign_by_forward_origin_for_user(telegram_id: str, origin_username: str) -> Optional[Campaign]:
        """Find a candidate active campaign by bot username for the user (excludes owner's and validated today)."""
        if not origin_username:
            return None
        ou = origin_username[1:] if origin_username.startswith('@') else origin_username
        with get_db_session() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
            if not user:
                return None
            today = get_utc_date()
            validated_today_subq = (
                select(CampaignParticipation.campaign_id)
                .where(
                    CampaignParticipation.user_id == user.id,
                    CampaignParticipation.status == ParticipationStatus.validated,
                    func.date(CampaignParticipation.validated_at) == today,
                )
            )
            base_q = (
                db.query(Campaign)
                .filter(Campaign.bot_username.ilike(ou))
                .filter(Campaign.is_active == True)
                .filter(~Campaign.id.in_(validated_today_subq))
            )
            preferred_q = base_q.filter(Campaign.owner_id != user.id).order_by(Campaign.id.desc())
            return preferred_q.first()

    # ===== Participation lifecycle =====
    @staticmethod
    def start_participation(campaign_id: int, user_id: int) -> Optional[CampaignParticipation]:
        with get_db_session() as db:
            part = CampaignParticipation(
                campaign_id=int(campaign_id),
                user_id=int(user_id),
                status=ParticipationStatus.pending,
            )
            db.add(part)
            db.commit()
            db.refresh(part)
            return part

    @staticmethod
    def mark_participation_failed(participation_id: int) -> None:
        with get_db_session() as db:
            part = db.query(CampaignParticipation).get(int(participation_id))
            if not part:
                return
            part.status = ParticipationStatus.failed
            db.commit()

    @staticmethod
    def set_forward_and_generate_link(participation_id: int, forward_message_id: str) -> Optional[CampaignParticipation]:
        return CampaignService.set_forward_and_generate_link(participation_id, forward_message_id)

    @staticmethod
    def validate_and_payout(participation_id: int) -> Tuple[Optional[Decimal], Optional[str]]:
        """
        Validate a participation and distribute payouts.
        Returns (user_reward, error) where error in {None, 'insufficient_balance', 'not_found'}.
        """
        with get_db_session() as db:
            part = db.query(CampaignParticipation).get(int(participation_id))
            if not part:
                return None, 'not_found'
            user = db.query(User).get(int(part.user_id))
            camp = db.query(Campaign).get(int(part.campaign_id))
            if not user or not camp:
                return None, 'not_found'

            # Stamp validation
            part.status = ParticipationStatus.validated
            part.validated_at = get_utc_time()
            db.commit()

            camp.amount_per_referral = camp.amount_per_referral or Decimal("0")
            if camp.balance < camp.amount_per_referral:
                return None, 'insufficient_balance'

            apr = camp.amount_per_referral
            user_pct = Decimal(str(getattr(config, "PARTICIPATION_USER_REWARD_PERCENT", 75))) / Decimal("100")
            sponsor_pct = Decimal(str(getattr(config, "SPONSOR_PARTICIPATION_COMMISSION_PERCENT", 5))) / Decimal("100")
            user_reward = (apr * user_pct).quantize(Decimal("0.000001"))
            sponsor_commission = (apr * sponsor_pct).quantize(Decimal("0.000001"))

            # Deduct full APR from campaign, credit user, increment count
            camp.balance -= apr
            user.earn_balance = (user.earn_balance or Decimal("0")) + user_reward
            camp.referral_count = (camp.referral_count or 0) + 1

            db.add(
                Transaction(
                    user_id=user.id,
                    type=TransactionType.task_reward,
                    amount_trx=user_reward,
                    balance_type=BalanceType.earn_balance,
                    reference_id=str(part.id),
                    description="Task reward validated",
                )
            )

            # Sponsor commission via ReferralService (credits sponsor and record commission)
            if user.sponsor_id and sponsor_commission > 0:
                try:
                    ReferralService.pay_task_commission(
                        sponsor_id=int(user.sponsor_id),
                        referred_user_id=user.id,
                        amount_trx=apr,
                        percentage=sponsor_pct,
                        participation_id=part.id,
                    )
                except Exception:
                    # don't fail payout if sponsor logic fails
                    pass

            # Admin remainder
            actual_sponsor_commission = sponsor_commission if user.sponsor_id and sponsor_commission > 0 else Decimal("0")
            admin_remainder = (apr - user_reward - actual_sponsor_commission).quantize(Decimal("0.000001"))
            if admin_remainder > 0:
                admin_user = db.query(User).filter(User.telegram_id == str(config.TELEGRAM_ADMIN_ID)).first()
                if admin_user:
                    admin_user.earn_balance = (admin_user.earn_balance or Decimal("0")) + admin_remainder
                    db.add(
                        Transaction(
                            user_id=admin_user.id,
                            type=TransactionType.task_reward,
                            amount_trx=admin_remainder,
                            balance_type=BalanceType.earn_balance,
                            reference_id=str(part.id),
                            description="Admin remainder from task reward",
                        )
                    )

            db.commit()
            return user_reward, None

    # ===== Reporting =====
    @staticmethod
    def create_report(campaign_id: int, reporter_telegram_id: str, reason: str, description: Optional[str] = None) -> bool:
        from database.models import CampaignReport, ReportReason  # local import to avoid cycles
        with get_db_session() as db:
            user = db.query(User).filter(User.telegram_id == str(reporter_telegram_id)).first()
            if not user:
                return False
            try:
                reason_enum = ReportReason[reason]
            except Exception:
                return False
            CampaignReport.create(db, campaign_id=int(campaign_id), reporter_id=user.id, reason=reason_enum, description=description)
            return True
