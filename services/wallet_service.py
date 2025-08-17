from __future__ import annotations

from decimal import Decimal

from database.database import get_db_session
from database.models import (
    User,
    UserWallet,
    Withdrawal,
    WithdrawalStatus,
    Transaction,
    TransactionType,
    BalanceType,
    TransactionStatus,
)
from utils.crypto import encrypt_text
from utils.tron_client import get_tron_client
from utils.logger import get_logger


logger = get_logger("wallet_service")


class WalletService:
    tron = get_tron_client()

    # ===== Basic user helpers =====
    @staticmethod
    def get_user_by_telegram_id(telegram_id: str) -> User | None:
        with get_db_session() as db:
            return db.query(User).filter(User.telegram_id == str(telegram_id)).first()

    # ===== Wallet helpers =====
    @staticmethod
    def get_or_create_user_wallet(user_id: int) -> UserWallet:
        with get_db_session() as db:
            existing = db.query(UserWallet).filter(UserWallet.user_id == int(user_id)).first()
            if existing:
                return existing
            wallet = WalletService.tron.generate_wallet()
            uw = UserWallet(
                user_id=int(user_id),
                address=wallet["address"],
                private_key_encrypted=encrypt_text(wallet["private_key"]),
            )
            db.add(uw)
            db.commit()
            db.refresh(uw)
            return uw

    @staticmethod
    def get_user_wallet_address_by_telegram(telegram_id: str) -> str | None:
        user = WalletService.get_user_by_telegram_id(telegram_id)
        if not user:
            return None
        uw = WalletService.get_or_create_user_wallet(user.id)
        return uw.address

    # ===== Withdrawals =====
    @staticmethod
    def create_withdrawal(user_id: int, amount: Decimal, to_address: str) -> tuple[Withdrawal | None, str | None]:
        """
        Create a withdrawal request and log a pending transaction.
        Returns (withdrawal, error) where error in {None, 'not_found', 'insufficient_balance'}
        """
        with get_db_session() as db:
            user = db.query(User).get(int(user_id))
            if not user:
                return None, "not_found"
            if user.earn_balance < amount:
                return None, "insufficient_balance"

            # Deduct balance and create withdrawal
            user.earn_balance = (user.earn_balance or Decimal("0")) - amount
            w = Withdrawal(
                user_id=user.id,
                amount_trx=amount,
                to_address=to_address,
                status=WithdrawalStatus.pending,
            )
            db.add(w)
            db.flush()  # ensure w.id

            # Log transaction as pending
            db.add(
                Transaction(
                    user_id=user.id,
                    type=TransactionType.withdrawal,
                    status=TransactionStatus.pending,
                    amount_trx=amount,
                    balance_type=BalanceType.earn_balance,
                    reference_id=str(w.id),
                    description="Withdrawal requested",
                )
            )

            db.commit()
            db.refresh(w)
            return w, None
