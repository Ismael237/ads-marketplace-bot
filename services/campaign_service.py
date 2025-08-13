from __future__ import annotations

from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session

from database.models import (
    User,
    Campaign,
    CampaignParticipation,
    ParticipationStatus,
)
from utils.helpers import generate_validation_link
from sqlalchemy import func
from utils.helpers import get_utc_date


class CampaignService:
    def __init__(self, db: Session):
        self.db = db

    def create_campaign(
        self,
        owner: User,
        title: str,
        bot_link: str,
        bot_username: str,
        amount_per_referral: Decimal,
    ) -> Campaign:
        campaign = Campaign.create(
            self.db,
            owner_id=owner.id,
            title=title,
            bot_link=bot_link,
            bot_username=bot_username,
            amount_per_referral=amount_per_referral,
            balance=Decimal("0"),
            referral_count=0,
            is_active=True,
        )
        return campaign

    def pause_campaign(self, campaign: Campaign) -> Campaign:
        campaign.is_active = False
        return campaign.save(self.db)

    def resume_campaign(self, campaign: Campaign) -> Campaign:
        campaign.is_active = True
        return campaign.save(self.db)

    def can_user_participate(self, campaign: Campaign, user: User) -> bool:
        # Check if campaign is active
        if not campaign.is_active:
            return False

        # Disallow owners from participating in their own campaigns
        if campaign.owner_id == user.id:
            return False

        # Disallow if user has already validated this campaign today (once per day)
        today = get_utc_date()
        validated_today = (
            self.db.query(CampaignParticipation)
            .filter(
                CampaignParticipation.campaign_id == campaign.id,
                CampaignParticipation.user_id == user.id,
                CampaignParticipation.status == ParticipationStatus.validated,
                func.date(CampaignParticipation.validated_at) == today,
            )
            .first()
        )
        if validated_today:
            return False

        # Allow participation if no existing participation, or if previous participation failed
        existing = (
            self.db.query(CampaignParticipation)
            .filter(
                CampaignParticipation.campaign_id == campaign.id,
                CampaignParticipation.user_id == user.id,
            )
            .first()
        )
        # Allow if no existing participation or if the existing one failed
        return existing is None or existing.status == ParticipationStatus.failed

    def start_participation(self, campaign: Campaign, user: User) -> CampaignParticipation:
        participation = CampaignParticipation.create(
            self.db,
            campaign_id=campaign.id,
            user_id=user.id,
            status=ParticipationStatus.pending,
        )
        return participation

    def set_forward_and_generate_link(self, participation: CampaignParticipation, forward_message_id: str) -> CampaignParticipation:
        participation.forward_message_id = forward_message_id
        participation.validation_link = generate_validation_link()
        return participation.save(self.db)


