from __future__ import annotations

from decimal import Decimal
from math import ceil

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

    # ===== History / Transactions =====
    @staticmethod
    def _apply_history_filter(q, filter_key: str):
        if filter_key == "all":
            return q
        if filter_key == "deposits":
            return q.filter(Transaction.type == TransactionType.deposit)
        if filter_key == "ads":
            return q.filter(Transaction.type == TransactionType.campaign_spend)
        if filter_key == "withdrawals":
            return q.filter(Transaction.type == TransactionType.withdrawal)
        return q

    @staticmethod
    def get_transactions_for_user(user_id: int, filter_key: str, page: int, page_size: int) -> tuple[list[Transaction], int, int]:
        """Return (items, total_pages, page) for a user's transactions.
        filter_key in {"all","deposits","ads","withdrawals"}
        """
        with get_db_session() as db:
            base_q = db.query(Transaction).filter(Transaction.user_id == int(user_id))
            q = WalletService._apply_history_filter(base_q, filter_key)
            total = q.count()
            total_pages = max(1, ceil(total / page_size))
            page = max(1, min(page, total_pages))
            items = (
                q.order_by(Transaction.id.desc())
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
            )
            return items, total_pages, page

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
