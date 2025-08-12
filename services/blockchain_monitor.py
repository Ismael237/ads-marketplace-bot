from __future__ import annotations

from decimal import Decimal
from typing import List
from sqlalchemy.orm import Session

import config
from database.models import UserWallet, Deposit, DepositStatus
from services.wallet_service import WalletService
from utils.tron_client import get_tron_client
from utils.logger import get_logger


logger = get_logger("blockchain_monitor")


class BlockchainMonitor:
    """
    Simplified monitor: for MVP we assume deposits are identified externally and
    recorded, or we rely on limited provider capabilities. This class exposes
    hooks to check confirmations and mark deposits as confirmed once threshold
    is reached.
    """

    def __init__(self, db: Session):
        self.db = db
        self.tron = get_tron_client()

    def check_pending_deposits(self) -> int:
        pending: List[Deposit] = (
            self.db.query(Deposit)
            .filter(Deposit.status == DepositStatus.pending)
            .all()
        )
        confirmed_count = 0
        for dep in pending:
            info = self.tron.get_transaction_info(dep.tx_hash)
            if not info:
                continue
            block_number = info.get("blockNumber")
            confirmations = self.tron.get_confirmations(block_number)
            if confirmations is not None and confirmations >= 19:
                dep.confirmations = confirmations
                # Confirm deposit (credits balance, creates tx, commissions, sweep)
                ws = WalletService(self.db)
                ws.confirm_deposit(dep)
                confirmed_count += 1
        if confirmed_count:
            logger.info(f"Confirmed {confirmed_count} deposits")
        return confirmed_count


