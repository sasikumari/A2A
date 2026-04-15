from dataclasses import dataclass
from datetime import datetime
import time
import uuid
from typing import Dict


def gen_utr(bank_code: str):
    return f"{bank_code}{datetime.utcnow().strftime('%y%m%d')}{str(uuid.uuid4().int)[-8:]}"


@dataclass
class CBSAccount:
    id: str
    vpa: str
    name: str
    bank_code: str
    balance: float


class DummyCBS:
    """
    Minimal in-memory Core Banking System (CBS) simulator.
    Holds accounts and performs debit/credit with optional latency,
    returning UTRs for postings. Banks delegate to this for state.
    """

    def __init__(self, bank_code: str, bus):
        self.bank_code = bank_code
        self.bus = bus
        self._accounts_by_id: Dict[str, CBSAccount] = {}

    # Accounts
    def add_account(self, account: CBSAccount):
        self._accounts_by_id[account.id] = account

    def get_account_by_vpa(self, vpa: str) -> CBSAccount:
        for acc in self._accounts_by_id.values():
            if acc.vpa == vpa:
                return acc
        raise ValueError("Unknown VPA")

    def get_account_by_id(self, account_id: str) -> CBSAccount:
        if account_id not in self._accounts_by_id:
            raise ValueError("Unknown Account ID")
        return self._accounts_by_id[account_id]

    # Pre-validations
    def has_sufficient_balance(self, account_id: str, amount: float) -> bool:
        return self.get_account_by_id(account_id).balance >= amount

    def prevalidate_credit(self, amount: float) -> bool:
        return amount > 0

    # Postings
    def debit(self, account_id: str, amount: float, simulate_latency_ms: int = 20) -> str:
        if amount <= 0:
            raise ValueError("Invalid debit amount")
        if not self.has_sufficient_balance(account_id, amount):
            raise ValueError("Insufficient funds")
        # simulate small CBS latency
        if simulate_latency_ms:
            time.sleep(simulate_latency_ms / 1000.0)
        acc = self.get_account_by_id(account_id)
        acc.balance -= amount
        utr = gen_utr(self.bank_code)
        self.bus.publish_event("bank_events", {
            "utr": utr, "type": "DEBIT", "account": account_id, "amount": amount,
            "ts": datetime.utcnow().isoformat()
        })
        return utr

    def credit(self, account_id: str, amount: float, simulate_latency_ms: int = 20) -> str:
        if amount <= 0:
            raise ValueError("Invalid credit amount")
        # simulate small CBS latency
        if simulate_latency_ms:
            time.sleep(simulate_latency_ms / 1000.0)
        acc = self.get_account_by_id(account_id)
        acc.balance += amount
        utr = gen_utr(self.bank_code)
        self.bus.publish_event("bank_events", {
            "utr": utr, "type": "CREDIT", "account": account_id, "amount": amount,
            "ts": datetime.utcnow().isoformat()
        })
        return utr


