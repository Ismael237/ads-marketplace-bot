from __future__ import annotations

from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

import config
from database.models import User, UserWallet, Deposit, DepositStatus, Transaction, TransactionType, BalanceType
from services.referral_service import ReferralService
from utils.crypto import encrypt_text, decrypt_text
from utils.tron_client import get_tron_client, address_from_private_key_hex
from utils.logger import get_logger


logger = get_logger("wallet_service")


class WalletService:
    def __init__(self, db: Session):
        self.db = db
        self.tron = get_tron_client()

    def get_or_create_user_wallet(self, user: User) -> UserWallet:
        existing = self.db.query(UserWallet).filter(UserWallet.user_id == user.id).first()
        if existing:
            return existing
        wallet = self.tron.generate_wallet()
        return UserWallet.create(
            self.db,
            user_id=user.id,
            address=wallet["address"],
            private_key_encrypted=encrypt_text(wallet["private_key"]),
        )

    def get_user_wallet_address(self, user: User) -> str:
        wallet = self.get_or_create_user_wallet(user)
        return wallet.address

    def record_deposit(
        self,
        user: User,
        wallet: UserWallet,
        tx_hash: str,
        amount_trx: Decimal,
        status: DepositStatus = DepositStatus.pending,
    ) -> Deposit:
        dep = Deposit.create(
            self.db,
            user_id=user.id,
            wallet_id=wallet.id,
            tx_hash=tx_hash,
            amount_trx=amount_trx,
            status=status,
        )
        return dep

    def confirm_deposit(self, deposit: Deposit) -> Deposit:
        if deposit.status == DepositStatus.confirmed:
            return deposit
        user = self.db.query(User).filter(User.id == deposit.user_id).first()
        user.ad_balance += deposit.amount_trx
        user.total_spent = user.total_spent or Decimal("0")
        user.save(self.db)
        deposit.status = DepositStatus.confirmed
        deposit.save(self.db)
        Transaction.create(
            self.db,
            user_id=user.id,
            type=TransactionType.deposit,
            amount_trx=deposit.amount_trx,
            balance_type=BalanceType.ad_balance,
            reference_id=str(deposit.id),
            description="Deposit confirmed",
        )
        # Pay referral commission on deposit if sponsor exists
        if user.sponsor_id:
            sponsor = self.db.query(User).filter(User.id == user.sponsor_id).first()
            if sponsor:
                ReferralService(self.db).pay_deposit_commission(
                    sponsor=sponsor,
                    referred_user=user,
                    amount_trx=deposit.amount_trx,
                    percentage=Decimal(str(config.DEPOSIT_COMMISSION_RATE)),
                    deposit_id=deposit.id,
                )
        # Autosweep from user deposit wallet to main wallet (if configured)
        try:
            rate = Decimal(str(config.DEPOSIT_TO_MAIN_WALLET_RATE))
            if rate > 0:
                uw = self.db.query(UserWallet).filter(UserWallet.id == deposit.wallet_id).first()
                if uw and config.TRON_PRIVATE_KEY:
                    main_wallet_address = address_from_private_key_hex(config.TRON_PRIVATE_KEY)
                    sweep_amount = (deposit.amount_trx * rate).quantize(Decimal("0.000001"))
                    from_private_key_hex = decrypt_text(uw.private_key_encrypted)
                    # Best-effort sweep; errors are logged but don't break deposit confirmation
                    self.tron.transfer_trx(from_private_key_hex, main_wallet_address, float(sweep_amount))
        except Exception as exc:
            logger.error(f"Autosweep failed for deposit {deposit.id}: {exc}")
        return deposit


