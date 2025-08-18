"""
Database models for Bot Marketplace
Defines all database tables and relationships for the campaign marketplace system
Integrates base models, utilities, and marketplace-specific models
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, Enum, Boolean, Text, func
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, Session
import enum

from utils.helpers import get_utc_time

# Create the base class for all models
Base = declarative_base()


class TimestampMixin:
    """Mixin to add timestamp fields to models"""
    
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=get_utc_time, nullable=False)
    
    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=get_utc_time, onupdate=get_utc_time, nullable=False)


class BaseModel(Base, TimestampMixin):
    """
    Base model class with common fields and methods
    All models should inherit from this class
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    
    def to_dict(self) -> dict:
        """Convert model instance to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update_from_dict(self, data: dict):
        """Update model instance from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def create(cls, db: Session, **kwargs):
        """Create a new instance and save to database"""
        instance = cls(**kwargs)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance
    
    @classmethod
    def get_by_id(cls, db: Session, id: int):
        """Get instance by ID"""
        return db.query(cls).filter(cls.id == id).first()
    
    @classmethod
    def get_all(cls, db: Session, skip: int = 0, limit: int = 100):
        """Get all instances with pagination"""
        return db.query(cls).offset(skip).limit(limit).all()
    
    def save(self, db: Session):
        """Save instance to database"""
        db.add(self)
        db.commit()
        db.refresh(self)
        return self
    
    def delete(self, db: Session):
        """Delete instance from database"""
        db.delete(self)
        db.commit()
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"

# Enums for marketplace system
class CampaignStatus(enum.Enum):
    active = 'active'
    inactive = 'inactive'
    paused = 'paused'


class ParticipationStatus(enum.Enum):
    pending = 'pending'
    validated = 'validated'
    failed = 'failed'


class DepositStatus(enum.Enum):
    pending = 'pending'
    confirmed = 'confirmed'
    failed = 'failed'


class WithdrawalStatus(enum.Enum):
    pending = 'pending'
    processing = 'processing'
    completed = 'completed'
    failed = 'failed'


class TransactionType(enum.Enum):
    deposit = 'deposit'
    withdrawal = 'withdrawal'
    task_reward = 'task_reward'
    campaign_spend = 'campaign_spend'
    referral_commission = 'referral_commission'
    internal_transfer = 'internal_transfer'


class TransactionStatus(enum.Enum):
    pending = 'pending'
    completed = 'completed'
    failed = 'failed'


class BalanceType(enum.Enum):
    earn_balance = 'earn_balance'
    ad_balance = 'ad_balance'


class CommissionType(enum.Enum):
    task_completion = 'task_completion'
    deposit = 'deposit'


class CommissionStatus(enum.Enum):
    pending = 'pending'
    paid = 'paid'


class ReportReason(enum.Enum):
    bot_inactive = 'bot_inactive'
    spam = 'spam'
    dead_link = 'dead_link'
    other = 'other'


class ReportStatus(enum.Enum):
    pending = 'pending'
    reviewed = 'reviewed'
    resolved = 'resolved'

# Marketplace Models
class User(BaseModel):
    """User model for marketplace participants and advertisers"""
    __tablename__ = 'users'
    
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    referral_code = Column(String, unique=True, nullable=False, index=True)
    sponsor_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Balances
    earn_balance = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    ad_balance = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    total_earned = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    total_spent = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    
    # Relationships
    sponsor = relationship("User", remote_side=lambda: [User.id], back_populates="referrals")
    referrals = relationship("User", back_populates="sponsor", foreign_keys=[sponsor_id])
    campaigns = relationship("Campaign", back_populates="owner")
    participations = relationship("CampaignParticipation", back_populates="user")
    wallets = relationship("UserWallet", back_populates="user")
    deposits = relationship("Deposit", back_populates="user")
    withdrawals = relationship("Withdrawal", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    commissions_received = relationship("ReferralCommission", foreign_keys="ReferralCommission.user_id", back_populates="beneficiary")
    commissions_generated = relationship("ReferralCommission", foreign_keys="ReferralCommission.referred_user_id", back_populates="referrer")


class Campaign(BaseModel):
    """Campaign model for advertisers to create marketing campaigns"""
    __tablename__ = 'campaigns'
    
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String, nullable=False)
    bot_link = Column(String, nullable=False)
    bot_username = Column(String, nullable=False)
    amount_per_referral = Column(Numeric(precision=18, scale=6), nullable=False)
    balance = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    referral_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="campaigns")
    participations = relationship("CampaignParticipation", back_populates="campaign")
    reports = relationship("CampaignReport", back_populates="campaign")


class CampaignParticipation(BaseModel):
    """Participation model for users participating in campaigns"""
    __tablename__ = 'campaign_participations'
    
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    forward_message_id = Column(String, nullable=True)
    validation_link = Column(String, nullable=True)
    amount_earned = Column(Numeric(precision=18, scale=6), nullable=True)
    commission_paid = Column(Numeric(precision=18, scale=6), nullable=True)
    status = Column(Enum(ParticipationStatus), default=ParticipationStatus.pending, nullable=False)
    validated_at = Column(DateTime, nullable=True)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="participations")
    user = relationship("User", back_populates="participations")


class UserWallet(BaseModel):
    """User wallet model for TRON addresses"""
    __tablename__ = 'user_wallets'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    address = Column(String, nullable=False, unique=True)
    private_key_encrypted = Column(String, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="wallets")
    deposits = relationship("Deposit", back_populates="wallet")


class Deposit(BaseModel):
    """Deposit model for tracking TRX deposits"""
    __tablename__ = 'deposits'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    wallet_id = Column(Integer, ForeignKey('user_wallets.id'), nullable=False)
    tx_hash = Column(String, nullable=False, unique=True)
    amount_trx = Column(Numeric(precision=18, scale=6), nullable=False)
    confirmations = Column(Integer, default=0, nullable=False)
    status = Column(Enum(DepositStatus), default=DepositStatus.pending, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="deposits")
    wallet = relationship("UserWallet", back_populates="deposits")


class Withdrawal(BaseModel):
    """Withdrawal model for tracking TRX withdrawals"""
    __tablename__ = 'withdrawals'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount_trx = Column(Numeric(precision=18, scale=6), nullable=False)
    to_address = Column(String, nullable=False)
    tx_hash = Column(String, nullable=True)
    status = Column(Enum(WithdrawalStatus), default=WithdrawalStatus.pending, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="withdrawals")


class ReferralCommission(BaseModel):
    """Referral commission model for tracking commissions"""
    __tablename__ = 'referral_commissions'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # Beneficiary
    referred_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # Generator
    participation_id = Column(Integer, ForeignKey('campaign_participations.id'), nullable=True)
    deposit_id = Column(Integer, ForeignKey('deposits.id'), nullable=True)
    type = Column(Enum(CommissionType), nullable=False)
    status = Column(Enum(CommissionStatus), nullable=False, default=CommissionStatus.pending)
    amount_trx = Column(Numeric(precision=18, scale=6), nullable=False)
    percentage = Column(Numeric(precision=5, scale=4), nullable=False)
    
    # Relationships
    beneficiary = relationship("User", foreign_keys=[user_id], back_populates="commissions_received")
    referrer = relationship("User", foreign_keys=[referred_user_id], back_populates="commissions_generated")
    participation = relationship("CampaignParticipation")
    deposit = relationship("Deposit")


class Transaction(BaseModel):
    """Transaction model for tracking all financial operations"""
    __tablename__ = 'transactions'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.pending)
    amount_trx = Column(Numeric(precision=18, scale=6), nullable=False)
    balance_type = Column(Enum(BalanceType), nullable=False)
    reference_id = Column(String, nullable=True)
    description = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions")


class CampaignReport(BaseModel):
    """Campaign report model for user reports"""
    __tablename__ = 'campaign_reports'
    
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)
    reporter_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    reason = Column(Enum(ReportReason), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(ReportStatus), default=ReportStatus.pending, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="reports")
    reporter = relationship("User")
