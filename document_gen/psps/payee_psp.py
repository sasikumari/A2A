import uuid
import xmlschema
import xml.etree.ElementTree as ET
from banks.beneficiary_bank import BeneficiaryBank
from switch.upi_switch import UPISwitch, VPARegistry, now_ts

class PayeePSP:
    def __init__(self, bank: BeneficiaryBank, switch: UPISwitch, registry: VPARegistry, schema_dir="api/schemas"):
        self.bank = bank
        self.switch = switch
        self.registry = registry
        self.schema_dir = schema_dir

    def resolve_bank_by_ifsc(self, ifsc: str):
        """
        Given an IFSC, return the beneficiary bank instance if it matches this PSP's bank.
        Simple heuristic: IFSC begins with bank.code (as produced in ValAdd response).
        """
        if not ifsc:
            return None
        if ifsc.startswith(self.bank.code):
            return self.bank
        return None

    def initiate_collect_xml(self, payee_vpa: str, payer_vpa: str, amount: float, note: str) -> str:
        xml = f"""<CollectRequest>
  <PayeeVPA>{payee_vpa}</PayeeVPA>
  <PayerVPA>{payer_vpa}</PayerVPA>
  <Amount>{amount:.2f}</Amount>
  <Note>{note}</Note>
</CollectRequest>"""
        schema = xmlschema.XMLSchema(f"{self.schema_dir}/upi_collect_request.xsd")
        if not schema.is_valid(xml):
            raise ValueError("Invalid CollectRequest XML")
        return xml

    def send_collect(self, xml_req: str, payer_approval_fn):
        return self.switch.handle_collect(xml_req, payer_approval_fn)

    def process_valadd_request(self, xml_req: str):
        """
        Handle ValAdd (Validate & Add) requests routed from the switch.
        Validates payload, checks VPA registry, and returns NPCI-compliant response XML.
        """
        req_schema = xmlschema.XMLSchema(f"{self.schema_dir}/upi_req_valadd.xsd")
        if not req_schema.is_valid(xml_req):
            raise ValueError("Invalid ValAdd request XML")

        ns = {"upi": "http://npci.org/upi/schema/"}
        root = ET.fromstring(xml_req)
        payer_elem = root.find("upi:Payer", ns)
        payee_elem = root.find("upi:Payee", ns)
        payer_vpa = payer_elem.attrib.get("addr", "") if payer_elem is not None else ""
        payee_vpa = payee_elem.attrib.get("addr", "") if payee_elem is not None else ""

        print(f"[Payee PSP] Validate Address: {payer_vpa} → {payee_vpa}")

        try:
            bank = self.registry.resolve(payee_vpa)
            account = bank.get_account_by_vpa(payee_vpa)
            result = "SUCCESS"
            err_code = ""
        except Exception:
            result = "FAILURE"
            err_code = "U17"
            account = None
            bank = self.bank

        ns_uri = "http://npci.org/upi/schema/"
        ET.register_namespace("upi", ns_uri)
        resp_root = ET.Element(f"{{{ns_uri}}}RespValAdd")

        head = ET.SubElement(resp_root, f"{{{ns_uri}}}Head")
        head.set("ver", "1.0")
        head.set("ts", now_ts())
        head.set("orgId", "PAYEEPSP")
        head.set("msgId", "VALADD_" + str(uuid.uuid4().int)[-6:])
        head.set("prodType", "UPI")

        txn = ET.SubElement(resp_root, f"{{{ns_uri}}}Txn")
        txn.set("id", str(uuid.uuid4()))
        txn.set("type", "ValAdd")
        txn.set("note", "Address validation response")
        txn.set("custRef", payer_vpa)

        resp = ET.SubElement(resp_root, f"{{{ns_uri}}}Resp")
        resp.set("reqMsgId", "VALADD_REQ")
        resp.set("result", result)
        resp.set("errCode", err_code)
        resp.set("maskName", payee_vpa.split("@")[0][:3] + "****" if payee_vpa else "")
        resp.set("code", "00" if result == "SUCCESS" else "U17")
        resp.set("type", "VPA")
        resp.set("IFSC", bank.code + "001")
        resp.set("accType", "SAVINGS")
        resp.set("IIN", "999999")
        resp.set("pType", "UPIMANDATE" if payee_vpa.endswith("@umn") else "")

        merchant = ET.SubElement(resp, f"{{{ns_uri}}}Merchant")
        ET.SubElement(merchant, f"{{{ns_uri}}}Identifier", subCode="", mid="", sid="", tid="", merchantType="", merchantGenre="", pinCode="", regIdNo="", tier="", onBoardingType="")
        ET.SubElement(merchant, f"{{{ns_uri}}}Name", brand="", legal="", franchise="")
        ET.SubElement(merchant, f"{{{ns_uri}}}Ownership", type="")

        if payee_vpa.endswith("@umn"):
            ET.SubElement(resp, f"{{{ns_uri}}}FeatureSupported", value="01-MANDATE")

        xml_resp = ET.tostring(resp_root, encoding="utf-8", xml_declaration=True).decode("utf-8")

        try:
            resp_schema = xmlschema.XMLSchema(f"{self.schema_dir}/upi_reesp_valadd.xsd")
            if not resp_schema.is_valid(xml_resp):
                raise ValueError("Generated RespValAdd XML failed schema validation")
        except Exception as e:
            print(f"[Payee PSP] ⚠️ RespValAdd XML validation warning: {e}")

        print(f"\n[Payee PSP] Generated RespValAdd XML:\n{xml_resp}\n")
        return xml_resp, result

    def resolve_payee(self, payee_vpa: str):
        bank = self.registry.resolve(payee_vpa)
        account = bank.get_account_by_vpa(payee_vpa)
        return bank, account.id

    def process_auth_details(self, req_xml: str) -> str:
        """
        Respond to ReqAuthDetails with payee account details and IFSC.
        """
        ns = "http://npci.org/upi/schema/"
        ET.register_namespace("upi", ns)
        root = ET.fromstring(req_xml)
        # Extract payee for lookup (defensive parse)
        payee_vpa = ""
        for el in root.iter():
            if el.tag.endswith("Payee"):
                payee_vpa = el.attrib.get("addr", "") or payee_vpa
        try:
            account = self.bank.get_account_by_vpa(payee_vpa)
        except Exception:
            account = None

        resp_root = ET.Element(f"{{{ns}}}RespAuthDetails")
        head = ET.SubElement(resp_root, f"{{{ns}}}Head")
        head.set("ver", "2.0")
        head.set("ts", now_ts())
        head.set("orgId", "PAYEEPSP")
        head.set("msgId", "AUTH_" + str(uuid.uuid4().int)[-6:])

        # Echo minimal Txn from request if present
        txn_req = None
        for el in root.iter():
            if el.tag.endswith("Txn"):
                txn_req = el
                break
        txn = ET.SubElement(resp_root, f"{{{ns}}}Txn")
        if txn_req is not None:
            for k, v in txn_req.attrib.items():
                txn.set(k, v)
        txn.set("type", "PAY")

        # Payer echo (optional)
        payer = ET.SubElement(resp_root, f"{{{ns}}}Payer")
        payer.set("addr", "")  # unknown here
        payer.set("name", "")
        payer.set("seqNum", "1")
        payer.set("type", "PERSON")
        ET.SubElement(payer, f"{{{ns}}}Amount", value="0.00", curr="INR")

        # Payee with account details
        payees = ET.SubElement(resp_root, f"{{{ns}}}Payees")
        payee = ET.SubElement(payees, f"{{{ns}}}Payee")
        payee.set("addr", payee_vpa or "")
        payee.set("name", "")
        payee.set("seqNum", "1")
        payee.set("type", "ENTITY")
        ET.SubElement(payee, f"{{{ns}}}Amount", value="0.00", curr="INR")
        ac = ET.SubElement(payee, f"{{{ns}}}Ac")
        ac.set("addrType", "ACCOUNT")
        ET.SubElement(ac, f"{{{ns}}}Detail", name="IFSC", value=(self.bank.code + "001"))
        ET.SubElement(ac, f"{{{ns}}}Detail", name="ACTYPE", value="SAVING")
        ET.SubElement(ac, f"{{{ns}}}Detail", name="ACNUM", value=(account.id if account else "UNKNOWN"))

        xml_resp = ET.tostring(resp_root, encoding="utf-8", xml_declaration=True).decode("utf-8")
        print(f"\n[Payee PSP] Generated RespAuthDetails XML:\n{xml_resp}\n")
        return xml_resp

    def process_txn_confirmation(self, req_xml: str) -> str:
        """
        Acknowledge ReqTxnConfirmation.
        """
        ns = "http://npci.org/upi/schema/"
        ET.register_namespace("upi", ns)
        root = ET.fromstring(req_xml)

        # Extract Txn to echo
        txn_req = None
        for el in root.iter():
            if el.tag.endswith("Txn"):
                txn_req = el
                break

        resp_root = ET.Element(f"{{{ns}}}RespTxnConfirmation")
        head = ET.SubElement(resp_root, f"{{{ns}}}Head")
        head.set("ver", "2.0")
        head.set("ts", now_ts())
        head.set("orgId", "PAYEEPSP")
        head.set("msgId", "TXNCONF_" + str(uuid.uuid4().int)[-6:])

        txn = ET.SubElement(resp_root, f"{{{ns}}}Txn")
        if txn_req is not None:
            for k, v in txn_req.attrib.items():
                txn.set(k, v)
        txn.set("type", "TxnConfirmation")

        resp = ET.SubElement(resp_root, f"{{{ns}}}Resp")
        resp.set("reqMsgId", head.attrib.get("msgId", ""))
        resp.set("result", "SUCCESS")

        xml_resp = ET.tostring(resp_root, encoding="utf-8", xml_declaration=True).decode("utf-8")
        print(f"\n[Payee PSP] Generated RespTxnConfirmation XML:\n{xml_resp}\n")
        return xml_resp