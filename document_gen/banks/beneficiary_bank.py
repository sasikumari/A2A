from dataclasses import dataclass
from banks.cbs import DummyCBS, CBSAccount, gen_utr

@dataclass
class Account:
    id: str
    vpa: str
    name: str
    bank_code: str
    balance: float

class BeneficiaryBank:
    def __init__(self, code: str, ledger, bus):
        self.code = code
        self.ledger = ledger
        self.bus = bus
        self.cbs = DummyCBS(bank_code=code, bus=bus)

    def add_account(self, acc: Account):
        self.cbs.add_account(CBSAccount(**acc.__dict__))

    def get_account_by_vpa(self, vpa: str):
        return self.cbs.get_account_by_vpa(vpa)

    def prevalidate_credit(self, amount: float) -> bool:
        # Simple demo prevalidation: accept positive amounts
        return self.cbs.prevalidate_credit(amount)

    def credit(self, account_id: str, amount: float) -> str:
        return self.cbs.credit(account_id, amount)
