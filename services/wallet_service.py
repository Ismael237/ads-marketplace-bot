from __future__ import annotations

from sqlalchemy.orm import Session

from database.models import User, UserWallet
from utils.crypto import encrypt_text
from utils.tron_client import get_tron_client
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

