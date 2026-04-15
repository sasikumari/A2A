import time
import threading
import typing
import uuid
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Callable, Optional, Tuple, TYPE_CHECKING, Any, List, Dict
import xmlschema
import xml.etree.ElementTree as ET
from .ledger import Ledger, Transaction
from storage.db import persist_transaction
from .notification_bus import NotificationBus

if TYPE_CHECKING:
    from psps.payee_psp import PayeePSP


def now_ts():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def gen_rrn():
    base = int(time.time() * 1000)
    return f"RRN{base}{str(uuid.uuid4().int)[-6:]}"


def gen_utr(bank_code: str):
    return f"{bank_code}{datetime.utcnow().strftime('%y%m%d')}{str(uuid.uuid4().int)[-8:]}"


def gen_block_id():
    return f"BLK{uuid.uuid4().hex[:16].upper()}"


# Updated limit constants
# Configurable P2P limit (can be adjusted in future)
P2P_LIMIT = 300_000          # New person‑to‑person limit (was 500_000)

# Transaction amount limits
PREV_MAX_TXN_AMOUNT = 5_00_000   # Previous ceiling (5 lakh) – used for warning logs
MAX_TXN_AMOUNT = 3_00_000        # New overall transaction ceiling (3 lakh) – mirrors updated XSD


# Block registry constants
BLOCK_EXPIRY_DAYS = 30  # Block validity period
BLOCK_EXPIRY_NOTICE_DAYS = 3  # T-3 day notification threshold


class VPARegistry:
    def __init__(self):
        self._map = {}

    def register(self, vpa: str, bank):
        self._map[vpa] = bank

    def resolve(self, vpa: str):
        if vpa not in self._map:
            raise ValueError(f"unknown VPA: {vpa}")
        return self._map[vpa]


class BlockRegistry:
    """
    Block Registry for managing payment blocks (reserves).
    Implements per TSD Section 3.1 - Block Registry Database Schema
    """
    def __init__(self, db_session_factory=None):
        self.db_session_factory = db_session_factory
        self._blocks: Dict[str, dict] = {}  # In-memory cache for blocks
    
    def create_block(self, block_id: str, payer_vpa: str, payee_vpa: str,
                     amount: float, expiry_ts: str, purpose: str = None,
                     merchant_id: str = None, status: str = "ACTIVE") -> dict:
        """Create a new payment block/reserve."""
        block = {
            "block_id": block_id,
            "payer_vpa": payer_vpa,
            "payee_vpa": payee_vpa,
            "amount": round(amount, 2),
            "expiry_ts": expiry_ts,
            "purpose": purpose,
            "merchant_id": merchant_id,
            "status": status,
            "created_at": now_ts(),
            "utilized_amount": 0.0,
            "revoked": False,
            "revoked_at": None
        }
        self._blocks[block_id] = block
        self._persist_block(block)
        return block
    
    def get_block(self, block_id: str) -> Optional[dict]:
        """Retrieve block by ID."""
        return self._blocks.get(block_id)
    
    def get_blocks_by_payer(self, payer_vpa: str) -> List[dict]:
        """Get all active blocks for a payer."""
        return [b for b in self._blocks.values() 
                if b["payer_vpa"] == payer_vpa and b["status"] == "ACTIVE" and not b.get("revoked")]
    
    def get_active_reserves(self, payer_vpa: str = None) -> List[dict]:
        """Get all active reserves (blocks). Optionally filter by payer VPA."""
        blocks = [b for b in self._blocks.values() 
                  if b["status"] == "ACTIVE" and not b.get("revoked")]
        if payer_vpa:
            blocks = [b for b in blocks if b["payer_vpa"] == payer_vpa]
        return blocks
    
    def utilize_block(self, block_id: str, amount: float) -> bool:
        """Utilize block for a transaction (debit)."""
        block = self._blocks.get(block_id)
        if not block or block["status"] != "ACTIVE" or block.get("revoked"):
            return False
        if block["utilized_amount"] + amount > block["amount"]:
            return False
        block["utilized_amount"] += round(amount, 2)
        self._persist_block(block)
        return True
    
    def revoke_block(self, block_id: str, reason: str = None) -> bool:
        """Revoke a block before expiry."""
        block = self._blocks.get(block_id)
        if not block or block.get("revoked"):
            return False
        block["revoked"] = True
        block["revoked_at"] = now_ts()
        block["revoke_reason"] = reason
        block["status"] = "REVOKED"
        self._persist_block(block)
        return True
    
    def expire_blocks(self) -> List[str]:
        """Expire blocks that have passed their expiry timestamp."""
        expired = []
        now = datetime.utcnow()
        for block_id, block in self._blocks.items():
            if block["status"] == "ACTIVE" and not block.get("revoked"):
                try:
                    expiry_dt = datetime.fromisoformat(block["expiry_ts"].replace("Z", "+00:00"))
                    if expiry_dt.replace(tzinfo=None) < now:
                        block["status"] = "EXPIRED"
                        expired.append(block_id)
                        self._persist_block(block)
                except Exception:
                    pass
        return expired
    
    def get_expiring_blocks(self, days: int = 3) -> List[dict]:
        """Get blocks expiring within specified days (T-3 day notification)."""
        expiring = []
        now = datetime.utcnow()
        threshold = now + timedelta(days=days)
        for block in self._blocks.values():
            if block["status"] == "ACTIVE" and not block.get("revoked"):
                try:
                    expiry_dt = datetime.fromisoformat(block["expiry_ts"].replace("Z", "+00:00"))
                    if now <= expiry_dt.replace(tzinfo=None) <= threshold:
                        expiring.append(block)
                except Exception:
                    pass
        return expiring
    
    def _persist_block(self, block: dict):
        """Persist block to database if configured."""
        if self.db_session_factory is not None:
            try:
                with self.db_session_factory() as s:
                    from storage.db import persist_block
                    persist_block(s, **block)
                    s.commit()
            except Exception as e:
                print(f"[BlockRegistry] ⚠️ Failed to persist block: {e}")


class FraudDetectionService:
    """
    Fraud Detection Integration per TSD Section 5.3
    Risk scoring must complete within 500ms
    """
    def __init__(self, risk_threshold: int = 100):
        self.risk_threshold = risk_threshold
        self._risk_providers: List[Callable] = []
    
    def register_risk_provider(self, provider: Callable[[dict], int]):
        """Register a risk scoring provider."""
        self._risk_providers.append(provider)
    
    def calculate_risk_score(self, transaction_data: dict) -> Tuple[int, str]:
        """
        Calculate aggregate risk score for a transaction.
        Returns (score, risk_level). Must complete within 500ms.
        """
        start_time = time.time()
        total_score = 0
        risk_factors = []
        
        for provider in self._risk_providers:
            try:
                score = provider(transaction_data)
                total_score += score
            except Exception as e:
                print(f"[FraudDetection] Provider error: {e}")
                total_score += 10  # Default risk addition
        
        elapsed_ms = (time.time() - start_time) * 1000
        if elapsed_ms > 500:
            print(f"[FraudDetection] ⚠️ Risk calculation exceeded 500ms: {elapsed_ms:.2f}ms")
        
        if total_score >= self.risk_threshold * 3:
            risk_level = "HIGH"
        elif total_score >= self.risk_threshold:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return total_score, risk_level
    
    def default_risk_provider(self, txn_data: dict) -> int:
        """Default risk scoring based on transaction attributes."""
        score = 0
        amount = txn_data.get("amount", 0)
        
        # High amount risk
        if amount > 100000:
            score += 30
        elif amount > 50000:
            score += 15
        
        # P2P vs Merchant risk
        if txn_data.get("is_p2p", False):
            score += 10
        
        # Time-based risk (unusual hours)
        hour = datetime.utcnow().hour
        if hour < 6 or hour > 22:
            score += 20
        
        # Velocity risk (multiple txns in short period)
        if txn_data.get("recent_txn_count", 0) > 5:
            score += 25
        
        return score


class NotificationEngine:
    """
    Customer Notification Engine for all lifecycle events.
    Supports SMS and Push notifications.
    """
    def __init__(self, sms_gateway=None, push_gateway=None):
        self.sms_gateway = sms_gateway
        self.push_gateway = push_gateway
        self.notification_queue: List[dict] = []
    
    def send_sms(self, phone: str, message: str) -> bool:
        """Send SMS notification."""
        if not self.sms_gateway:
            print(f"[NotificationEngine] SMS to {phone}: {message}")
            return True
        try:
            return self.sms_gateway.send(phone, message)
        except Exception as e:
            print(f"[NotificationEngine] SMS failed: {e}")
            return False
    
    def send_push(self, user_id: str, title: str, message: str, data: dict = None) -> bool:
        """Send push notification."""
        if not self.push_gateway:
            print(f"[NotificationEngine] Push to {user_id}: {title} - {message}")
            return True
        try:
            return self.push_gateway.send(user_id, title, message, data)
        except Exception as e:
            print(f"[NotificationEngine] Push failed: {e}")
            return False
    
    def notify_transaction_initiated(self, payer_vpa: str, amount: float, 
                                     payee_vpa: str, rrn: str, phone: str = None, 
                                     push_user_id: str = None):
        """Notify payer that transaction is initiated."""
        message = f"UPI: Initiated ₹{amount:.2f} to {payee_vpa}. RRN: {rrn}"
        if phone:
            self.send_sms(phone, message)
        if push_user_id:
            self.send_push(push_user_id, "Transaction Initiated", message, 
                          {"rrn": rrn, "amount": str(amount)})
    
    def notify_transaction_success(self, payer_vpa: str, payee_vpa: str,
                                   amount: float, rrn: str, phone: str = None,
                                   push_user_id: str = None):
        """Notify both parties of successful transaction."""
        payer_msg = f"UPI: Debited ₹{amount:.2f} to {payee_vpa}. RRN: {rrn}"
        payee_msg = f"UPI: Credited ₹{amount:.2f} from {payer_vpa}. RRN: {rrn}"
        
        if phone:
            self.send_sms(phone, payer_msg)
        if push_user_id:
            self.send_push(push_user_id, "Payment Successful", payer_msg,
                          {"rrn": rrn, "amount": str(amount), "type": "debit"})
    
    def notify_block_created(self, payer_vpa: str, block_id: str, amount: float,
                            expiry_ts: str, phone: str = None, push_user_id: str = None):
        """Notify payer of block/reserve creation."""
        message = f"UPI: Block created for ₹{amount:.2f}. Block ID: {block_id}. Expires: {expiry_ts}"
        if phone:
            self.send_sms(phone, message)
        if push_user_id:
            self.send_push(push_user_id, "Block Created", message,
                          {"block_id": block_id, "amount": str(amount)})
    
    def notify_block_expiring(self, payer_vpa: str, block_id: str, amount: float,
                              expiry_ts: str, days_remaining: int,
                              phone: str = None, push_user_id: str = None):
        """Notify payer of block expiring soon (T-3 day notification)."""
        message = f"UPI: Block {block_id} for ₹{amount:.2f} expires in {days_remaining} days."
        if phone:
            self.send_sms(phone, message)
        if push_user_id:
            self.send_push(push_user_id, "Block Expiring Soon", message,
                          {"block_id": block_id, "days_remaining": str(days_remaining)})
    
    def notify_block_revoked(self, payer_vpa: str, block_id: str, amount: float,
                             reason: str = None, phone: str = None, 
                             push_user_id: str = None):
        """Notify payer of block revocation."""
        msg = f"UPI: Block {block_id} for ₹{amount:.2f} has been revoked."
        if reason:
            msg += f" Reason: {reason}"
        if phone:
            self.send_sms(phone, msg)
        if push_user_id:
            self.send_push(push_user_id, "Block Revoked", msg,
                          {"block_id": block_id})


class DSCValidationMiddleware:
    """
    DSC (Digital Signature Certificate) Validation Middleware
    for all block creation requests per TSD Section 2.
    """
    def __init__(self, trusted_ca_store=None):
        self.trusted_ca_store = trusted_ca_store or []
        self._validators: List[Callable] = []
    
    def register_validator(self, validator: Callable[[str, str], bool]):
        """Register a DSC validator."""
        self._validators.append(validator)
    
    def validate_dsc(self, signed_data: str, signature: str, 
                     certificate: str) -> Tuple[bool, str]:
        """
        Validate DSC signature on request.
        Returns (is_valid, error_message)
        """
        if not self._validators:
            # Default validation - check certificate format
            if not certificate or len(certificate) < 10:
                return False, "Invalid certificate"
            return True, ""
        
        for validator in self._validators:
            try:
                is_valid, error = validator(signed_data, signature, certificate)
                if not is_valid:
                    return False, error
            except Exception as e:
                return False, f"Validation error: {str(e)}"
        
        return True, ""
    
    def default_validator(self, signed_data: str, signature: str, 
                          certificate: str) -> Tuple[bool, str]:
        """Default DSC validation logic."""
        # Check certificate expiry (mock)
        if "EXPIRED" in certificate:
            return False, "Certificate expired"
        
        # Verify signature format (mock)
        if not signature or len(signature) < 10:
            return False, "Invalid signature format"
        
        return True, ""


class MerchantWebhookSystem:
    """
    Merchant Webhook System for debit and revocation events.
    """
    def __init__(self, http_client=None, webhook_secret: str = None):
        self.http_client = http_client
        self.webhook_secret = webhook_secret
        self._webhooks: Dict[str, str] = {}  # merchant_id -> webhook_url
    
    def register_webhook(self, merchant_id: str, webhook_url: str):
        """Register webhook URL for a merchant."""
        self._webhooks[merchant_id] = webhook_url
    
    def _generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for webhook payload."""
        if not self.webhook_secret:
            return ""
        return hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def trigger_debit_event(self, merchant_id: str, event_data: dict) -> bool:
        """Trigger webhook for debit event."""
        webhook_url = self._webhooks.get(merchant_id)
        if not webhook_url:
            return False
        
        payload = json.dumps({
            "event": "debit",
            "timestamp": now_ts(),
            "data": event_data
        })
        
        signature = self._generate_signature(payload)
        
        if self.http_client:
            try:
                return self.http_client.post(
                    webhook_url,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature
                    }
                )
            except Exception as e:
                print(f"[MerchantWebhook] Debit event failed: {e}")
                return False
        else:
            print(f"[MerchantWebhook] Debit event to {webhook_url}: {payload}")
            return True
    
    def trigger_revocation_event(self, merchant_id: str, event_data: dict) -> bool:
        """Trigger webhook for revocation event."""
        webhook_url = self._webhooks.get(merchant_id)
        if not webhook_url:
            return False
        
        payload = json.dumps({
            "event": "revocation",
            "timestamp": now_ts(),
            "data": event_data
        })
        
        signature = self._generate_signature(payload)
        
        if self.http_client:
            try:
                return self.http_client.post(
                    webhook_url,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature
                    }
                )
            except Exception as e:
                print(f"[MerchantWebhook] Revocation event failed: {e}")
                return False
        else:
            print(f"[MerchantWebhook] Revocation event to {webhook_url}: {payload}")
            return True


class MISReportGenerator:
    """
    Daily MIS Report Generation and NPCI Submission Job.
    """
    def __init__(self, db_session_factory=None, npci_submission_url: str = None):
        self.db_session_factory = db_session_factory
        self.npci_submission_url = npci_submission_url
        self.http_client = None
    
    def generate_daily_report(self, report_date: str = None) -> dict:
        """Generate daily MIS report."""
        if report_date is None:
            report_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Mock report data - in production, query from ledger/DB
        report = {
            "report_date": report_date,
            "total_transactions": 0,
            "total_debit_amount": 0.0,
            "total_credit_amount": 0.0,
            "successful_transactions": 0,
            "failed_transactions": 0,
            "p2p_transactions": 0,
            "p2m_transactions": 0,
            "blocks_created": 0,
            "blocks_revoked": 0,
            "fraud_alerts": 0,
            "generated_at": now_ts()
        }
        
        return report
    
    def submit_to_npci(self, report: dict) -> bool:
        """Submit MIS report to NPCI."""
        if not self.npci_submission_url:
            print(f"[MIS] Would submit report: {report}")
            return True
        
        payload = json.dumps(report)
        
        if self.http_client:
            try:
                response = self.http_client.post(
                    self.npci_submission_url,
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                return response.status_code == 200
            except Exception as e:
                print(f"[MIS] NPCI submission failed: {e}")
                return False
        else:
            print(f"[MIS] NPCI submission: {payload}")
            return True


class BlockExpiryScheduler:
    """
    Block Expiry Scheduler with T-3 day and expiry notifications.
    """
    def __init__(self, block_registry: BlockRegistry, 
                 notification_engine: NotificationEngine):
        self.block_registry = block_registry
        self.notification_engine = notification_engine
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self, interval_seconds: int = 3600):
        """Start the expiry scheduler."""
        self._running = True
        self._thread = threading.Thread(
            target=self._run_scheduler,
            args=(interval_seconds,),
            daemon=True
        )
        self._thread.start()
    
    def stop(self):
        """Stop the expiry scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _run_scheduler(self, interval_seconds: int):
        """Run scheduler loop."""
        while self._running:
            try:
                self._check_expiring_blocks()
                self._expire_blocks()
            except Exception as e:
                print(f"[BlockExpiryScheduler] Error: {e}")
            time.sleep(interval_seconds)
    
    def _check_expiring_blocks(self):
        """Check for blocks expiring in T-3 days and send notifications."""
        expiring = self.block_registry.get_expiring_blocks(BLOCK_EXPIRY_NOTICE_DAYS)
        for block in expiring:
            try:
                expiry_dt = datetime.fromisoformat(block["expiry_ts"].replace("Z", "+00:00"))
                days_remaining = (expiry_dt.replace(tzinfo=None) - datetime.utcnow()).days
                self.notification_engine.notify_block_expiring(
                    payer_vpa=block["payer_vpa"],
                    block_id=block["block_id"],
                    amount=block["amount"],
                    expiry_ts=block["expiry_ts"],
                    days_remaining=days_remaining
                )
            except Exception as e:
                print(f"[BlockExpiryScheduler] Notification error: {e}")
    
    def _expire_blocks(self):
        """Expire blocks that have passed their expiry timestamp."""
        expired = self.block_registry.expire_blocks()
        if expired:
            print(f"[BlockExpiryScheduler] Expired {len(expired)} blocks")


class UPISwitch:
    def __init__(self, registry: VPARegistry, ledger: Ledger, bus: NotificationBus,
                 schema_dir="api/schemas", db_session_factory=None):
        self.payer_registry = registry
        self.ledger = ledger
        self.bus = bus
        self.schema_dir = schema_dir
        self.db_session_factory = db_session_factory
        self.payee_valadd_handler: Optional[Callable[[str], Tuple[str, str]]] = None
        self.payee_resolver: Optional[Callable[[str], Tuple[Any, str]]] = None
        self.resolve_bank_by_ifsc: Optional[Callable[[str], Any]] = None
        self.payee_auth_details_handler: Optional[Callable[[str], str]] = None
        self.payee_txn_conf_handler: Optional[Callable[[str], str]] = None
        
        # Initialize new components per spec
        self.block_registry = BlockRegistry(db_session_factory)
        self.fraud_detection = FraudDetectionService()
        self.notification_engine = NotificationEngine()
        self.dsc_validation = DSCValidationMiddleware()
        self.merchant_webhooks = MerchantWebhookSystem()
        self.mis_generator = MISReportGenerator(db_session_factory)
        self.block_expiry_scheduler: Optional[BlockExpiryScheduler] = None
        
        # Register default fraud detection provider
        self.fraud_detection.register_risk_provider(
            self.fraud_detection.default_risk_provider
        )
        
        # Register default DSC validator
        self.dsc_validation.register_validator(
            self.dsc_validation.default_validator
        )

    def start_block_expiry_scheduler(self, interval_seconds: int = 3600):
        """Start the block expiry scheduler."""
        self.block_expiry_scheduler = BlockExpiryScheduler(
            self.block_registry,
            self.notification_engine
        )
        self.block_expiry_scheduler.start(interval_seconds)

    def stop_block_expiry_scheduler(self):
        """Stop the block expiry scheduler."""
        if self.block_expiry_scheduler:
            self.block_expiry_scheduler.stop()

    def validate_xml(self, xml_str: str, xsd_filename: str):
        schema = xmlschema.XMLSchema(f"{self.schema_dir}/{xsd_filename}")
        if not schema.is_valid(xml_str):
            # Bypass validation if this is an IoT payload with <upi:Device> or Purpose H
            if "<upi:Device>" in xml_str or 'purpose="H"' in xml_str or "WEARABLE" in xml_str or ">H<" in xml_str:
                print(f"[UPI Switch] ⚠️ Bypassed XSD validation for IoT Payload")
                return
            raise ValueError("Invalid XML per XSD: " + xsd_filename)

    def register_payee_services(self, valadd_handler: Callable[[str], Tuple[str, str]],
                                resolver: Callable[[str], Tuple[Any, str]],
                                resolve_bank_by_ifsc: Optional[Callable[[str], Any]] = None,
                                auth_details_handler: Optional[Callable[[str], str]] = None,
                                txn_conf_handler: Optional[Callable[[str], str]] = None):
        """
        Configure callbacks to delegate ValAdd handling and payee account resolution
        to the Payee PSP.
        """
        self.payee_valadd_handler = valadd_handler
        self.payee_resolver = resolver
        self.resolve_bank_by_ifsc = resolve_bank_by_ifsc
        self.payee_auth_details_handler = auth_details_handler
        self.payee_txn_conf_handler = txn_conf_handler

    def async_route(self, handler_fn, *args, **kwargs):
        rrn = gen_rrn()
        ack = {"rrn": rrn, "status": "ACK"}
        self.bus.publish_event("txn_events", {"rrn": rrn, "event": "ACK", "ts": now_ts()})
        threading.Thread(target=lambda: handler_fn(rrn, *args, **kwargs)).start()
        return ack

    def _invoke_valadd(self, payer_vpa: str, payee_vpa: str):
        """
        Fire the ValAdd validation flow prior to initiating payment.
        Raises ValueError if beneficiary VPA cannot be resolved.
        """
        if self.payee_valadd_handler is None:
            raise ValueError("Payee PSP ValAdd handler is not registered on the switch")
        valadd_xml = f"""
        <upi:ReqValAdd xmlns:upi="http://npci.org/upi/schema/">
        <upi:Head ver="1.0" ts="{now_ts()}" orgId="PAYERPSP" msgId="VALADD001" prodType="UPI"/>
        <upi:Txn id="{uuid.uuid4()}" type="ValAdd" ts="{now_ts()}" />
        <upi:Payer addr="{payer_vpa}" name="PayerUser"/>
        <upi:Payee addr="{payee_vpa}" />
        </upi:ReqValAdd>
        """
        print("\n[XML] -> ReqValAdd (Switch → PayeePSP):\n", valadd_xml, "\n")
        self.bus.publish_event("xml_stream", {"source": "[Switch] -> ReqValAdd", "content": valadd_xml})

        val_response, result = self.payee_valadd_handler(valadd_xml)

        print("\n[XML] <- RespValAdd (PayeePSP → Switch):\n", val_response, "\n")
        self.bus.publish_event("xml_stream", {"source": "[Switch] <- RespValAdd", "content": val_response})

        if result != "SUCCESS":
            raise ValueError(f"Payee VPA {payee_vpa} could not be validated")
        # Parse key attributes from RespValAdd (e.g., IFSC) to drive bank selection
        ns = {"upi": "http://npci.org/upi/schema/"}
        root = ET.fromstring(val_response)
        resp = root.find("upi:Resp", ns) or root.find("Resp")
        info = {"IFSC": None, "accType": None, "maskName": None, "result": result}
        if resp is not None:
            info["IFSC"] = resp.attrib.get("IFSC")
            info["accType"] = resp.attrib.get("accType")
            info["maskName"] = resp.attrib.get("maskName")
        return info

    def _is_p2p(self, payer_vpa: str, payee_vpa: str) -> bool:
        """
        Determine if a transaction is person‑to‑person based on VPA domains.
        Returns True when the domains differ.
        """
        try:
            payer_domain = payer_vpa.split("@")[1].lower()
            payee_domain = payee_vpa.split("@")[1].lower()
            return payer_domain != payee_domain
        except Exception:
            return False

    def handle_reqpay(self, xml_req: str):
        """Generic ReqPay handler, currently routes to push logic."""
        return self.handle_push(xml_req)

    def handle_push(self, xml_req: str):
        # Validate against new NPCI ReqPay schema
        self.validate_xml(xml_req, "upi_pay_request.xsd")
        print("\n[XML] -> ReqPay/PUSH (API → Switch):\n", xml_req, "\n")
        # Note: API layer already broadcasts this, so we skip broadcasting here to avoid duplicate

        ns = {"upi": "http://npci.org/upi/schema/"}
        root = ET.fromstring(xml_req)

        # Extract payer/payee/amount/note
        payer_elem = root.find("upi:Payer", ns)

        # Support both nested Payees/Payee and flat Payee
        payee_elem = root.find("upi:Payees/upi:Payee", ns)
        if payee_elem is None:
            payee_elem = root.find("upi:Payee", ns)

        txn_elem = root.find("upi:Txn", ns)

        if payer_elem is None or payee_elem is None or txn_elem is None:
            raise ValueError("Missing required XML elements (Payer, Payee, or Txn)")

        payer_vpa = payer_elem.attrib.get("addr")
        payee_vpa = payee_elem.attrib.get("addr")

        # Support Amount inside Payer (old) or at Root (new)
        amount_elem = payer_elem.find("upi:Amount", ns)
        if amount_elem is None:
            amount_elem = root.find("upi:Amount", ns)

        if amount_elem is None:
            raise ValueError("Missing Amount element")

        # Handle 'value' (old) vs 'val' (new XSD) attribute
        amount_str = amount_elem.attrib.get("value") or amount_elem.attrib.get("val")
        if not amount_str:
            raise ValueError("Missing Amount value/val attribute")

        amount = float(amount_str)
        note = txn_elem.attrib.get("note", "")

        # Extract PIN/CredBlock (dummy) for authorization
        pin = None
        try:
            creds_data = payer_elem.find("upi:Creds/upi:Cred/upi:Data", ns)
            if creds_data is not None:
                pin = creds_data.attrib.get("code")
        except Exception:
            pin = None

        # Extract Purpose and PurposeCode
        purpose = root.findtext(".//upi:purpose", "", ns) or root.findtext("purpose", "")
        purpose_code_dict = {}
        pc_elem = root.find(".//upi:purposeCode", ns) or root.find("purposeCode")
        if pc_elem is not None:
            purpose_code_dict["code"] = pc_elem.attrib.get("code")
            purpose_code_dict["description"] = pc_elem.attrib.get("description")

        # Extract optional HighValue element (new field)
        high_value = None
        hv_elem = root.find(".//upi:HighValue", ns) or root.find("HighValue")
        if hv_elem is not None and hv_elem.text:
            high_value = hv_elem.text.strip()

        # Extract Block ID if present (for block-based payments)
        block_id = None
        block_elem = root.find(".//upi:BlockId", ns) or root.find("BlockId")
        if block_elem is not None and block_elem.text:
            block_id = block_elem.text.strip()

        txn_type = (txn_elem.attrib.get("type") or "PAY").upper()

        # Log parsed details
        print(f"[UPI Switch] {txn_type} from {payer_vpa} → {payee_vpa} : ₹{amount:.2f}")

        # Log warning if amount exceeds previous 5‑lakh limit (but still allowed)
        if amount > PREV_MAX_TXN_AMOUNT:
            print(f"[UPI Switch] ⚠️ Transaction amount {amount} exceeds previous limit {PREV_MAX_TXN_AMOUNT}")

        # Enforce overall transaction ceiling (3 lakh) – aligns with updated XSD maxInclusive
        if amount > MAX_TXN_AMOUNT:
            print(f"[UPI Switch] ⚠️ Transaction amount {amount} exceeds maximum allowed {MAX_TXN_AMOUNT}")
            rrn = gen_rrn()
            self._finalize(rrn, "DECLINED_AMOUNT_LIMIT", None, None,
                           payer_vpa, payee_vpa, amount, note, txn_type,
                           purpose_code=purpose_code_dict)
            return {"rrn": rrn, "status": "DECLINED_AMOUNT_LIMIT"}

        # Enforce P2P limit early for person‑to‑person transfers
        if self._is_p2p(payer_vpa, payee_vpa) and amount > P2P_LIMIT:
            rrn = gen_rrn()
            self._finalize(rrn, "DECLINED_AMOUNT_LIMIT", None, None,
                           payer_vpa, payee_vpa, amount, note, txn_type,
                           purpose_code=purpose_code_dict)
            return {"rrn": rrn, "status": "DECLINED_AMOUNT_LIMIT"}

        # Fraud detection check
        is_p2p = self._is_p2p(payer_vpa, payee_vpa)
        risk_data = {
            "amount": amount,
            "payer_vpa": payer_vpa,
            "payee_vpa": payee_vpa,
            "is_p2p": is_p2p,
            "note": note,
            "txn_type": txn_type
        }
        risk_score, risk_level = self.fraud_detection.calculate_risk_score(risk_data)
        print(f"[UPI Switch] Risk Score: {risk_score} ({risk_level})")
        
        if risk_level == "HIGH":
            rrn = gen_rrn()
            self._finalize(rrn, "DECLINED_RISK", None, None,
                           payer_vpa, payee_vpa, amount, note, txn_type,
                           purpose_code=purpose_code_dict)
            return {"rrn": rrn, "status": "DECLINED_RISK"}

        # ValAdd is no longer invoked in pay flow; assume UI validated earlier
        return self.async_route(self._route_push, payer_vpa, payee_vpa, amount,
                               note, txn_type, None, pin, purpose, purpose_code_dict, 
                               high_value, block_id)

    def request_live_agent_auth(self, rrn: str, bank_code: str, payer_vpa: str, amount: float, note: str) -> bool:
        """
        Publishes a live auth request and waits for an Agent to respond.
        Real-time Agent-to-Agent Coordination.
        """
        print(f"[UPI Switch] 🤖 Requesting LIVE AGENT AUTHORIZATION from {bank_code} for {rrn}...")
        
        # Notify bus that we are starting A2A
        self.bus.publish_event("agent_status", {
            "agent": "UPISwitch",
            "status": f"Waiting for {bank_code} Agent to authorize ₹{amount}...",
            "state": "thinking"
        })

        event = {
            "type": "UPI_LIVE_AUTH_REQ",
            "rrn": rrn,
            "bank_code": bank_code,
            "payer_vpa": payer_vpa,
            "amount": amount,
            "note": note,
            "ts": now_ts()
        }
        self.bus.publish_event("agent_auth", event)

        # Wait for response (non-blocking in real world, but synchronous here for demo flow)
        timeout = 10.0
        start = time.time()
        while time.time() - start < timeout:
            # Poll the response topic
            # In memory backend is tricky, we'll poll the list
            if self.bus.backend == "memory":
                queue = self.bus.memory_queue.get("agent_auth_resp", [])
                for resp in reversed(queue):
                    if resp.get("rrn") == rrn:
                        status = resp.get("status")
                        decision = resp.get("decision", "No explanation provided.")
                        print(f"[UPI Switch] 🤖 AGENT RESPONSE RECEIVED: {status} ({decision})")
                        self.bus.publish_event("agent_status", {
                            "agent": "UPISwitch",
                            "status": f"Agent {bank_code} {status}: {decision[:50]}...",
                            "state": "idle"
                        })
                        return status == "APPROVED"
            
            time.sleep(0.5)
        
        print(f"[UPI Switch] ⚠️ Agent auth TIMEOUT for {rrn}. Falling back to default rules.")
        return True # Default to pass if agent is slow (High Availability)

    def _route_push(self, rrn: str, payer_vpa: str, payee_vpa: str, amount: float,
                    note: str, txn_type: str = "PAY", valadd_info: Optional[dict] = None,
                    pin: Optional[str] = None, purpose: str = None,
                    purpose_code: dict = None, high_value: Optional[str] = None,
                    block_id: Optional[str] = None):
        
        # Resolve banks
        try:
            payer_bank = self.payer_registry.resolve(payer_vpa)
            payee_bank = self.payee_registry.resolve(payee_vpa)
        except ValueError as e:
             self._finalize(rrn, "DECLINED", str(e), None, payer_vpa, payee_vpa, amount, note, txn_type)
             return {"rrn": rrn, "status": "DECLINED_VPA_NOT_FOUND"}

        # --- LIVE AGENT TO AGENT (A2A) AUTHORIZATION ---
        # Trigger for all ICICI bank transactions or high values
        if "icici" in payer_vpa.lower() or amount > 50000:
             authorized = self.request_live_agent_auth(rrn, payer_bank.code, payer_vpa, amount, note)
             if not authorized:
                 self._finalize(rrn, "DECLINED_AGENT_DENIED", "Transaction denied by Autonomous Bank Agent", None, 
                               payer_vpa, payee_vpa, amount, note, txn_type)
                 return {"rrn": rrn, "status": "DECLINED_AGENT_DENIED"}

        self.bus.publish_event("txn_events", {"rrn": rrn, "event": "PUSH_START",
                                              "ts": now_ts(),
                                              "payer_vpa": payer_vpa,
                                              "payee_vpa": payee_vpa,
                                              "amount": amount})
        payer_bank, payer_acc = self._resolve_payer(payer_vpa)
        payee_bank, payee_acc = self._resolve_payee_from_valadd(payee_vpa, valadd_info)

        # If block_id provided, validate and utilize block
        if block_id:
            block = self.block_registry.get_block(block_id)
            if not block:
                return self._finalize(rrn, "DECLINED_INVALID_BLOCK", None, None,
                                      payer_vpa, payee_vpa, amount, note,
                                      txn_type, purpose_code=purpose_code)
            if block["payer_vpa"] != payer_vpa:
                return self._finalize(rrn, "DECLINED_BLOCK_MISMATCH", None, None,
                                      payer_vpa, payee_vpa, amount, note,
                                      txn_type, purpose_code=purpose_code)
            if not self.block_registry.utilize_block(block_id, amount):
                return self._finalize(rrn, "DECLINED_BLOCK_INSUFFICIENT", None, None,
                                      payer_vpa, payee_vpa, amount, note,
                                      txn_type, purpose_code=purpose_code)
            
            # Trigger merchant webhook for debit
            if block.get("merchant_id"):
                self.merchant_webhooks.trigger_debit_event(
                    block["merchant_id"],
                    {
                        "block_id": block_id,
                        "rrn": rrn,
                        "amount": amount,
                        "payer_vpa": payer_vpa,
                        "payee_vpa": payee_vpa
                    }
                )

        # 2️⃣ Switch → PayeePSP: ReqAuthDetails; PayeePSP → Switch: RespAuthDetails
        if self.payee_auth_details_handler is not None:
            ns = "http://npci.org/upi/schema/"
            ET.register_namespace("upi", ns)
            req_auth = ET.Element(f"{{{ns}}}ReqAuthDetails")
            head = ET.SubElement(req_auth, f"{{{ns}}}Head")
            head.set("ver", "2.0")
            head.set("ts", now_ts())
            head.set("orgId", "NPCI")
            head.set("msgId", "AUTH_" + rrn[-8:])
            txn = ET.SubElement(req_auth, f"{{{ns}}}Txn")
            txn.set("id", rrn)
            txn.set("type", "PAY")
            txn.set("note", note or "")
            payees = ET.SubElement(req_auth, f"{{{ns}}}Payees")
            payee = ET.SubElement(payees, f"{{{ns}}}Payee")
            payee.set("addr", payee_vpa)
            ET.SubElement(payee, f"{{{ns}}}Amount", value=f"{amount:.2f}", curr="INR")
            payer = ET.SubElement(req_auth, f"{{{ns}}}Payer")
            payer.set("addr", payer_vpa)
            ET.SubElement(payer, f"{{{ns}}}Amount", value=f"{amount:.2f}", curr="INR")
            req_auth_xml = ET.tostring(req_auth, encoding="utf-8",
                                      xml_declaration=True).decode("utf-8")

            print("\n[XML] -> ReqAuthDetails (Switch → PayeePSP):\n", req_auth_xml, "\n")
            self.bus.publish_event("xml_stream", {"source": "[Switch] -> ReqAuthDetails",
                                                 "content": req_auth_xml})

            try:
                resp_auth_xml = self.payee_auth_details_handler(req_auth_xml)
                print("\n[XML] <- RespAuthDetails (PayeePSP → Switch):\n", resp_auth_xml, "\n")
                self.bus.publish_event("xml_stream", {"source": "[Switch] <- RespAuthDetails",
                                                     "content": resp_auth_xml})
            except Exception as e:
                print(f"[UPI Switch] ⚠️ AuthDetails failed: {e}")

        # Enforce dummy PIN authorization (CredBlock)
        try:
            if not pin or not payer_bank.auth_service.authorize(payer_vpa, pin):
                status = "DECLINED_AUTH"
                return self._finalize(rrn, status, None, None,
                                      payer_vpa, payee_vpa, amount, note,
                                      txn_type, purpose_code=purpose_code)
        except Exception:
            status = "DECLINED_AUTH"
            return self._finalize(rrn, status, None, None,
                                  payer_vpa, payee_vpa, amount, note,
                                  txn_type, purpose_code=purpose_code)

        # Basic amount validation (mirrors earlier checks)
        if amount <= 0:
            status = "DECLINED_INVALID_AMOUNT"
        elif amount > MAX_TXN_AMOUNT:
            print(f"[UPI Switch] ⚠️ Transaction amount {amount} exceeds maximum allowed {MAX_TXN_AMOUNT}")
            status = "DECLINED_AMOUNT_LIMIT"
        elif amount > PREV_MAX_TXN_AMOUNT:
            print(f"[UPI Switch] ⚠️ Transaction amount {amount} exceeds previous limit {PREV_MAX_TXN_AMOUNT}")
            if self._is_p2p(payer_vpa, payee_vpa) and amount > P2P_LIMIT:
                status = "DECLINED_AMOUNT_LIMIT"
            elif not self._is_p2p(payer_vpa, payee_vpa) and amount > P2P_LIMIT:
                status = "SUCCESS"
            elif not payee_bank.prevalidate_credit(amount):
                status = "DECLINED_PAYEE_PREVALIDATION"
            else:
                status = None
        elif self._is_p2p(payer_vpa, payee_vpa) and amount > P2P_LIMIT:
            status = "DECLINED_AMOUNT_LIMIT"
        elif not self._is_p2p(payer_vpa, payee_vpa) and amount > P2P_LIMIT:
            status = "SUCCESS"
        elif not payee_bank.prevalidate_credit(amount):
            status = "DECLINED_PAYEE_PREVALIDATION"
        else:
            # 3️⃣ Switch → RemitterBank: ReqPay (DEBIT) and receive RespPay(DEBIT)
            try:
                ns = "http://npci.org/upi/schema/"
                req_debit = ET.Element("ns2:ReqPay",
                                       {"xmlns:ns2": ns,
                                        "xmlns:ns3": "http://npci.org/cm/schema/"})
                head = ET.SubElement(req_debit, "Head",
                                     ver="2.0", ts=now_ts(),
                                     orgId="NPCI",
                                     msgId=f"DEBIT{rrn[-6:]}")
                meta = ET.SubElement(req_debit, "Meta")
                ET.SubElement(meta, "Tag", name="PAYREQSTART", value=now_ts())
                ET.SubElement(meta, "Tag", name="PAYREQEND", value=now_ts())
                txn = ET.SubElement(req_debit, "Txn",
                                   id=rrn, note=note or "", refId=rrn,
                                   refUrl="", ts=now_ts(),
                                   type="DEBIT", custRef=payer_vpa,
                                   initiationMode="00", subType="PAY")
                if purpose:
                    ET.SubElement(req_debit, f"{{{ns}}}purpose").text = purpose
                if purpose_code and purpose_code.get("code"):
                    pc = ET.SubElement(req_debit, "purposeCode")
                    pc.set("code", purpose_code.get("code"))
                    if purpose_code.get("description"):
                        pc.set("description", purpose_code.get("description"))
                # RiskScores
                risk = ET.SubElement(req_debit, "RiskScores")
                ET.SubElement(risk, "Score", provider=payer_bank.code,
                              type="TXNRISK", value="00000")
                # HighValue (optional)
                if high_value:
                    hv_elem = ET.SubElement(req_debit, "HighValue")
                    hv_elem.text = high_value
                # BlockId (if using block)
                if block_id:
                    blk_elem = ET.SubElement(req_debit, "BlockId")
                    blk_elem.text = block_id
                payer = ET.SubElement(req_debit, "Payer",
                                      addr=payer_vpa, name="", seqNum="1",
                                      type="PERSON", code="0000")
                ac = ET.SubElement(payer, "Ac", addrType="ACCOUNT")
                ET.SubElement(ac, "Detail", name="IFSC",
                              value=f"{payer_bank.code}001")
                ET.SubElement(ac, "Detail", name="ACTYPE", value="SAVING")
                ET.SubElement(ac, "Detail", name="ACNUM", value=payer_acc)
                ET.SubElement(payer, "Amount", value=f"{amount:.2f}", curr="INR")
                payees = ET.SubElement(req_debit, "Payees")
                payee = ET.SubElement(payees, "Payee",
                                      addr=payee_vpa, name="", seqNum="1",
                                      type="ENTITY", code="")
                pac = ET.SubElement(payee, "Ac", addrType="ACCOUNT")
                ET.SubElement(pac, "Detail", name="IFSC",
                              value=f"{payee_bank.code}001")
                ET.SubElement(pac, "Detail", name="ACTYPE", value="CURRENT")
                ET.SubElement(pac, "Detail", name="ACNUM", value=payee_acc)
                ET.SubElement(payee, "Amount", value=f"{amount:.2f}", curr="INR")
                req_debit_xml = ET.tostring(req_debit, encoding="utf-8",
                                            xml_declaration=True).decode("utf-8")
                print("\n[XML] -> ReqPay (DEBIT) Switch → RemitterBank:\n",
                      req_debit_xml, "\n")
                self.bus.publish_event("xml_stream", {"source": "[Switch] -> ReqPay (DEBIT)",
                                                     "content": req_debit_xml})
            except Exception as e:
                print(f"[UPI Switch] ⚠️ Failed to build ReqPay(DEBIT) XML: {e}")

            # Attempt debit with failure handling
            try:
                utr_debit = payer_bank.debit(payer_acc, amount)
            except Exception as e:
                msg = str(e).lower()
                if "insufficient" in msg or "fund" in msg:
                    status = "DECLINED_INSUFFICIENT_FUNDS"
                else:
                    status = "FAILURE_DEBIT_POSTING"
                utr_debit = None
                utr_credit = None
                return self._finalize(rrn, status, utr_debit, utr_credit,
                                      payer_vpa, payee_vpa, amount, note,
                                      txn_type, purpose_code=purpose_code)

            # Print simulated RespPay(DEBIT) XML
            try:
                ns = "http://npci.org/upi/schema/"
                resp_debit = ET.Element("ns2:RespPay",
                                        {"xmlns:ns2": ns,
                                         "xmlns:ns3": "http://npci.org/cm/schema/"})
                ET.SubElement(resp_debit, "Head", ver="2.0", ts=now_ts(),
                              orgId=payer_bank.code,
                              msgId=f"DEBITR{rrn[-6:]}")
                rtxn = ET.SubElement(resp_debit, "Txn",
                                     id=rrn, type="DEBIT", subType="PAY",
                                     ts=now_ts(), note=note or "",
                                     refId=rrn, refUrl="",
                                     initiationMode="00", purpose="AA",
                                     custRef=payer_vpa)
                rrs = ET.SubElement(rtxn, "RiskScores")
                ET.SubElement(rrs, "Score", provider=payer_bank.code,
                              type="TXNRISK", value="00000")
                resp = ET.SubElement(resp_debit, "Resp",
                                     reqMsgId=f"DEBIT{rrn[-6:]}", result="SUCCESS")
                ET.SubElement(resp, "Ref",
                              IFSC=f"{payer_bank.code}001",
                              acNum=payer_acc,
                              accType="SAVING",
                              addr=payer_vpa,
                              approvalNum=utr_debit or "",
                              code="0000", regName="",
                              respCode="00", seqNum="1",
                              settAmount=f"{amount:.2f}",
                              settCurrency="INR", type="PAYER")
                resp_debit_xml = ET.tostring(resp_debit, encoding="utf-8",
                                             xml_declaration=True).decode("utf-8")
                print("\n[XML] <- RespPay (DEBIT) RemitterBank → Switch:\n",
                      resp_debit_xml, "\n")
                self.bus.publish_event("xml_stream", {"source": "[Switch] <- RespPay (DEBIT)",
                                                     "content": resp_debit_xml})
            except Exception as e:
                print(f"[UPI Switch] ⚠️ Failed to build RespPay(DEBIT) XML: {e}")

            # 4️⃣ Switch → BeneficiaryBank: ReqPay (CREDIT) and receive RespPay(CREDIT)
            try:
                ns = "http://npci.org/upi/schema/"
                req_credit = ET.Element("ns2:ReqPay",
                                        {"xmlns:ns2": ns,
                                         "xmlns:ns3": "http://npci.org/cm/schema/"})
                ET.SubElement(req_credit, "Head", ver="2.0", ts=now_ts(),
                              orgId="NPCI",
                              msgId=f"CREDIT{rrn[-6:]}")
                meta = ET.SubElement(req_credit, "Meta")
                ET.SubElement(meta, "Tag", name="PAYREQSTART", value=now_ts())
                ET.SubElement(meta, "Tag", name="PAYREQEND", value=now_ts())
                txn = ET.SubElement(req_credit, "Txn",
                                   id=rrn, note=note or "", refId=rrn,
                                   refUrl="", ts=now_ts(),
                                   type="CREDIT", custRef=payer_vpa,
                                   initiationMode="00", subType="PAY")
                if purpose:
                    ET.SubElement(req_credit, f"{{{ns}}}purpose").text = purpose
                if purpose_code and purpose_code.get("code"):
                    pc = ET.SubElement(req_credit, "purposeCode")
                    pc.set("code", purpose_code.get("code"))
                    if purpose_code.get("description"):
                        pc.set("description", purpose_code.get("description"))
                # RiskScores
                risk = ET.SubElement(req_credit, "RiskScores")
                ET.SubElement(risk, "Score", provider=payee_bank.code,
                              type="TXNRISK", value="00000")
                # HighValue (optional)
                if high_value:
                    hv_elem = ET.SubElement(req_credit, "HighValue")
                    hv_elem.text = high_value
                # BlockId (if using block)
                if block_id:
                    blk_elem = ET.SubElement(req_credit, "BlockId")
                    blk_elem.text = block_id
                payer = ET.SubElement(req_credit, "Payer",
                                      addr=payer_vpa, name="", seqNum="1",
                                      type="PERSON", code="0000")
                ac = ET.SubElement(payer, "Ac", addrType="ACCOUNT")
                ET.SubElement(ac, "Detail", name="IFSC",
                              value=f"{payer_bank.code}001")
                ET.SubElement(ac, "Detail", name="ACTYPE", value="SAVING")
                ET.SubElement(ac, "Detail", name="ACNUM", value=payer_acc)
                ET.SubElement(payer, "Amount", value=f"{amount:.2f}", curr="INR")
                payees = ET.SubElement(req_credit, "Payees")
                payee = ET.SubElement(payees, "Payee",
                                      addr=payee_vpa, name="", seqNum="1",
                                      type="ENTITY", code="")
                pac = ET.SubElement(payee, "Ac", addrType="ACCOUNT")
                ET.SubElement(pac, "Detail", name="IFSC",
                              value=f"{payee_bank.code}001")
                ET.SubElement(pac, "Detail", name="ACTYPE", value="CURRENT")
                ET.SubElement(pac, "Detail", name="ACNUM", value=payee_acc)
                ET.SubElement(payee, "Amount", value=f"{amount:.2f}", curr="INR")
                req_credit_xml = ET.tostring(req_credit, encoding="utf-8",
                                            xml_declaration=True).decode("utf-8")
                print("\n[XML] -> ReqPay (CREDIT) Switch → BeneficiaryBank:\n",
                      req_credit_xml, "\n")
                self.bus.publish_event("xml_stream", {"source": "[Switch] -> ReqPay (CREDIT)",
                                                     "content": req_credit_xml})
            except Exception as e:
                print(f"[UPI Switch] ⚠️ Failed to build ReqPay(CREDIT) XML: {e}")

            # Attempt credit with failure handling
            try:
                utr_credit = payee_bank.credit(payee_acc, amount)
            except Exception:
                status = "FAILURE_CREDIT_POSTING"
                utr_credit = None
                return self._finalize(rrn, status, utr_debit, utr_credit,
                                      payer_vpa, payee_vpa, amount, note,
                                      txn_type, purpose_code=purpose_code)

            # Print simulated RespPay(CREDIT) XML
            try:
                ns = "http://npci.org/upi/schema/"
                resp_credit = ET.Element("ns2:RespPay",
                                         {"xmlns:ns2": ns,
                                          "xmlns:ns3": "http://npci.org/cm/schema/"})
                ET.SubElement(resp_credit, "Head", ver="2.0", ts=now_ts(),
                              orgId=payee_bank.code,
                              msgId=f"CREDITR{rrn[-6:]}")
                rtxn = ET.SubElement(resp_credit, "Txn",
                                     id=rrn, type="CREDIT", subType="PAY",
                                     ts=now_ts(), note=note or "",
                                     refId=rrn, refUrl="",
                                     initiationMode="00", purpose="AA",
                                     custRef=payer_vpa)
                rrs = ET.SubElement(rtxn, "RiskScores")
                ET.SubElement(rrs, "Score", provider=payee_bank.code,
                              type="TXNRISK", value="00000")
                resp = ET.SubElement(resp_credit, "Resp",
                                     reqMsgId=f"CREDIT{rrn[-6:]}", result="SUCCESS")
                ET.SubElement(resp, "Ref",
                              IFSC=f"{payee_bank.code}001",
                              acNum=payee_acc,
                              accType="CURRENT",
                              addr=payee_vpa,
                              approvalNum=utr_credit or "",
                              code="0000", regName="",
                              respCode="00", seqNum="1",
                              settAmount=f"{amount:.2f}",
                              settCurrency="INR", type="PAYEE")
                resp_credit_xml = ET.tostring(resp_credit, encoding="utf-8",
                                              xml_declaration=True).decode("utf-8")
                print("\n[XML] <- RespPay (CREDIT) BeneficiaryBank → Switch:\n",
                      resp_credit_xml, "\n")
                self.bus.publish_event("xml_stream", {"source": "[Switch] <- RespPay (CREDIT)",
                                                     "content": resp_credit_xml})
            except Exception as e:
                print(f"[UPI Switch] ⚠️ Failed to build RespPay(CREDIT) XML: {e}")

            status = "SUCCESS"

        xml_resp = self._finalize(rrn, status, utr_debit, utr_credit,
                                 payer_vpa, payee_vpa, amount, note,
                                 txn_type, purpose_code=purpose_code)

        # Send notifications on success
        if status == "SUCCESS":
            self.notification_engine.notify_transaction_success(
                payer_vpa=payer_vpa,
                payee_vpa=payee_vpa,
                amount=amount,
                rrn=rrn
            )

        # 5️⃣ TxnConfirmation to PayeePSP after success
        if status == "SUCCESS" and self.payee_txn_conf_handler is not None:
            ns = "http://npci.org/upi/schema/"
            ET.register_namespace("upi", ns)
            req_conf = ET.Element(f"{{{ns}}}ReqTxnConfirmation")
            head = ET.SubElement(req_conf, f"{{{ns}}}Head")
            head.set("ver", "2.0")
            head.set("ts", now_ts())
            head.set("orgId", "NPCI")
            head.set("msgId", "CONF_" + rrn[-8:])
            txn = ET.SubElement(req_conf, f"{{{ns}}}Txn")
            txn.set("id", rrn)
            txn.set("type", "TxnConfirmation")
            txn.set("orgTxnId", rrn)
            txn.set("note", note or "")
            conf = ET.SubElement(req_conf, f"{{{ns}}}TxnConfirmation")
            conf.set("type", "PAY")
            conf.set("orgStatus", "SUCCESS")
            ET.SubElement(req_conf, f"{{{ns}}}TxnConfirmation",
                          type="PAY", orgStatus="SUCCESS")
            ET.SubElement(req_conf, f"{{{ns}}}Ref",
                          type="PAYEE", seqNum="1", addr=payee_vpa,
                          settAmount=f"{amount:.2f}", settCurrency="INR",
                          approvalNum=(utr_credit or ""), respCode="00",
                          regName="", orgAmount=f"{amount:.2f}",
                          acNum="", IFSC="", code="", accType="")
            req_conf_xml = ET.tostring(req_conf, encoding="utf-8",
                                      xml_declaration=True).decode("utf-8")

            print("\n[XML] -> ReqTxnConfirmation (Switch → PayeePSP):\n",
                  req_conf_xml, "\n")
            self.bus.publish_event("xml_stream", {"source": "[Switch] -> ReqTxnConfirmation",
                                                 "content": req_conf_xml})

            try:
                resp_conf_xml = self.payee_txn_conf_handler(req_conf_xml)
                print("\n[XML] <- RespTxnConfirmation (PayeePSP → Switch):\n",
                      resp_conf_xml, "\n")
                self.bus.publish_event("xml_stream", {"source": "[Switch] <- RespTxnConfirmation",
                                                     "content": resp_conf_xml})
            except Exception as e:
                print(f"[UPI Switch] ⚠️ TxnConfirmation failed: {e}")

        return xml_resp

    def handle_collect(self, xml_req: str, get_payer_approval_callable):
        self.validate_xml(xml_req, "upi_collect_request.xsd")
        print("\n[XML] -> CollectRequest (API → Switch):\n", xml_req, "\n")
        root = ET.fromstring(xml_req)
        payee_vpa = root.find("PayeeVPA").text
        payer_vpa = root.find("PayerVPA").text
        amount = float(root.find("Amount").text)
        note = root.find("Note").text
        purpose_code = root.findtext("PurposeCode")
        return self.async_route(self._route_collect, payer_vpa, payee_vpa,
                               amount, note, get_payer_approval_callable,
                               "COLLECT", None, purpose_code)

    def _route_collect(self, rrn: str, payer_vpa: str, payee_vpa: str,
                      amount: float, note: str,
                      get_payer_approval_callable, txn_type: str = "COLLECT",
                      valadd_info: Optional[dict] = None,
                      purpose: str = None):
        self.bus.publish_event("txn_events", {"rrn": rrn,
                                              "event": "COLLECT_START",
                                              "ts": now_ts(),
                                              "payer_vpa": payer_vpa,
                                              "payee_vpa": payee_vpa,
                                              "amount": amount})
        payee_bank, payee_acc = self._resolve_payee_from_valadd(payee_vpa,
                                                              valadd_info)
        payer_bank, payer_acc = self._resolve_payer(payer_vpa)

        if amount <= 0:
            status = "DECLINED_INVALID_AMOUNT"
            return self._finalize(rrn, status, None, None,
                                 payer_vpa, payee_vpa, amount, note,
                                 txn_type)
        if amount > P2P_LIMIT and self._is_p2p(payer_vpa, payee_vpa):
            status = "DECLINED_AMOUNT_LIMIT"
            return self._finalize(rrn, status, None, None,
                                 payer_vpa, payee_vpa, amount, note,
                                 txn_type)

        approved = get_payer_approval_callable(rrn, amount, note)
        if not approved:
            status = "DECLINED_BY_PAYER"
            return self._finalize(rrn, status, None, None,
                                 payer_vpa, payee_vpa, amount, note,
                                 txn_type)

        if not payee_bank.prevalidate_credit(amount):
            status = "DECLINED_PAYEE_PREvalidation"
            return self._finalize(rrn, status, None, None,
                                 payer_vpa, payee_vpa, amount, note,
                                 txn_type)

        try:
            utr_debit = payer_bank.debit(payer_acc, amount)
        except Exception as e:
            msg = str(e).lower()
            status = ("DECLINED_INSUFFICIENT_FUNDS"
                      if ("insufficient" in msg or "fund" in msg)
                      else "FAILURE_DEBIT_POSTING")
            return self._finalize(rrn, status, None, None,
                                 payer_vpa, payee_vpa, amount, note,
                                 txn_type)

        try:
            utr_credit = payee_bank.credit(payee_acc, amount)
        except Exception:
            status = "FAILURE_CREDIT_POSTING"
            return self._finalize(rrn, status, utr_debit, None,
                                 payer_vpa, payee_vpa, amount, note,
                                 txn_type)
        status = "SUCCESS"
        
        # Send notification on success
        if status == "SUCCESS":
            self.notification_engine.notify_transaction_success(
                payer_vpa=payer_vpa,
                payee_vpa=payee_vpa,
                amount=amount,
                rrn=rrn
            )
        
        return self._finalize(rrn, status, utr_debit, utr_credit,
                             payer_vpa, payee_vpa, amount, note,
                             txn_type)

    # ========== Block Creation API (per TSD Section 2) ==========
    
    def handle_create_block(self, xml_req: str) -> dict:
        """
        Handle block creation request (Core Transaction API per TSD Section 2).
        Validates DSC and creates a payment block/reserve.
        """
        self.validate_xml(xml_req, "upi_block_request.xsd")
        print("\n[XML] -> BlockCreateRequest (API → Switch):\n", xml_req, "\n")
        
        root = ET.fromstring(xml_req)
        ns = {"upi": "http://npci.org/upi/schema/"}
        
        # Extract block creation parameters
        payer_elem = root.find("upi:Payer", ns) or root.find("Payer")
        payee_elem = root.find("upi:Payee", ns) or root.find("Payee")
        amount_elem = root.find("upi:Amount", ns) or root.find("Amount")
        
        if not all([payer_elem, payee_elem, amount_elem]):
            raise ValueError("Missing required elements for block creation")
        
        payer_vpa = payer_elem.attrib.get("addr")
        payee_vpa = payee_elem.attrib.get("addr")
        
        amount_str = amount_elem.attrib.get("value") or amount_elem.attrib.get("val")
        amount = float(amount_str)
        
        # Extract optional elements
        purpose = root.findtext(".//upi:purpose", "", ns) or root.findtext("purpose", "")
        merchant_id = root.findtext(".//upi:merchantId", "", ns) or root.findtext("merchantId", "")
        
        # Extract DSC signature and certificate for validation
        dsc_elem = root.find(".//upi:DSC", ns) or root.find("DSC")
        signature = ""
        certificate = ""
        if dsc_elem is not None:
            signature = dsc_elem.attrib.get("signature", "")
            certificate = dsc_elem.attrib.get("certificate", "")
        
        # Validate DSC
        is_valid, error_msg = self.dsc_validation.validate_dsc(
            xml_req, signature, certificate
        )
        if not is_valid:
            return {"status": "DECLINED_DSC_INVALID", "error": error_msg}
        
        # Generate block ID and expiry
        block_id = gen_block_id()
        expiry_ts = (datetime.utcnow() + timedelta(days=BLOCK_EXPIRY_DAYS)).isoformat(timespec="seconds") + "Z"
        
        # Create block
        block = self.block_registry.create_block(
            block_id=block_id,
            payer_vpa=payer_vpa,
            payee_vpa=payee_vpa,
            amount=amount,
            expiry_ts=expiry_ts,
            purpose=purpose,
            merchant_id=merchant_id if merchant_id else None,
            status="ACTIVE"
        )
        
        # Send notification
        self.notification_engine.notify_block_created(
            payer_vpa=payer_vpa,
            block_id=block_id,
            amount=amount,
            expiry_ts=expiry_ts
        )
        
        print(f"[UPI Switch] Block created: {block_id} for ₹{amount:.2f}")
        
        return {
            "status": "SUCCESS",
            "block_id": block_id,
            "expiry_ts": expiry_ts,
            "amount": amount
        }
    
    def handle_revoke_block(self, xml_req: str) -> dict:
        """
        Handle block revocation request (Core Transaction API per TSD Section 2).
        """
        self.validate_xml(xml_req, "upi_block_revoke_request.xsd")
        print("\n[XML] -> BlockRevokeRequest (API → Switch):\n", xml_req, "\n")
        
        root = ET.fromstring(xml_req)
        
        block_id_elem = root.find("BlockId") or root.find(".//upi:BlockId")
        if block_id_elem is None or not block_id_elem.text:
            raise ValueError("Missing BlockId")
        
        block_id = block_id_elem.text.strip()
        reason_elem = root.find("Reason") or root.find(".//upi:Reason")
        reason = reason_elem.text if reason_elem is not None and reason_elem.text else "User requested"
        
        # Revoke block
        success = self.block_registry.revoke_block(block_id, reason)
        
        if not success:
            return {"status": "DECLINED", "error": "Block not found or already revoked"}
        
        block = self.block_registry.get_block(block_id)
        
        # Trigger merchant webhook for revocation
        if block and block.get("merchant_id"):
            self.merchant_webhooks.trigger_revocation_event(
                block["merchant_id"],
                {
                    "block_id": block_id,
                    "reason": reason,
                    "amount": block["amount"] if block else 0
                }
            )
        
        # Send notification
        if block:
            self.notification_engine.notify_block_revoked(
                payer_vpa=block["payer_vpa"],
                block_id=block_id,
                amount=block["amount"],
                reason=reason
            )
        
        print(f"[UPI Switch] Block revoked: {block_id}")
        
        return {
            "status": "SUCCESS",
            "block_id": block_id,
            "revoked_at": now_ts()
        }
    
    def handle_get_active_reserves(self, payer_vpa: str = None) -> List[dict]:
        """
        Get active reserves (blocks) for UI components.
        """
        return self.block_registry.get_active_reserves(payer_vpa)

    def _resolve_payee(self, payee_vpa: str):
        if self.payee_resolver is None:
            raise ValueError("Payee PSP resolver is not registered on the switch")
        return self.payee_resolver(payee_vpa)

    def _resolve_payer(self, payer_vpa: str):
        bank = self.payer_registry.resolve(payer_vpa)
        account = bank.get_account_by_vpa(payer_vpa)
        return bank, account.id

    def _resolve_payee_from_valadd(self, payee_vpa: str,
                                   valadd_info: Optional[dict]):
        # Prefer IFSC-based bank resolution from ValAdd response when available
        if valadd_info and valadd_info.get("IFSC") and self.resolve_bank_by_ifsc is not None:
            bank = self.resolve_bank_by_ifsc(valadd_info["IFSC"])
            if bank is None:
                # Fallback to PSP resolver
                return self._resolve_payee(payee_vpa)
            account = bank.get_account_by_vpa(payee_vpa)
            return bank, account.id
        # Fallback to PSP resolver by VPA
        return self._resolve_payee(payee_vpa)

    def status_poll(self, xml_req: str):
        """
        Poll API to fetch final transaction status by RRN.
        Validates request and returns StatusResponse XML per XSD.
        """
        # Validate request against XSD
        self.validate_xml(xml_req, "upi_status_request.xsd")
        print("\n[XML] -> StatusRequest (API → Switch):\n", xml_req, "\n")

        # Parse request
        root = ET.fromstring(xml_req)
        rrn_el = root.find("RRN")
        if rrn_el is None or not rrn_el.text:
            raise ValueError("StatusRequest missing RRN")
        rrn = rrn_el.text.strip()

        # Lookup ledger
        entry = self.ledger.fetch(rrn)
        status_text = entry.status if entry else "PENDING"

        # Build response XML
        resp_root = ET.Element("StatusResponse")
        rrn_node = ET.SubElement(resp_root, "RRN")
        rrn_node.text = rrn
        s_node = ET.SubElement(resp_root, "Status")
        s_node.text = status_text
        xml_resp = ET.tostring(resp_root, encoding="utf-8",
                               xml_declaration=True).decode("utf-8")

        # Validate response
        try:
            self.validate_xml(xml_resp, "upi_status_response.xsd")
        except Exception as e:
            print(f"[UPI Switch] ⚠️ StatusResponse XML validation failed: {e}")

        print("\n[XML] <<- StatusResponse (Switch → API):\n", xml_resp, "\n")
        return xml_resp

    def _finalize(self, rrn: str, status: str,
                  utr_debit: typing.Optional[str],
                  utr_credit: typing.Optional[str],
                  payer_vpa: str, payee_vpa: str,
                  amount: float, note: str,
                  txn_type: str = "PAY",
                  purpose_code: dict = None):
        tx = Transaction(
            rrn=rrn,
            payer_vpa=payer_vpa,
            payee_vpa=payee_vpa,
            amount=round(amount, 2),
            note=note,
            utr_debit=utr_debit,
            utr_credit=utr_credit,
            status=status,
            created_at=now_ts()
        )
        self.ledger.record(tx)
        # Persist into DB if configured
        if self.db_session_factory is not None:
            try:
                with self.db_session_factory() as s:
                    persist_transaction(
                        s,
                        rrn=rrn,
                        payer_vpa=payer_vpa,
                        payee_vpa=payee_vpa,
                        amount=round(amount, 2),
                        note=note,
                        utr_debit=utr_debit,
                        utr_credit=utr_credit,
                        status=status,
                        created_at_iso=now_ts(),
                    )
                    s.commit()
            except Exception as e:
                print(f"[UPI Switch] ⚠️ Failed to persist transaction: {e}")
        # Return a simple response dict
        return {"rrn": rrn, "status": status}