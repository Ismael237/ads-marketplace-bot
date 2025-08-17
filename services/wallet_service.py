from __future__ import annotations

from decimal import Decimal
from math import ceil
from datetime import datetime

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
    Deposit,
    DepositStatus,
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

    @staticmethod
    def list_wallets() -> list[UserWallet]:
        with get_db_session() as db:
            return db.query(UserWallet).all()

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

    # ===== Deposits =====
    @staticmethod
    def upsert_deposit_and_credit_if_confirmed(
        user_id: int,
        wallet_id: int,
        tx_hash: str,
        amount_trx: Decimal,
        confirmations: int,
        now: datetime | None = None,
    ) -> tuple[Deposit, bool]:
        """Create deposit if not exists. If confirmed (>=19) and not previously credited,
        credit user's ad_balance and add a deposit Transaction. Returns (deposit, credited_now).
        """
        now = now or datetime.utcnow()
        with get_db_session() as db:
            dep = db.query(Deposit).filter(Deposit.tx_hash == str(tx_hash)).first()
            credited_now = False
            if not dep:
                dep = Deposit(
                    user_id=int(user_id),
                    wallet_id=int(wallet_id),
                    tx_hash=str(tx_hash),
                    amount_trx=amount_trx,
                    confirmations=int(confirmations or 0),
                    status=DepositStatus.confirmed if int(confirmations or 0) >= 19 else DepositStatus.pending,
                    created_at=now,
                    confirmed_at=now if int(confirmations or 0) >= 19 else None,
                )
                db.add(dep)
            else:
                # Update confirmations/status if it already exists
                dep.confirmations = int(confirmations or 0)
                if dep.status != DepositStatus.confirmed and dep.confirmations >= 19:
                    dep.status = DepositStatus.confirmed
                    dep.confirmed_at = now

            # If confirmed and no existing deposit transaction, credit
            if dep.status == DepositStatus.confirmed:
                tx_exist = (
                    db.query(Transaction)
                    .filter(
                        Transaction.user_id == int(user_id),
                        Transaction.type == TransactionType.deposit,
                        Transaction.reference_id == str(tx_hash),
                    )
                    .first()
                )
                if not tx_exist:
                    user = db.query(User).get(int(user_id))
                    user.ad_balance = (user.ad_balance or Decimal("0")) + amount_trx
                    db.add(
                        Transaction(
                            user_id=int(user_id),
                            type=TransactionType.deposit,
                            status=TransactionStatus.completed,
                            amount_trx=amount_trx,
                            balance_type=BalanceType.ad_balance,
                            description=f"Deposit {tx_hash}",
                            reference_id=str(tx_hash),
                        )
                    )
                    credited_now = True

            db.commit()
            db.refresh(dep)
            return dep, credited_now

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

    @staticmethod
    def fetch_pending_withdrawals() -> list[Withdrawal]:
        with get_db_session() as db:
            return db.query(Withdrawal).filter(
                Withdrawal.status.in_([WithdrawalStatus.pending, WithdrawalStatus.processing])
            ).all()

    @staticmethod
    def mark_withdrawal_completed(wd_id: int, tx_hash: str) -> None:
        with get_db_session() as db:
            wd = db.query(Withdrawal).get(int(wd_id))
            if not wd:
                return
            wd.tx_hash = tx_hash
            wd.status = WithdrawalStatus.completed
            wd.processed_at = datetime.utcnow()
            # Update original transaction (keep amount; do not adjust balance here)
            tx_record = (
                db.query(Transaction)
                .filter(Transaction.reference_id == str(wd.id), Transaction.type == TransactionType.withdrawal)
                .first()
            )
            if tx_record:
                tx_record.status = TransactionStatus.completed
                tx_record.description = f"Withdrawal {tx_hash}"
            db.commit()

    @staticmethod
    def mark_withdrawal_failed(wd_id: int, reason: str) -> None:
        with get_db_session() as db:
            wd = db.query(Withdrawal).get(int(wd_id))
            if not wd:
                return
            wd.status = WithdrawalStatus.failed
            # Refund user's balance because it was deducted at request time
            user = db.query(User).get(int(wd.user_id))
            if user:
                user.earn_balance = (user.earn_balance or Decimal("0")) + Decimal(wd.amount_trx)
            tx_record = (
                db.query(Transaction)
                .filter(Transaction.reference_id == str(wd.id), Transaction.type == TransactionType.withdrawal)
                .first()
            )
            if tx_record:
                tx_record.status = TransactionStatus.failed
                tx_record.description = f"Withdrawal failed: {reason}"
            db.commit()
