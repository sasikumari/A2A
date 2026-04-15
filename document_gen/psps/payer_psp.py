import xmlschema
from banks.remitter_bank import RemitterBank
from switch.upi_switch import UPISwitch

class PayerPSP:
    def __init__(self, bank: RemitterBank, switch: UPISwitch, schema_dir="api/schemas"):
        self.bank = bank
        self.switch = switch
        self.schema_dir = schema_dir

    def validate_vpa(self, vpa: str) -> bool:
        return "@" in vpa

    def initiate_push_xml(self, payer_vpa: str, payee_vpa: str, amount: float, note: str, pin: str) -> str:
        if not self.bank.auth_service.authorize(payer_vpa, pin):
            raise ValueError("Invalid PIN")
        xml = f"""<PayRequest>
  <PayerVPA>{payer_vpa}</PayerVPA>
  <PayeeVPA>{payee_vpa}</PayeeVPA>
  <Amount>{amount:.2f}</Amount>
  <Note>{note}</Note>
</PayRequest>"""
        schema = xmlschema.XMLSchema(f"{self.schema_dir}/upi_pay_request.xsd")
        if not schema.is_valid(xml):
            raise ValueError("Invalid PayRequest XML")
        return xml

    def send_push(self, xml_req: str):
        return self.switch.handle_push(xml_req)
