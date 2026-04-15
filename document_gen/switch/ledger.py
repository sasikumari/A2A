from dataclasses import dataclass
from datetime import datetime
import typing

@dataclass
class Transaction:
    rrn: str
    payer_vpa: str
    payee_vpa: str
    amount: float
    note: str
    utr_debit: typing.Optional[str]
    utr_credit: typing.Optional[str]
    status: str
    created_at: str

class Ledger:
    def __init__(self):
        self.entries = []

    def record(self, tx: Transaction):
        self.entries.append(tx)

    def fetch(self, rrn: str):
        for e in self.entries:
            if e.rrn == rrn:
                return e
        return None
