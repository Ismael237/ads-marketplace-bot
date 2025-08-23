from __future__ import annotations

from decimal import Decimal
from typing import Optional, Tuple, List

from database.database import get_db_session
from database.models import (
    TransactionStatus,
    User,
    Campaign,
    CampaignParticipation,
    ParticipationStatus,
    Transaction,
    TransactionType,
    BalanceType,
)
from utils.helpers import generate_validation_link
from sqlalchemy import func
from utils.helpers import get_utc_date


class CampaignService:
    """Service de campagnes basé sur des méthodes statiques et transactions internes."""

    # ====== Basic fetch helpers ======
    @staticmethod
    def get_user_by_telegram_id(telegram_id: str) -> Optional[User]:
        with get_db_session() as db:
            return db.query(User).filter(User.telegram_id == str(telegram_id)).first()

    @staticmethod
    def get_campaign_by_id(campaign_id: int) -> Optional[Campaign]:
        with get_db_session() as db:
            return db.query(Campaign).get(int(campaign_id))

    @staticmethod
    def list_user_campaigns_by_owner(owner_id: int) -> List[Campaign]:
        with get_db_session() as db:
            return (
                db.query(Campaign)
                .filter(Campaign.owner_id == int(owner_id))
                .order_by(Campaign.id.desc())
                .all()
            )

    @staticmethod
    def list_user_campaigns_by_telegram(telegram_id: str) -> List[Campaign]:
        with get_db_session() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
            if not user:
                return []
            return (
                db.query(Campaign)
                .filter(Campaign.owner_id == user.id)
                .order_by(Campaign.id.desc())
                .all()
            )

    # ====== Create campaign ======
    @staticmethod
    def create_campaign(
        owner: User,
        title: str,
        bot_link: str,
        bot_username: str,
        amount_per_referral: Decimal,
    ) -> Campaign:
        """Créer une campagne (transaction unique)."""
        with get_db_session() as db:
            # Recharger l'owner si nécessaire
            owner_db = db.query(User).get(int(owner.id)) if isinstance(owner, User) else None
            if not owner_db:
                # fallback si on a seulement un id valide
                owner_db = db.query(User).filter(User.id == int(getattr(owner, "id", 0))).first()
            if not owner_db:
                raise ValueError("Owner not found")

            camp = Campaign(
                owner_id=owner_db.id,
                title=title,
                bot_link=bot_link,
                bot_username=bot_username,
                amount_per_referral=amount_per_referral,
                balance=Decimal("0"),
                referral_count=0,
                is_active=True,
            )
            db.add(camp)
            db.commit()
            db.refresh(camp)
            return camp

    # ====== Update Campaign ======
    @staticmethod
    def update_campaign(
        owner_id: int,
        campaign_id: int,
        title: str = None,
        bot_link: str = None,
        bot_username: str = None
    ) -> Tuple[Optional[Campaign], Optional[str]]:
        """
        Update campaign details.
        
        Args:
            owner_id: ID of the campaign owner (for authorization)
            campaign_id: ID of the campaign to update
            title: New title (optional)
            bot_link: New bot link (optional)
            bot_username: New bot username (optional, will be extracted from bot_link if not provided)
            
        Returns:
            Tuple of (updated_campaign, error_message)
        """
        with get_db_session() as db:
            camp = db.query(Campaign).get(int(campaign_id))
            if not camp:
                return None, "Campaign not found"
                
            # Verify ownership
            if camp.owner_id != int(owner_id):
                return None, "Not authorized to update this campaign"
                
            # Update fields if provided
            if title is not None:
                camp.title = title.strip()
                
            if bot_link is not None:
                camp.bot_link = bot_link.strip()
                # Update username from link if not explicitly provided
                if bot_username is None:
                    camp.bot_username = bot_link.split('/')[-1].split('?')[0].replace('@', '')
            elif bot_username is not None:
                camp.bot_username = bot_username.strip()
            
            db.commit()
            db.refresh(camp)
            return camp, None

    # ====== Pause/Resume/Toggle ======
    @staticmethod
    def pause_campaign_by_id(campaign_id: int) -> Optional[Campaign]:
        with get_db_session() as db:
            camp = db.query(Campaign).get(int(campaign_id))
            if not camp:
                return None
            camp.is_active = False
            db.commit()
            db.refresh(camp)
            return camp

    @staticmethod
    def resume_campaign_by_id(campaign_id: int) -> Optional[Campaign]:
        with get_db_session() as db:
            camp = db.query(Campaign).get(int(campaign_id))
            if not camp:
                return None
            camp.is_active = True
            db.commit()
            db.refresh(camp)
            return camp

    @staticmethod
    def toggle_campaign(owner_id: int, campaign_id: int) -> Tuple[Optional[Campaign], Optional[str]]:
        """Bascule l'état actif d'une campagne pour un owner donné.
        Retourne (campaign, error_reason) où error_reason peut être 'not_found', 'not_owner', 'insufficient_balance'."""
        with get_db_session() as db:
            camp = db.query(Campaign).get(int(campaign_id))
            if not camp:
                return None, "not_found"
            if int(camp.owner_id) != int(owner_id):
                return None, "not_owner"
            new_state = not bool(camp.is_active)
            if new_state and camp.balance < camp.amount_per_referral:
                return camp, "insufficient_balance"
            camp.is_active = new_state
            db.commit()
            db.refresh(camp)
            return camp, None

    # ====== Auto deactivation rule ======
    @staticmethod
    def enforce_auto_pause_if_insufficient_balance(campaign_id: int) -> Optional[Campaign]:
        with get_db_session() as db:
            camp = db.query(Campaign).get(int(campaign_id))
            if not camp:
                return None
            if camp.is_active and camp.balance < camp.amount_per_referral:
                camp.is_active = False
                db.commit()
                db.refresh(camp)
            return camp

    # ====== Participation helpers (kept for completeness, but not used in handlers shown) ======
    @staticmethod
    def can_user_participate(campaign: Campaign, user: User) -> Tuple[bool, Optional[str]]:
        if not campaign.is_active:
            return False, "inactive"
        if campaign.owner_id == user.id:
            return False, "owner"
        with get_db_session() as db:
            today = get_utc_date()
            validated_today = (
                db.query(CampaignParticipation)
                .filter(
                    CampaignParticipation.campaign_id == campaign.id,
                    CampaignParticipation.user_id == user.id,
                    CampaignParticipation.status == ParticipationStatus.validated,
                    func.date(CampaignParticipation.validated_at) == today,
                )
                .first()
            )
            if validated_today:
                return False, "validated_today"
        return True, None

    @staticmethod
    def start_participation(campaign: Campaign, user: User) -> CampaignParticipation:
        with get_db_session() as db:
            part = CampaignParticipation(
                campaign_id=campaign.id,
                user_id=user.id,
                status=ParticipationStatus.pending,
            )
            db.add(part)
            db.commit()
            db.refresh(part)
            return part

    @staticmethod
    def set_forward_and_generate_link(participation_id: int, forward_message_id: str) -> Optional[CampaignParticipation]:
        with get_db_session() as db:
            part = db.query(CampaignParticipation).get(int(participation_id))
            if not part:
                return None
            part.forward_message_id = forward_message_id
            part.validation_link = generate_validation_link()
            db.commit()
            db.refresh(part)
            return part

    # ====== Recharge logic ======
    @staticmethod
    def recharge_campaign(owner_id: int, campaign_id: int, amount: Decimal) -> Tuple[Optional[Campaign], Optional[str], bool]:
        """Recharge la campagne d'un owner.
        Retourne (campaign, error_reason, was_activated). error_reason ∈ {None, 'not_found', 'not_owner', 'insufficient_balance'}"""
        with get_db_session() as db:
            user = db.query(User).get(int(owner_id))
            if not user:
                return None, "not_found", False
            camp = db.query(Campaign).get(int(campaign_id))
            if not camp:
                return None, "not_found", False
            if camp.owner_id != user.id:
                return None, "not_owner", False
            if user.ad_balance < amount:
                return None, "insufficient_balance", False

            prev_active = bool(camp.is_active)
            # Money moves
            user.ad_balance = (user.ad_balance or Decimal("0")) - amount
            camp.balance = (camp.balance or Decimal("0")) + amount

            # Sponsor commission (10% par défaut via config si dispo)
            try:
                from decimal import Decimal as D
                import config
                if user.sponsor_id:
                    sponsor = db.query(User).get(int(user.sponsor_id))
                    if sponsor:
                        percent = D(str(getattr(config, "SPONSOR_RECHARGE_COMMISSION_PERCENT", 10)))
                        commission = (amount * percent) / D(100)
                        sponsor.earn_balance = (sponsor.earn_balance or D(0)) + commission
                        db.add(
                            Transaction(
                                user_id=sponsor.id,
                                type=TransactionType.referral_commission,
                                status=TransactionStatus.completed,
                                amount_trx=commission,
                                balance_type=BalanceType.earn_balance,
                                reference_id=str(camp.id),
                                description="Sponsor commission on campaign recharge",
                            )
                        )
            except Exception:
                # Fail-safe: ne pas casser la recharge si commission échoue
                pass

            # Activation auto si seuil atteint
            was_activated = False
            if camp.balance >= camp.amount_per_referral and not prev_active:
                camp.is_active = True
                was_activated = True

            # Log de la recharge comme dépense campagne (historique utilisateur)
            db.add(
                Transaction(
                    user_id=user.id,
                    type=TransactionType.campaign_spend,
                    status=TransactionStatus.completed,
                    amount_trx=amount,
                    balance_type=BalanceType.ad_balance,
                    reference_id=str(camp.id),
                    description="Campaign recharge",
                )
            )

            db.commit()
            db.refresh(camp)
            return camp, None, was_activated

    # ====== Broadcast helpers ======
    @staticmethod
    def get_all_users(exclude_telegram_id: Optional[str] = None) -> List[User]:
        with get_db_session() as db:
            q = db.query(User)
            if exclude_telegram_id is not None:
                q = q.filter(User.telegram_id != str(exclude_telegram_id))
            return q.all()
