from dataclasses import dataclass
from banks.cbs import DummyCBS, CBSAccount

@dataclass
class Account:
    id: str
    vpa: str
    name: str
    bank_code: str
    balance: float

class ICICIBank:
    def __init__(self, code: str, auth_service, ledger, bus):
        self.code = code
        self.auth_service = auth_service
        self.ledger = ledger
        self.bus = bus
        # Delegate state and postings to DummyCBS
        self.cbs = DummyCBS(bank_code=code, bus=bus)

    def add_account(self, acc: Account):
        self.cbs.add_account(CBSAccount(**acc.__dict__))

    def get_account_by_vpa(self, vpa: str):
        return self.cbs.get_account_by_vpa(vpa)

    def debit(self, account_id: str, amount: float) -> str:
        # Use CBS; balance validation and events are inside CBS
        return self.cbs.debit(account_id, amount)

    def credit(self, account_id: str, amount: float) -> str:
        # Use CBS
        return self.cbs.credit(account_id, amount)
