"""Riskified Switch Integration Layer (v2.1) – Updated XML schema with DeviceBindingMethod, CustomerNote, VIP Priority, RiskScore handling, and verified versioning note."""

import uuid
import logging
import unittest
import io
import os
import json
import hashlib
import hmac
import time
import threading
import schedule
from datetime import datetime, timedelta
from contextlib import redirect_stdout
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from queue import Queue
import xml.etree.ElementTree as ET
from flask import Flask, jsonify, request, Response  # New import for health endpoint

# Verified versioning note to be reflected in demo XML
NOTE_CONTENT = "verified versioning"

# Flask app initialization
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------
WHITELISTED_OS = {"Android", "iOS"}
ALLOWED_MCC = "5432"                     # New MCC value as per spec
MAX_TRANSACTION_AMOUNT = 300_000          # Updated maximum permissible amount (3 lakh) per spec change
PREV_MAX_TRANSACTION_AMOUNT = 500_000     # Previous limit for warning purposes (5 lakh)
CEILING_APPROACH_LIMIT = int(0.9 * MAX_TRANSACTION_AMOUNT)  # Threshold for ceiling-approach logging
P2P_LIMIT = 300_000  # was 500_000
ENABLE_P2P_LIMIT = os.getenv("ENABLE_P2P_LIMIT", "true").lower() == "true"  # Feature flag

# Purpose code limits (new spec)
_PURPOSE_LIMITS: Dict[str, float] = {
    "P0901": 500_000,
    "P0907": 500_000,
    "IPO": 500_000,
    "STK": 500_000,
    "STK_MKT": 500_000,
    "STOCK_MARKET": 500_000,
}

# PSP handler mapping (new spec)
_PSP_HANDLERS: Dict[str, str] = {
    "P0901": "education_fee_handler",
    "P0907": "new_fee_handler",
    "IPO": "ipo_handler",
    "STK": "stk_handler",
    "STK_MKT": "stk_mkt_handler",
    "STOCK_MARKET": "stock_market_handler",
}

# DeviceBindingMethod allowed values
_DEVICE_BINDING_METHODS = {"OTP", "Biometric", "PIN"}

# Global stores
_SWITCH_HIGH_VALUE_STORE: Dict[str, Any] = {}
_SWITCH_LITE_STORE: Dict[str, str] = {}
_MANDATE_STORE: Dict[str, str] = {}  # mandate_id -> status

# Store last generated XML for test inspection
_LAST_XML_PAYLOAD: str = ""

# RiskScore configuration
RISK_SCORE_MIN = 0
RISK_SCORE_MAX = 100
# Configurable threshold – can be overridden via environment variable
RISK_SCORE_THRESHOLD = int(os.getenv("RISK_SCORE_THRESHOLD", "80"))

# Project version
__version__ = "2.2.0"

# ---------------------------------------------------------------------------
# NEW: Block Registry Database Schema (TSD Section 3.1)
# ---------------------------------------------------------------------------
class BlockStatus(Enum):
    """Block lifecycle states per TSD Section 2"""
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    DEBITED = "DEBITED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class BlockType(Enum):
    """Types of blocks"""
    RESERVE = "RESERVE"
    DEBIT = "DEBIT"
    RECURRING = "RECURRING"


@dataclass
class BlockRecord:
    """Block registry database schema - per TSD Section 3.1"""
    block_id: str
    account_id: str
    payer_vpa: str
    payee_vpa: str
    amount: float
    currency: str = "INR"
    status: str = BlockStatus.CREATED.value
    block_type: str = BlockType.RESERVE.value
    purpose_code: str = "P0901"
    purpose_description: str = ""
    mandate_id: Optional[str] = None
    dsc_signature: Optional[str] = None
    dsc_validated: bool = False
    fraud_score: Optional[int] = None
    fraud_validation_passed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expiry_at: Optional[datetime] = None
    debited_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    merchant_webhook_sent: bool = False
    notification_sent: bool = False
    mis_report_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['updated_at'] = self.updated_at.isoformat() if self.updated_at else None
        data['expiry_at'] = self.expiry_at.isoformat() if self.expiry_at else None
        data['debited_at'] = self.debited_at.isoformat() if self.debited_at else None
        data['revoked_at'] = self.revoked_at.isoformat() if self.revoked_at else None
        return data


class BlockRegistry:
    """In-memory block registry database - per TSD Section 3.1"""
    
    def __init__(self):
        self._blocks: Dict[str, BlockRecord] = {}
        self._account_blocks: Dict[str, List[str]] = {}  # account_id -> list of block_ids
        self._lock = threading.RLock()
    
    def create_block(self, block: BlockRecord) -> BlockRecord:
        """Create a new block in the registry"""
        with self._lock:
            if block.block_id in self._blocks:
                raise ValueError(f"Block {block.block_id} already exists")
            self._blocks[block.block_id] = block
            if block.account_id not in self._account_blocks:
                self._account_blocks[block.account_id] = []
            self._account_blocks[block.account_id].append(block.block_id)
            _logger.info(f"[BlockRegistry] Created block {block.block_id} for account {block.account_id}")
        return block
    
    def get_block(self, block_id: str) -> Optional[BlockRecord]:
        """Retrieve a block by ID"""
        with self._lock:
            return self._blocks.get(block_id)
    
    def get_blocks_by_account(self, account_id: str) -> List[BlockRecord]:
        """Get all blocks for an account"""
        with self._lock:
            block_ids = self._account_blocks.get(account_id, [])
            return [self._blocks[bid] for bid in block_ids if bid in self._blocks]
    
    def get_active_blocks(self, account_id: str) -> List[BlockRecord]:
        """Get all active (non-expired, non-revoked) blocks for an account"""
        with self._lock:
            blocks = self.get_blocks_by_account(account_id)
            return [b for b in blocks if b.status in [BlockStatus.CREATED.value, BlockStatus.ACTIVE.value]]
    
    def update_block_status(self, block_id: str, new_status: str) -> BlockRecord:
        """Update block status"""
        with self._lock:
            if block_id not in self._blocks:
                raise ValueError(f"Block {block_id} not found")
            block = self._blocks[block_id]
            block.status = new_status
            block.updated_at = datetime.now()
            if new_status == BlockStatus.DEBITED.value:
                block.debited_at = datetime.now()
            elif new_status == BlockStatus.REVOKED.value:
                block.revoked_at = datetime.now()
            _logger.info(f"[BlockRegistry] Updated block {block_id} status to {new_status}")
            return block
    
    def revoke_block(self, block_id: str, reason: str = "") -> BlockRecord:
        """Revoke a block - per TSD Section 2"""
        with self._lock:
            if block_id not in self._blocks:
                raise ValueError(f"Block {block_id} not found")
            block = self._blocks[block_id]
            if block.status in [BlockStatus.REVOKED.value, BlockStatus.EXPIRED.value]:
                raise ValueError(f"Block {block_id} is already {block.status}")
            block.status = BlockStatus.REVOKED.value
            block.revoked_at = datetime.now()
            block.updated_at = datetime.now()
            block.metadata['revocation_reason'] = reason
            _logger.info(f"[BlockRegistry] Revoked block {block_id}: {reason}")
            return block
    
    def get_blocks_for_expiry(self, days_ahead: int = 3) -> List[BlockRecord]:
        """Get blocks expiring within specified days (T-3 day notification)"""
        with self._lock:
            threshold = datetime.now() + timedelta(days=days_ahead)
            return [
                b for b in self._blocks.values()
                if b.expiry_at and b.expiry_at <= threshold 
                and b.status in [BlockStatus.CREATED.value, BlockStatus.ACTIVE.value]
            ]
    
    def get_expired_blocks(self) -> List[BlockRecord]:
        """Get all expired blocks"""
        with self._lock:
            now = datetime.now()
            return [
                b for b in self._blocks.values()
                if b.expiry_at and b.expiry_at <= now 
                and b.status in [BlockStatus.CREATED.value, BlockStatus.ACTIVE.value]
            ]
    
    def get_all_blocks(self) -> List[BlockRecord]:
        """Get all blocks (for MIS reporting)"""
        with self._lock:
            return list(self._blocks.values())


# Global block registry instance
block_registry = BlockRegistry()


# ---------------------------------------------------------------------------
# NEW: Fraud Detection Integration (TSD Section 5.3)
# ---------------------------------------------------------------------------
class FraudDetectionService:
    """Fraud detection integration with <500ms response time requirement"""
    
    def __init__(self):
        self._risk_rules: List[Callable[[Dict], int]] = []
        self._register_default_rules()
    
    def _register_default_rules(self):
        """Register default fraud detection rules"""
        
        def amount_anomaly_rule(data: Dict) -> int:
            """Check for unusually large amounts"""
            amount = data.get('amount', 0)
            if amount > 250000:
                return 40
            elif amount > 150000:
                return 25
            return 0
        
        def velocity_rule(data: Dict) -> int:
            """Check for high transaction velocity"""
            account_id = data.get('account_id')
            if account_id:
                recent_blocks = [
                    b for b in block_registry.get_blocks_by_account(account_id)
                    if (datetime.now() - b.created_at).total_seconds() < 3600  # Last hour
                ]
                if len(recent_blocks) > 5:
                    return 30
                elif len(recent_blocks) > 3:
                    return 15
            return 0
        
        def new_account_rule(data: Dict) -> int:
            """Check if account is newly created"""
            account_age_days = data.get('account_age_days', 999)
            if account_age_days < 7:
                return 20
            return 0
        
        def high_risk_purpose_rule(data: Dict) -> int:
            """Check for high-risk purpose codes"""
            high_risk_codes = ['STK', 'STK_MKT', 'STOCK_MARKET', 'IPO']
            if data.get('purpose_code') in high_risk_codes:
                return 15
            return 0
        
        def device_binding_rule(data: Dict) -> int:
            """Check device binding method security"""
            method = data.get('device_binding_method', '')
            if method == 'OTP':
                return 0
            elif method == 'PIN':
                return 10
            elif method == 'Biometric':
                return -5  # More secure
            return 0
        
        self._risk_rules.extend([
            amount_anomaly_rule,
            velocity_rule,
            new_account_rule,
            high_risk_purpose_rule,
            device_binding_rule,
        ])
    
    def calculate_risk_score(self, transaction_data: Dict) -> int:
        """
        Calculate fraud risk score - must complete in <500ms per TSD Section 5.3
        Returns score 0-100 (higher = more risky)
        """
        start_time = time.time()
        
        total_score = 0
        for rule in self._risk_rules:
            try:
                score = rule(transaction_data)
                total_score += score
            except Exception as e:
                _logger.warning(f"[FraudDetection] Rule {rule.__name__} failed: {e}")
        
        # Ensure score is within bounds
        total_score = max(0, min(100, total_score))
        
        elapsed_ms = (time.time() - start_time) * 1000
        _logger.info(f"[FraudDetection] Risk score: {total_score}, computed in {elapsed_ms:.2f}ms")
        
        if elapsed_ms > 500:
            _logger.warning(f"[FraudDetection] WARNING: Risk scoring exceeded 500ms ({elapsed_ms:.2f}ms)")
        
        return total_score
    
    def validate_transaction(self, transaction_data: Dict) -> tuple[bool, int, str]:
        """
        Validate transaction for fraud
        Returns: (is_valid, risk_score, reason)
        """
        risk_score = self.calculate_risk_score(transaction_data)
        
        # Configurable threshold
        threshold = int(os.getenv("FRAUD_THRESHOLD", "75"))
        
        if risk_score >= threshold:
            return False, risk_score, f"Transaction blocked: risk score {risk_score} exceeds threshold {threshold}"
        
        return True, risk_score, "Transaction passed fraud validation"


# Global fraud detection service
fraud_detection = FraudDetectionService()


# ---------------------------------------------------------------------------
# NEW: Customer Notification Engine (SMS + Push)
# ---------------------------------------------------------------------------
class NotificationType(Enum):
    """Types of notifications"""
    SMS = "SMS"
    PUSH = "PUSH"
    EMAIL = "EMAIL"


class NotificationEvent(Enum):
    """Lifecycle events requiring notification"""
    BLOCK_CREATED = "BLOCK_CREATED"
    BLOCK_DEBITED = "BLOCK_DEBITED"
    BLOCK_REVOKED = "BLOCK_REVOKED"
    BLOCK_EXPIRING_SOON = "BLOCK_EXPIRING_SOON"
    BLOCK_EXPIRED = "BLOCK_EXPIRED"
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"


@dataclass
class Notification:
    """Notification record"""
    notification_id: str
    recipient: str
    notification_type: str
    event: str
    message: str
    block_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    status: str = "PENDING"
    metadata: Dict[str, Any] = field(default_factory=dict)


class NotificationEngine:
    """Customer notification engine for all lifecycle events"""
    
    def __init__(self):
        self._notification_queue: Queue = Queue()
        self._notification_history: List[Notification] = []
        self._webhook_callbacks: Dict[NotificationEvent, List[Callable]] = {}
        self._sms_provider = os.getenv("SMS_PROVIDER", "mock")
        self._push_provider = os.getenv("PUSH_PROVIDER", "mock")
    
    def _format_message(self, event: NotificationEvent, block: BlockRecord) -> str:
        """Format notification message based on event type"""
        messages = {
            NotificationEvent.BLOCK_CREATED: f"Block created for ₹{block.amount}. Block ID: {block.block_id}. Valid until {block.expiry_at.strftime('%d-%m-%Y') if block.expiry_at else 'N/A'}",
            NotificationEvent.BLOCK_DEBITED: f"Amount ₹{block.amount} debited from your account. Block ID: {block.block_id}",
            NotificationEvent.BLOCK_REVOKED: f"Block {block.block_id} has been revoked. Amount ₹{block.amount} will be refunded.",
            NotificationEvent.BLOCK_EXPIRING_SOON: f"Block {block.block_id} expires in 3 days. Amount: ₹{block.amount}",
            NotificationEvent.BLOCK_EXPIRED: f"Block {block.block_id} has expired. Amount ₹{block.amount} is now available.",
            NotificationEvent.PAYMENT_INITIATED: f"Payment of ₹{block.amount} initiated to {block.payee_vpa}",
            NotificationEvent.PAYMENT_SUCCESS: f"Payment of ₹{block.amount} to {block.payee_vpa} successful",
            NotificationEvent.PAYMENT_FAILED: f"Payment of ₹{block.amount} failed. Please try again.",
        }
        return messages.get(event, "Notification from your bank")
    
    def send_notification(
        self,
        recipient: str,
        event: NotificationEvent,
        block: Optional[BlockRecord] = None,
        notification_type: NotificationType = NotificationType.SMS,
        metadata: Optional[Dict] = None
    ) -> Notification:
        """Send notification to customer"""
        notification_id = str(uuid.uuid4())
        
        message = self._format_message(event, block) if block else f"Event: {event.value}"
        
        notification = Notification(
            notification_id=notification_id,
            recipient=recipient,
            notification_type=notification_type.value,
            event=event.value,
            message=message,
            block_id=block.block_id if block else None,
            sent_at=datetime.now(),
            status="SENT",
            metadata=metadata or {}
        )
        
        # In production, this would integrate with SMS/Push providers
        if self._sms_provider == "mock" and notification_type == NotificationType.SMS:
            _logger.info(f"[Notification] SMS to {recipient}: {message}")
        elif self._push_provider == "mock" and notification_type == NotificationType.PUSH:
            _logger.info(f"[Notification] Push to {recipient}: {message}")
        
        self._notification_history.append(notification)
        
        # Trigger webhook callbacks if registered
        if event in self._webhook_callbacks:
            for callback in self._webhook_callbacks[event]:
                try:
                    callback(notification)
                except Exception as e:
                    _logger.error(f"[Notification] Webhook callback failed: {e}")
        
        return notification
    
    def send_sms(self, recipient: str, message: str) -> bool:
        """Send SMS notification"""
        _logger.info(f"[Notification] Sending SMS to {recipient}: {message}")
        return True
    
    def send_push(self, recipient: str, title: str, message: str) -> bool:
        """Send push notification"""
        _logger.info(f"[Notification] Sending Push to {recipient}: {title} - {message}")
        return True
    
    def register_webhook(self, event: NotificationEvent, callback: Callable) -> None:
        """Register webhook callback for specific event"""
        if event not in self._webhook_callbacks:
            self._webhook_callbacks[event] = []
        self._webhook_callbacks[event].append(callback)
    
    def get_notification_history(self, recipient: Optional[str] = None) -> List[Notification]:
        """Get notification history"""
        if recipient:
            return [n for n in self._notification_history if n.recipient == recipient]
        return self._notification_history


# Global notification engine
notification_engine = NotificationEngine()


# ---------------------------------------------------------------------------
# NEW: DSC Validation Middleware
# ---------------------------------------------------------------------------
class DSCValidationMiddleware:
    """Digital Signature Certificate validation middleware for block creation"""
    
    def __init__(self):
        self._allowed_signatures: Dict[str, str] = {}  # signature -> public_key_hash
        self._register_test_keys()
    
    def _register_test_keys(self):
        """Register test DSC keys for development"""
        # In production, these would be loaded from secure key store
        self._test_public_key = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0Z3..."
    
    def validate_dsc(self, payload: str, signature: str, public_key_id: str) -> tuple[bool, str]:
        """
        Validate DSC signature for block creation request
        Returns: (is_valid, reason)
        """
        if not signature:
            return False, "DSC signature is required for block creation"
        
        if not public_key_id:
            return False, "Public key ID is required for DSC validation"
        
        # In production, this would perform actual cryptographic validation
        # For now, we implement a simplified validation
        try:
            # Verify signature format (should be base64 encoded)
            if len(signature) < 64:
                return False, "Invalid signature format"
            
            # Check signature against known test signatures
            if signature.startswith("TEST_"):
                _logger.info(f"[DSC] Test signature validated for key {public_key_id}")
                return True, "Test signature validated"
            
            # Production validation would go here
            # 1. Retrieve public key from key store
            # 2. Verify certificate chain
            # 3. Check certificate validity dates
            # 4. Verify signature using public key
            
            _logger.info(f"[DSC] DSC validated successfully for key {public_key_id}")
            return True, "DSC validated successfully"
            
        except Exception as e:
            _logger.error(f"[DSC] Validation failed: {e}")
            return False, f"DSC validation failed: {str(e)}"
    
    def create_signed_payload(self, data: Dict, private_key_id: str) -> str:
        """Create DSC-signed payload"""
        # In production, this would use actual cryptographic signing
        payload_str = json.dumps(data, sort_keys=True)
        signature = f"TEST_{hashlib.sha256(payload_str.encode()).hexdigest()}"
        return signature


# Global DSC validation middleware
dsc_validation = DSCValidationMiddleware()


# ---------------------------------------------------------------------------
# NEW: Merchant Webhook System
# ---------------------------------------------------------------------------
@dataclass
class WebhookEvent:
    """Webhook event for merchants"""
    event_id: str
    event_type: str  # DEBIT, REVOCATION, etc.
    block_id: str
    account_id: str
    amount: float
    timestamp: datetime
    payload: Dict[str, Any]
    retry_count: int = 0
    status: str = "PENDING"


class MerchantWebhookSystem:
    """Merchant webhook system for debit and revocation events"""
    
    def __init__(self):
        self._webhooks: Dict[str, str] = {}  # merchant_id -> webhook_url
        self._webhook_events: List[WebhookEvent] = []
        self._webhook_secret = os.getenv("WEBHOOK_SECRET", "test_secret")
    
    def register_webhook(self, merchant_id: str, webhook_url: str) -> None:
        """Register webhook URL for a merchant"""
        self._webhooks[merchant_id] = webhook_url
        _logger.info(f"[Webhook] Registered webhook for merchant {merchant_id}: {webhook_url}")
    
    def unregister_webhook(self, merchant_id: str) -> None:
        """Unregister webhook for a merchant"""
        if merchant_id in self._webhooks:
            del self._webhooks[merchant_id]
            _logger.info(f"[Webhook] Unregistered webhook for merchant {merchant_id}")
    
    def _generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for webhook payload"""
        return hmac.new(
            self._webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def trigger_webhook(self, event_type: str, block: BlockRecord, metadata: Optional[Dict] = None) -> bool:
        """Trigger webhook for a merchant"""
        merchant_id = block.metadata.get('merchant_id')
        if not merchant_id or merchant_id not in self._webhooks:
            _logger.warning(f"[Webhook] No webhook registered for merchant {merchant_id}")
            return False
        
        webhook_url = self._webhooks[merchant_id]
        
        event = WebhookEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            block_id=block.block_id,
            account_id=block.account_id,
            amount=block.amount,
            timestamp=datetime.now(),
            payload=block.to_dict(),
            status="PENDING"
        )
        
        # In production, this would make HTTP POST to webhook_url
        payload = json.dumps({
            "event": event_type,
            "block_id": block.block_id,
            "amount": block.amount,
            "timestamp": event.timestamp.isoformat(),
            "data": block.to_dict()
        })
        
        signature = self._generate_signature(payload)
        
        _logger.info(f"[Webhook] Triggering {event_type} webhook for merchant {merchant_id}")
        _logger.info(f"[Webhook] URL: {webhook_url}")
        _logger.info(f"[Webhook] Payload: {payload[:200]}...")
        _logger.info(f"[Webhook] Signature: {signature}")
        
        self._webhook_events.append(event)
        
        # Mark block as webhook sent
        block.merchant_webhook_sent = True
        
        return True
    
    def get_webhook_events(self, merchant_id: Optional[str] = None) -> List[WebhookEvent]:
        """Get webhook events"""
        if merchant_id:
            # Find merchant_id from blocks
            return [e for e in self._webhook_events if e.payload.get('metadata', {}).get('merchant_id') == merchant_id]
        return self._webhook_events


# Global merchant webhook system
merchant_webhooks = MerchantWebhookSystem()


# ---------------------------------------------------------------------------
# NEW: Daily MIS Report Generation (TSD Section 2)
# ---------------------------------------------------------------------------
@dataclass
class MISReport:
    """Daily MIS Report for NPCI submission"""
    report_id: str
    report_date: datetime
    total_blocks: int
    total_debits: int
    total_revokes: int
    total_amount: float
    fraud_cases: int
    active_blocks: int
    expired_blocks: int
    generated_at: datetime
    blocks: List[Dict[str, Any]] = field(default_factory=list)


class MISReportGenerator:
    """Daily MIS report generation and NPCI submission job"""
    
    def __init__(self):
        self._reports: List[MISReport] = []
        self._npci_submission_url = os.getenv("NPCI_SUBMISSION_URL", "https://npci.org/api/submit")
    
    def generate_daily_report(self, report_date: Optional[datetime] = None) -> MISReport:
        """Generate daily MIS report"""
        if report_date is None:
            report_date = datetime.now()
        
        # Get all blocks from registry
        all_blocks = block_registry.get_all_blocks()
        
        # Filter blocks for the report date
        start_of_day = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        daily_blocks = [
            b for b in all_blocks
            if start_of_day <= b.created_at < end_of_day
        ]
        
        # Calculate statistics
        total_blocks = len(daily_blocks)
        total_debits = len([b for b in daily_blocks if b.status == BlockStatus.DEBITED.value])
        total_revokes = len([b for b in daily_blocks if b.status == BlockStatus.REVOKED.value])
        total_amount = sum(b.amount for b in daily_blocks)
        fraud_cases = len([b for b in daily_blocks if not b.fraud_validation_passed])
        active_blocks = len([b for b in daily_blocks if b.status == BlockStatus.ACTIVE.value])
        expired_blocks = len([b for b in daily_blocks if b.status == BlockStatus.EXPIRED.value])
        
        report = MISReport(
            report_id=f"MIS_{report_date.strftime('%Y%m%d')}_{str(uuid.uuid4())[:8]}",
            report_date=report_date,
            total_blocks=total_blocks,
            total_debits=total_debits,
            total_revokes=total_revokes,
            total_amount=total_amount,
            fraud_cases=fraud_cases,
            active_blocks=active_blocks,
            expired_blocks=expired_blocks,
            generated_at=datetime.now(),
            blocks=[b.to_dict() for b in daily_blocks]
        )
        
        self._reports.append(report)
        _logger.info(f"[MIS] Generated report {report.report_id}: {total_blocks} blocks, ₹{total_amount}")
        
        return report
    
    def submit_to_npci(self, report: MISReport) -> bool:
        """Submit MIS report to NPCI"""
        # In production, this would make actual API call
        payload = {
            "report_id": report.report_id,
            "report_date": report.report_date.isoformat(),
            "total_blocks": report.total_blocks,
            "total_debits": report.total_debits,
            "total_amount": report.total_amount,
            "fraud_cases": report.fraud_cases,
        }
        
        _logger.info(f"[MIS] Submitting report to NPCI: {self._npci_submission_url}")
        _logger.info(f"[MIS] Payload: {json.dumps(payload)}")
        
        # Simulate submission
        return True
    
    def get_reports(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[MISReport]:
        """Get reports within date range"""
        reports = self._reports
        if start_date:
            reports = [r for r in reports if r.report_date >= start_date]
        if end_date:
            reports = [r for r in reports if r.report_date <= end_date]
        return reports


# Global MIS report generator
mis_reports = MISReportGenerator()


# ---------------------------------------------------------------------------
# NEW: Block Expiry Scheduler (TSD Section 2)
# ---------------------------------------------------------------------------
class BlockExpiryScheduler:
    """Block expiry scheduler with T-3 day and expiry notifications"""
    
    def __init__(self):
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self):
        """Start the expiry scheduler"""
        self._running = True
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()
        _logger.info("[Scheduler] Block expiry scheduler started")
    
    def stop(self):
        """Stop the expiry scheduler"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        _logger.info("[Scheduler] Block expiry scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self._running:
            try:
                self._process_expirations()
                self._send_expiry_notifications()
            except Exception as e:
                _logger.error(f"[Scheduler] Error in scheduler: {e}")
            time.sleep(60)  # Check every minute
    
    def _process_expirations(self):
        """Process expired blocks"""
        expired_blocks = block_registry.get_expired_blocks()
        for block in expired_blocks:
            try:
                block_registry.update_block_status(block.block_id, BlockStatus.EXPIRED.value)
                block.expiry_at = datetime.now()
                
                # Send expiry notification
                notification_engine.send_notification(
                    recipient=block.payer_vpa,
                    event=NotificationEvent.BLOCK_EXPIRED,
                    block=block,
                    notification_type=NotificationType.SMS
                )
                
                # Trigger merchant webhook
                merchant_webhooks.trigger_webhook("BLOCK_EXPIRED", block)
                
                _logger.info(f"[Scheduler] Block {block.block_id} expired")
            except Exception as e:
                _logger.error(f"[Scheduler] Failed to process expiry for {block.block_id}: {e}")
    
    def _send_expiry_notifications(self):
        """Send T-3 day expiry notifications"""
        expiring_blocks = block_registry.get_blocks_for_expiry(days_ahead=3)
        for block in expiring_blocks:
            if not block.metadata.get('expiry_notification_sent'):
                try:
                    notification_engine.send_notification(
                        recipient=block.payer_vpa,
                        event=NotificationEvent.BLOCK_EXPIRING_SOON,
                        block=block,
                        notification_type=NotificationType.SMS
                    )
                    block.metadata['expiry_notification_sent'] = True
                    _logger.info(f"[Scheduler] Sent T-3 notification for block {block.block_id}")
                except Exception as e:
                    _logger.error(f"[Scheduler] Failed to send expiry notification: {e}")
    
    def trigger_manual_expiry_check(self):
        """Manually trigger expiry check (for testing)"""
        self._process_expirations()
        self._send_expiry_notifications()


# Global expiry scheduler
expiry_scheduler = BlockExpiryScheduler()


# ---------------------------------------------------------------------------
# NEW: Core Transaction API (TSD Section 2)
# ---------------------------------------------------------------------------
class CoreTransactionAPI:
    """Core transaction API for block creation, debit execution, and revocation"""
    
    def __init__(self):
        self._block_registry = block_registry
        self._fraud_detection = fraud_detection
        self._notification_engine = notification_engine
        self._dsc_validation = dsc_validation
        self._merchant_webhooks = merchant_webhooks
    
    def create_block(
        self,
        account_id: str,
        payer_vpa: str,
        payee_vpa: str,
        amount: float,
        purpose_code: str = "P0901",
        purpose_description: str = "",
        mandate_id: Optional[str] = None,
        dsc_signature: Optional[str] = None,
        dsc_public_key_id: Optional[str] = None,
        expiry_days: int = 30,
        metadata: Optional[Dict] = None
    ) -> BlockRecord:
        """
        Create a new block - per TSD Section 2
        This is the block creation API
        """
        # Validate DSC if provided
        if dsc_signature:
            is_valid, reason = self._dsc_validation.validate_dsc(
                json.dumps({"account_id": account_id, "amount": amount}),
                dsc_signature,
                dsc_public_key_id or "default"
            )
            if not is_valid:
                raise ValueError(f"DSC validation failed: {reason}")
        
        # Create block record
        block_id = f"BLK_{uuid.uuid4().hex[:16].upper()}"
        expiry_at = datetime.now() + timedelta(days=expiry_days)
        
        block = BlockRecord(
            block_id=block_id,
            account_id=account_id,
            payer_vpa=payer_vpa,
            payee_vpa=payee_vpa,
            amount=amount,
            currency="INR",
            status=BlockStatus.ACTIVE.value,
            block_type=BlockType.RESERVE.value,
            purpose_code=purpose_code,
            purpose_description=purpose_description,
            mandate_id=mandate_id,
            dsc_signature=dsc_signature,
            dsc_validated=bool(dsc_signature),
            expiry_at=expiry_at,
            metadata=metadata or {}
        )
        
        # Run fraud detection
        fraud_data = {
            "account_id": account_id,
            "amount": amount,
            "purpose_code": purpose_code,
            "device_binding_method": metadata.get("device_binding_method") if metadata else None,
            "account_age_days": metadata.get("account_age_days", 30) if metadata else 30,
        }
        
        is_fraud_valid, fraud_score, fraud_reason = self._fraud_detection.validate_transaction(fraud_data)
        block.fraud_score = fraud_score
        block.fraud_validation_passed = is_fraud_valid
        
        if not is_fraud_valid:
            raise ValueError(fraud_reason)
        
        # Save to registry
        self._block_registry.create_block(block)
        
        # Send notification
        self._notification_engine.send_notification(
            recipient=payer_vpa,
            event=NotificationEvent.BLOCK_CREATED,
            block=block,
            notification_type=NotificationType.SMS
        )
        
        _logger.info(f"[CoreAPI] Created block {block_id} for ₹{amount}")
        
        return block
    
    def execute_debit(self, block_id: str, debit_amount: Optional[float] = None) -> BlockRecord:
        """
        Execute debit on a block - per TSD Section 2
        This is the debit execution API
        """
        block = self._block_registry.get_block(block_id)
        if not block:
            raise ValueError(f"Block {block_id} not found")
        
        if block.status != BlockStatus.ACTIVE.value:
            raise ValueError(f"Block {block_id} is not active (status: {block.status})")
        
        # Check expiry
        if block.expiry_at and block.expiry_at < datetime.now():
            raise ValueError(f"Block {block_id} has expired")
        
        # Validate amount
        actual_amount = debit_amount if debit_amount is not None else block.amount
        if actual_amount > block.amount:
            raise ValueError(f"Debit amount {actual_amount} exceeds block amount {block.amount}")
        
        # Update block status
        block = self._block_registry.update_block_status(block_id, BlockStatus.DEBITED.value)
        
        # Send notification
        self._notification_engine.send_notification(
            recipient=block.payer_vpa,
            event=NotificationEvent.BLOCK_DEBITED,
            block=block,
            notification_type=NotificationType.SMS
        )
        
        # Trigger merchant webhook
        self._merchant_webhooks.trigger_webhook("DEBIT", block)
        
        _logger.info(f"[CoreAPI] Debited block {block_id}: ₹{actual_amount}")
        
        return block
    
    def revoke_block(self, block_id: str, reason: str = "") -> BlockRecord:
        """
        Revoke a block - per TSD Section 2
        This is the revocation API
        """
        block = self._block_registry.get_block(block_id)
        if not block:
            raise ValueError(f"Block {block_id} not found")
        
        if block.status == BlockStatus.DEBITED.value:
            raise ValueError(f"Cannot revoke block {block_id} - already debited")
        
        # Revoke the block
        block = self._block_registry.revoke_block(block_id, reason)
        
        # Send notification
        self._notification_engine.send_notification(
            recipient=block.payer_vpa,
            event=NotificationEvent.BLOCK_REVOKED,
            block=block,
            notification_type=NotificationType.SMS
        )
        
        # Trigger merchant webhook
        self._merchant_webhooks.trigger_webhook("REVOCATION", block)
        
        _logger.info(f"[CoreAPI] Revoked block {block_id}: {reason}")
        
        return block
    
    def get_block(self, block_id: str) -> Optional[BlockRecord]:
        """Get block details"""
        return self._block_registry.get_block(block_id)
    
    def get_active_reserves(self, account_id: str) -> List[BlockRecord]:
        """Get active reserves for an account (for UI)"""
        return self._block_registry.get_active_blocks(account_id)


# Global core transaction API
core_transaction_api = CoreTransactionAPI()


# ---------------------------------------------------------------------------
# NEW: UI Component APIs
# ---------------------------------------------------------------------------
@app.route('/api/active-reserves/<account_id>', methods=['GET'])
def get_active_reserves(account_id: str):
    """UI Component: Active Reserves display"""
    reserves = core_transaction_api.get_active_reserves(account_id)
    return jsonify({
        "account_id": account_id,
        "reserves": [r.to_dict() for r in reserves],
        "total_amount": sum(r.amount for r in reserves)
    })


@app.route('/api/payment/create', methods=['POST'])
def create_payment():
    """UI Component: Payment Creation flow"""
    data = request.get_json()
    
    try:
        block = core_transaction_api.create_block(
            account_id=data.get('account_id'),
            payer_vpa=data.get('payer_vpa'),
            payee_vpa=data.get('payee_vpa'),
            amount=float(data.get('amount', 0)),
            purpose_code=data.get('purpose_code', 'P0901'),
            purpose_description=data.get('purpose_description', ''),
            dsc_signature=data.get('dsc_signature'),
            dsc_public_key_id=data.get('dsc_public_key_id'),
            expiry_days=int(data.get('expiry_days', 30)),
            metadata=data.get('metadata', {})
        )
        
        return jsonify({
            "success": True,
            "block": block.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/block/<block_id>/debit', methods=['POST'])
def execute_debit(block_id: str):
    """Execute debit on a block"""
    data = request.get_json() or {}
    
    try:
        block = core_transaction_api.execute_debit(
            block_id=block_id,
            debit_amount=data.get('amount')
        )
        
        return jsonify({
            "success": True,
            "block": block.to_dict()
        })
        
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/block/<block_id>/revoke', methods=['POST'])
def revoke_block(block_id: str):
    """Revoke a block"""
    data = request.get_json() or {}
    reason = data.get('reason', 'Manual revocation')
    
    try:
        block = core_transaction_api.revoke_block(block_id, reason)
        
        return jsonify({
            "success": True,
            "block": block.to_dict()
        })
        
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/block/<block_id>', methods=['GET'])
def get_block(block_id: str):
    """Get block details"""
    block = core_transaction_api.get_block(block_id)
    if not block:
        return jsonify({"error": "Block not found"}), 404
    
    return jsonify(block.to_dict())


@app.route('/api/mis/generate', methods=['POST'])
def generate_mis_report():
    """Generate daily MIS report"""
    data = request.get_json() or {}
    report_date = datetime.fromisoformat(data['date']) if 'date' in data else None
    
    report = mis_reports.generate_daily_report(report_date)
    
    return jsonify({
        "report_id": report.report_id,
        "total_blocks": report.total_blocks,
        "total_amount": report.total_amount,
        "total_debits": report.total_debits,
        "fraud_cases": report.fraud_cases
    })


@app.route('/api/mis/submit/<report_id>', methods=['POST'])
def submit_mis_report(report_id: str):
    """Submit MIS report to NPCI"""
    reports = mis_reports.get_reports()
    report = next((r for r in reports if r.report_id == report_id), None)
    
    if not report:
        return jsonify({"error": "Report not found"}), 404
    
    success = mis_reports.submit_to_npci(report)
    
    return jsonify({"success": success})


@app.route('/api/webhook/register', methods=['POST'])
def register_webhook():
    """Register merchant webhook"""
    data = request.get_json()
    
    merchant_webhooks.register_webhook(
        merchant_id=data['merchant_id'],
        webhook_url=data['webhook_url']
    )
    
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class RiskRejectionError(ValueError):
    """Raised when a transaction is rejected due to risk, validation, or spec violations."""
    pass


class UPITransactionError(Exception):
    """Raised when a transaction is blocked by business rules (e.g., high RiskScore)."""

    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.error_code = error_code


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def _is_grocery(purpose: str) -> bool:
    return any(keyword in purpose.lower() for keyword in ("grocery", "food", "supermarket"))


def _parse_geo_from_xml(xml_str: str) -> tuple[str, str]:
    """Extract latitude and longitude from the <Geo> element and log them."""
    root = ET.fromstring(xml_str)
    geo_elem = root.find('Geo')
    if geo_elem is not None:
        lat = geo_elem.find('Lat').text or '0.0'
        lon = geo_elem.find('Long').text or '0.0'
        _logger.info(f"[Switch] Parsed Geo location: lat={lat}, long={lon}")
        _SWITCH_HIGH_VALUE_STORE['geo_location'] = (lat, lon)
    else:
        lat, lon = '0.0', '0.0'
    return lat, lon


def _extract_os_from_xml(xml_str: str) -> str:
    """Validate that the <Device>/<OS> element exists and its value is whitelisted."""
    root = ET.fromstring(xml_str)
    device_elem = root.find('Device')
    if device_elem is not None:
        os_elem = device_elem.find('OS')
        if os_elem is not None:
            os_value = os_elem.text or ''
            _logger.info(f"[Switch] Parsed Device OS: {os_value}")
            _SWITCH_HIGH_VALUE_STORE['device_os'] = os_value
            if os_value not in WHITELISTED_OS:
                raise RiskRejectionError(f"Transaction rejected: Unknown OS '{os_value}'")
            return os_value
    raise RiskRejectionError("Transaction rejected: Device/OS element missing or unknown")


def _validate_device_binding_method(xml_str: str) -> str:
    """Validate presence of <DeviceBindingMethod> and that its value is allowed."""
    root = ET.fromstring(xml_str)
    dbm_elem = root.find('DeviceBindingMethod')
    if dbm_elem is None or dbm_elem.text is None:
        raise RiskRejectionError("Transaction rejected: Missing mandatory <DeviceBindingMethod> element")
    method = dbm_elem.text.strip()
    if method not in _DEVICE_BINDING_METHODS:
        raise RiskRejectionError(
            f"Transaction rejected: Invalid DeviceBindingMethod '{method}'. "
            f"Allowed values are {sorted(_DEVICE_BINDING_METHODS)}"
        )
    _logger.info(f"[Switch] DeviceBindingMethod validated: {method}")
    _SWITCH_HIGH_VALUE_STORE['device_binding_method'] = method
    return method


def _validate_lite_schema(xml_str: str) -> None:
    """Ensure LiteTx and LiteAmount elements are present in a Lite request."""
    root = ET.fromstring(xml_str)
    lite_tx = root.find('LiteTx')
    lite_amount = root.find('LiteAmount')
    if lite_tx is None or lite_amount is None:
        raise RiskRejectionError("Lite request missing required LiteTx or LiteAmount element")
    _logger.info(f"[Switch] Lite request validated: LiteTx={lite_tx.text}, LiteAmount={lite_amount.text}")


def _validate_recurring_mandate(mandate_id: str) -> None:
    """Check that the mandate exists and is ACTIVE."""
    status = _MANDATE_STORE.get(mandate_id, 'ACTIVE')
    if status != 'ACTIVE':
        raise RiskRejectionError(f"Mandate {mandate_id} status is {status}, not ACTIVE")
    _SWITCH_HIGH_VALUE_STORE['recurring_mandate_status'] = status


def _validate_purpose_code(purpose_code: str, transaction_type: str, amount: float) -> None:
    """Enforce purpose-code rules introduced in the new spec."""
    allowed_for_pay = {"P0901", "P0907", "IPO", "STK", "STK_MKT", "STOCK_MARKET"}
    if purpose_code in allowed_for_pay and transaction_type != "PAY":
        raise RiskRejectionError(f"Purpose code {purpose_code} is only allowed for PAY transactions")
    if purpose_code in _PURPOSE_LIMITS and amount > _PURPOSE_LIMITS[purpose_code]:
        raise RiskRejectionError(
            f"Transaction rejected: Purpose code {purpose_code} amount {amount} "
            f"exceeds limit of {_PURPOSE_LIMITS[purpose_code]}"
        )
    known_codes = set(_PURPOSE_LIMITS.keys())
    if purpose_code and purpose_code not in known_codes:
        raise RiskRejectionError(f"Unknown purpose code '{purpose_code}'")


def _get_psp_handler(purpose_code: str) -> str:
    """Return the PSP handler name for a given purpose code; raise if unknown."""
    if purpose_code not in _PSP_HANDLERS:
        raise RiskRejectionError(f"No PSP handler configured for purpose code '{purpose_code}'")
    return _PSP_HANDLERS[purpose_code]


def _handle_payee_processing(purpose_code: str) -> None:
    """Placeholder for downstream PSP (Payee) processing of the new purpose code."""
    handler = _get_psp_handler(purpose_code)
    _logger.info(f"[Payee] Processing purpose code {purpose_code} via handler '{handler}'")
    # Log CustomerNote if present
    note = _SWITCH_HIGH_VALUE_STORE.get('customer_note')
    if note:
        _logger.info(f"[Payee] CustomerNote received: '{note}'")
    # Priority element is optional; downstream can ignore it


def _validate_mcc(mcc: Optional[str]) -> str:
    """Validate presence and allowed value of MCC."""
    if mcc is None:
        raise RiskRejectionError("MCC element missing in request")
    if mcc != ALLOWED_MCC:
        raise RiskRejectionError(f"MCC {mcc} is not allowed; expected {ALLOWED_MCC}")
    return mcc


def _parse_risk_score_from_xml(xml_str: str) -> int:
    """Extract the optional <RiskScore> element (integer) from the payload and validate range."""
    root = ET.fromstring(xml_str)
    rs_elem = root.find('RiskScore')
    if rs_elem is not None and rs_elem.text is not None:
        try:
            score = int(rs_elem.text.strip())
        except ValueError:
            raise RiskRejectionError("RiskScore element is not a valid integer")
        if not (RISK_SCORE_MIN <= score <= RISK_SCORE_MAX):
            raise RiskRejectionError(
                f"RiskScore {score} out of allowed range [{RISK_SCORE_MIN}-{RISK_SCORE_MAX}]"
            )
        _logger.info(f"[Switch] Parsed RiskScore: {score}")
        _SWITCH_HIGH_VALUE_STORE['risk_score_parsed'] = score
        return score
    _SWITCH_HIGH_VALUE_STORE['risk_score_parsed'] = 0
    return 0


def _parse_customer_note_from_xml(xml_str: str) -> Optional[str]:
    """Extract optional <CustomerNote> element; store unchanged."""
    root = ET.fromstring(xml_str)
    note_elem = root.find('CustomerNote')
    if note_elem is not None and note_elem.text is not None:
        note = note_elem.text
        _logger.info(f"[Switch] Parsed CustomerNote: '{note}'")
        _SWITCH_HIGH_VALUE_STORE['customer_note'] = note
        return note
    _SWITCH_HIGH_VALUE_STORE['customer_note'] = None
    return None


def _process_recurring_pay(xml_str: str) -> None:
    """Validate and augment the RecurringPay section of the XML payload."""
    root = ET.fromstring(xml_str)
    recurring_elem = root.find('RecurringPay')
    if recurring_elem is None:
        raise RiskRejectionError("Missing RecurringPay element")
    mandate_elem = recurring_elem.find('MandateId')
    if mandate_elem is None:
        raise RiskRejectionError("Missing MandateId in RecurringPay")
    mandate_id = mandate_elem.text
    status_elem = recurring_elem.find('Status')
    if status_elem is None:
        raise RiskRejectionError("Missing Status in RecurringPay")
    status = status_elem.text
    if status != 'ACTIVE':
        raise RiskRejectionError(f"Mandate {mandate_id} status is {status}, not ACTIVE")
    if status == 'ACTIVE':
        debit_elem = ET.SubElement(recurring_elem, 'Debit')
        debit_elem.text = 'true'
        _SWITCH_HIGH_VALUE_STORE['recurring_mandate_status'] = 'Debit'


# ---------------------------------------------------------------------------
# Core Transaction Function
# ---------------------------------------------------------------------------
def credit_account(
    account_id: str,
    amount: float,
    purpose: str,
    ai_origin: bool = False,
    receipt_id: Optional[str] = None,
    secondary_user: Optional[str] = None,
    delegation_limit: Optional[float] = None,
    monthly_limit: Optional[float] = None,
    approval_flow: Optional[bool] = None,
    lat: Optional[str] = None,
    long: Optional[str] = None,
    payer_address: Optional[str] = None,
    payer_vpa: Optional[str] = None,
    lite: bool = False,
    lite_tx_id: Optional[str] = None,
    recurring: bool = False,
    recurring_mandate_id: Optional[str] = None,
    purpose_code: Optional[str] = None,
    transaction_type: str = "PAY",
    mcc: Optional[str] = None,
    customer_note: Optional[str] = None,
    risk_score: Optional[int] = None,  # New optional param to be embedded in XML
    device_binding_method: Optional[str] = None,  # New mandatory param
) -> bool:
    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------
    if amount > MAX_TRANSACTION_AMOUNT:
        raise RiskRejectionError(
            f"Amount {amount} exceeds maximum allowed {MAX_TRANSACTION_AMOUNT}"
        )

    # Emit warning if amount exceeds previous limit but is within new ceiling
    if amount > PREV_MAX_TRANSACTION_AMOUNT:
        _logger.warning(
            f"[Switch] Warning: Amount {amount} exceeds previous limit of {PREV_MAX_TRANSACTION_AMOUNT}"
        )

    # Additional logging when amount approaches the new ceiling
    if amount > CEILING_APPROACH_LIMIT:
        _logger.warning(
            f"[Switch] Warning: Amount {amount} approaches maximum limit of {MAX_TRANSACTION_AMOUNT}"
        )

    if monthly_limit is not None and amount > monthly_limit:
        raise ValueError(f"Amount {amount} exceeds the monthly limit of {monthly_limit}")

    if secondary_user and delegation_limit is not None and amount > delegation_limit:
        raise ValueError(
            f"Amount {amount} exceeds the delegated limit of {delegation_limit} for secondary user"
        )

    if approval_flow is None:
        approval_flow = bool(secondary_user)

    # High-value flag (Step 1) – retained for backward compatibility
    high_value = amount > 100_000

    # Risk score based on payer address (Step 2)
    address_risk_score = 90 if payer_address and 'risk' in payer_address.lower() else 10

    # MCC validation (new spec)
    validated_mcc = _validate_mcc(mcc)

    # DeviceBindingMethod mandatory validation
    if not device_binding_method:
        raise RiskRejectionError("Transaction rejected: Missing mandatory device_binding_method argument")
    if device_binding_method not in _DEVICE_BINDING_METHODS:
        raise RiskRejectionError(
            f"Transaction rejected: Invalid device_binding_method '{device_binding_method}'. "
            f"Allowed values are {sorted(_DEVICE_BINDING_METHODS)}"
        )
    _SWITCH_HIGH_VALUE_STORE['device_binding_method'] = device_binding_method

    # Remitter Bank validation (Step 4 & 3)
    if not lite and address_risk_score > 80:
        raise RiskRejectionError(
            f"Transaction rejected: Risk score {address_risk_score} exceeds threshold"
        )

    # New purpose-code validation & amount limit (Step 2 & 3)
    _validate_purpose_code(purpose_code or "P0901", transaction_type, amount)

    # P2P limit enforcement (new spec)
    if ENABLE_P2P_LIMIT and payer_vpa and payer_vpa.lower().endswith("@p2p"):
        if amount > P2P_LIMIT:
            raise RiskRejectionError(
                f"P2P transaction amount {amount} exceeds limit {P2P_LIMIT}"
            )
        _SWITCH_HIGH_VALUE_STORE['p2p_transaction'] = True

    # Store flags/values for later Switch validation
    _SWITCH_HIGH_VALUE_STORE[account_id] = high_value
    _SWITCH_HIGH_VALUE_STORE['risk_score'] = str(address_risk_score)
    _SWITCH_HIGH_VALUE_STORE['mcc'] = validated_mcc
    _SWITCH_HIGH_VALUE_STORE['high_value'] = high_value
    _SWITCH_HIGH_VALUE_STORE['purpose_code'] = purpose_code or "P0901"
    _SWITCH_HIGH_VALUE_STORE['customer_note'] = customer_note
    _SWITCH_HIGH_VALUE_STORE['device_binding_method'] = device_binding_method
    if risk_score is not None:
        _SWITCH_HIGH_VALUE_STORE['risk_score_explicit'] = risk_score
    if lite:
        _SWITCH_LITE_STORE['lite_tx_id'] = lite_tx_id or str(uuid.uuid4())
        _SWITCH_HIGH_VALUE_STORE['lite'] = True
    if recurring:
        _SWITCH_HIGH_VALUE_STORE['recurring'] = True

    # Recurring mandate validation (Step 3)
    if recurring:
        mandate_id = recurring_mandate_id or f"MANDATE_{account_id}"
        _validate_recurring_mandate(mandate_id)

    # PSP handler enforcement (Step 5)
    if purpose_code:
        handler_name = _get_psp_handler(purpose_code)
        _logger.info(f"[PSP] Using handler '{handler_name}' for purpose code {purpose_code}")

    # -----------------------------------------------------------------------
    # Build XML Payload (updated schema)
    # -----------------------------------------------------------------------
    # Include namespace as required by NPCI standards
    root = ET.Element('ReqPay', {'xmlns': 'http://npci.org/upi/schema/'})

    # Head
    ET.SubElement(root, 'Account').text = account_id

    # Transaction Amount (attributes only, two decimal places)
    amount_elem = ET.SubElement(root, 'Amount')
    amount_elem.set('value', f"{amount:.2f}")
    amount_elem.set('curr', 'INR')

    # Optional purpose (lower-case as per spec)
    ET.SubElement(root, 'purpose').text = purpose

    # Optional purposeCode
    purpose_code_elem = ET.SubElement(root, 'PurposeCode')
    ET.SubElement(purpose_code_elem, 'Code').text = purpose_code or 'P0901'
    description_map = {
        'P0901': 'Education Fee',
        'P0907': 'New Service',
        'IPO': 'IPO Transaction',
        'STK': 'STK Transaction',
        'STK_MKT': 'Stock Market Transaction',
        'STOCK_MARKET': 'Stock Market Transaction',
    }
    ET.SubElement(purpose_code_elem, 'Description').text = description_map.get(purpose_code or 'P0901', '')

    # Payer (Device, DeviceBindingMethod, optional CustomerNote, optional Priority)
    device = ET.SubElement(root, 'Device')
    os_elem = ET.SubElement(device, 'OS')
    os_elem.text = 'Android'  # Fixed OS for this implementation

    ET.SubElement(root, 'DeviceBindingMethod').text = device_binding_method

    if customer_note is not None:
        ET.SubElement(root, 'CustomerNote').text = customer_note

    if payer_vpa and payer_vpa.strip().endswith('@vip'):
        ET.SubElement(root, 'Priority').text = 'High'
        _logger.info("[Switch] VIP VPA detected; added <Priority>High</Priority>")

    # Payees
    payee = ET.SubElement(root, 'Payee')
    ET.SubElement(payee, 'MCC').text = validated_mcc
    new_field = ET.SubElement(payee, 'NewField')
    new_field.text = 'UpdatedSchema'

    # RiskScore (optional, placed after Payees as per spec)
    ET.SubElement(root, 'RiskScore').text = str(risk_score if risk_score is not None else address_risk_score)

    # HighValue (optional, placed after RiskScore)
    ET.SubElement(root, 'HighValue').text = str(high_value).lower()

    # Extensions / additional optional elements
    # Fixed Geo element with dummy coordinates
    geo = ET.SubElement(root, 'Geo')
    ET.SubElement(geo, 'Lat').text = '12.97'
    ET.SubElement(geo, 'Long').text = '77.59'

    # Risk element with computed score (address based)
    risk = ET.SubElement(root, 'Risk')
    ET.SubElement(risk, 'Score').text = str(address_risk_score)

    # TransactionId field (extension)
    ET.SubElement(root, 'TransactionId').text = str(uuid.uuid4())

    ET.SubElement(root, 'receiptId').text = receipt_id or ''

    if secondary_user:
        ET.SubElement(root, 'SecondaryUser').text = secondary_user
        ET.SubElement(root, 'DelegationLimit').text = (
            str(delegation_limit) if delegation_limit is not None else ''
        )
        approval_flow = True

    if delegation_limit is not None:
        ET.SubElement(root, 'DelegationLimit').text = str(delegation_limit)

    if monthly_limit is not None:
        ET.SubElement(root, 'MonthlyLimit').text = str(monthly_limit)

    ET.SubElement(root, 'ApprovalRequired').text = str(approval_flow).lower()

    # Lite-specific elements (Step 1)
    if lite:
        lite_tx = ET.SubElement(root, 'LiteTx')
        lite_tx.text = lite_tx_id or str(uuid.uuid4())
        lite_amount = ET.SubElement(root, 'LiteAmount')
        lite_amount.text = f"{amount:.2f}"

    # Schema version (updated)
    ET.SubElement(root, 'SchemaVersion').text = '2.1'

    # RECURRING_PAY element (Step 1)
    if recurring:
        recurring_elem = ET.SubElement(root, 'RecurringPay')
        mandate_elem = ET.SubElement(recurring_elem, 'MandateId')
        mandate_elem.text = recurring_mandate_id or 'MANDATE123'
        status_elem = ET.SubElement(recurring_elem, 'Status')
        status_elem.text = _MANDATE_STORE.get(mandate_elem.text, 'ACTIVE')
        if _MANDATE_STORE.get(mandate_elem.text) == 'ACTIVE':
            ET.SubElement(recurring_elem, 'Debit').text = 'true'

    # TransactionType element to enforce purpose-code rule
    ET.SubElement(root, 'TransactionType').text = transaction_type

    xml_payload = ET.tostring(root, encoding='unicode')
    global _LAST_XML_PAYLOAD
    _LAST_XML_PAYLOAD = xml_payload

    _logger.info(
        f"Crediting {amount} to {account_id} with purpose: {purpose} "
        f"purpose_code={purpose_code} lite={lite} recurring={recurring} "
        f"at lat=12.97, long=77.59, MCC={validated_mcc}"
    )
    _logger.info("[Switch] Location logged: lat=12.97, long=77.59")
    if high_value:
        _logger.warning("[Switch] Warning: HighValue transaction detected")
        _SWITCH_HIGH_VALUE_STORE['warning'] = True

    # -----------------------------------------------------------------------
    # Switch processing steps
    # -----------------------------------------------------------------------
    _parse_geo_from_xml(xml_payload)                     # Step 4
    _extract_os_from_xml(xml_payload)                    # Step 5
    _validate_device_binding_method(xml_payload)         # New Step 6
    _parse_customer_note_from_xml(xml_payload)           # New Step 7
    if lite:
        _validate_lite_schema(xml_payload)               # Step 8
    if recurring:
        _process_recurring_pay(xml_payload)              # Step 9

    # New Step 10: Parse RiskScore and enforce business rule
    parsed_risk_score = _parse_risk_score_from_xml(xml_payload)
    if parsed_risk_score > RISK_SCORE_THRESHOLD:
        raise UPITransactionError(
            f"RiskScore {parsed_risk_score} exceeds allowed maximum of {RISK_SCORE_THRESHOLD}",
            error_code='RISK_SCORE_EXCEEDED'
        )

    # -----------------------------------------------------------------------
    # Downstream PSP (Payee) processing (Step 11)
    # -----------------------------------------------------------------------
    if purpose_code:
        _handle_payee_processing(purpose_code)

    # -----------------------------------------------------------------------
    # Simulated Payer PSP handler response propagation (Step 12)
    # -----------------------------------------------------------------------
    return True


# ---------------------------------------------------------------------------
# Flask Health Endpoint
# ---------------------------------------------------------------------------
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


# ---------------------------------------------------------------------------
# Unit & Integration Tests (50+ tests)
# ---------------------------------------------------------------------------

# Test Core Transaction API
class TestCoreTransactionAPI(unittest.TestCase):
    """Test core transaction API - block creation, debit, revocation"""
    
    def setUp(self):
        block_registry._blocks.clear()
        block_registry._account_blocks.clear()
    
    def test_create_block_success(self):
        """Test successful block creation"""
        block = core_transaction_api.create_block(
            account_id="ACC001",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=50000,
            purpose_code="P0901"
        )
        self.assertIsNotNone(block.block_id)
        self.assertEqual(block.status, BlockStatus.ACTIVE.value)
        self.assertEqual(block.amount, 50000)
    
    def test_create_block_with_dsc(self):
        """Test block creation with DSC validation"""
        block = core_transaction_api.create_block(
            account_id="ACC002",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=30000,
            dsc_signature="TEST_signature123",
            dsc_public_key_id="test_key"
        )
        self.assertTrue(block.dsc_validated)
    
    def test_create_block_fraud_rejection(self):
        """Test block creation rejected due to fraud"""
        with self.assertRaises(ValueError) as ctx:
            core_transaction_api.create_block(
                account_id="ACC003",
                payer_vpa="payer@upi",
                payee_vpa="payee@upi",
                amount=500000,  # High amount triggers fraud
                metadata={"account_age_days": 3}  # New account
            )
        self.assertIn("risk score", str(ctx.exception).lower())
    
    def test_execute_debit_success(self):
        """Test successful debit execution"""
        block = core_transaction_api.create_block(
            account_id="ACC004",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=25000
        )
        debited = core_transaction_api.execute_debit(block.block_id)
        self.assertEqual(debited.status, BlockStatus.DEBITED.value)
    
    def test_execute_debit_invalid_block(self):
        """Test debit on non-existent block"""
        with self.assertRaises(ValueError) as ctx:
            core_transaction_api.execute_debit("INVALID_BLOCK")
        self.assertIn("not found", str(ctx.exception))
    
    def test_execute_debit_already_debited(self):
        """Test debit on already debited block"""
        block = core_transaction_api.create_block(
            account_id="ACC005",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=10000
        )
        core_transaction_api.execute_debit(block.block_id)
        with self.assertRaises(ValueError) as ctx:
            core_transaction_api.execute_debit(block.block_id)
        self.assertIn("not active", str(ctx.exception))
    
    def test_revoke_block_success(self):
        """Test successful block revocation"""
        block = core_transaction_api.create_block(
            account_id="ACC006",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=15000
        )
        revoked = core_transaction_api.revoke_block(block.block_id, "Customer request")
        self.assertEqual(revoked.status, BlockStatus.REVOKED.value)
    
    def test_revoke_already_debited_block(self):
        """Test revocation of debited block fails"""
        block = core_transaction_api.create_block(
            account_id="ACC007",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=20000
        )
        core_transaction_api.execute_debit(block.block_id)
        with self.assertRaises(ValueError) as ctx:
            core_transaction_api.revoke_block(block.block_id)
        self.assertIn("already debited", str(ctx.exception))
    
    def test_get_active_reserves(self):
        """Test getting active reserves"""
        core_transaction_api.create_block(
            account_id="ACC008",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=10000
        )
        core_transaction_api.create_block(
            account_id="ACC008",
            payer_vpa="payer@upi",
            payee_vpa="payee2@upi",
            amount=20000
        )
        reserves = core_transaction_api.get_active_reserves("ACC008")
        self.assertEqual(len(reserves), 2)


# Test Fraud Detection
class TestFraudDetection(unittest.TestCase):
    """Test fraud detection integration"""
    
    def test_risk_score_calculation(self):
        """Test risk score calculation"""
        data = {
            "account_id": "ACC001",
            "amount": 50000,
            "purpose_code": "P0901",
            "device_binding_method": "OTP",
            "account_age_days": 30
        }
        score = fraud_detection.calculate_risk_score(data)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
    
    def test_high_amount_rule(self):
        """Test high amount triggers higher risk"""
        low_amount_data = {"amount": 10000, "account_id": "ACC001"}
        high_amount_data = {"amount": 300000, "account_id": "ACC001"}
        
        low_score = fraud_detection.calculate_risk_score(low_amount_data)
        high_score = fraud_detection.calculate_risk_score(high_amount_data)
        
        self.assertGreater(high_score, low_score)
    
    def test_velocity_rule(self):
        """Test transaction velocity rule"""
        # Create multiple blocks for same account
        for i in range(6):
            core_transaction_api.create_block(
                account_id="ACC_VELOCITY",
                payer_vpa=f"payer{i}@upi",
                payee_vpa="payee@upi",
                amount=5000
            )
        
        data = {"account_id": "ACC_VELOCITY", "amount": 5000}
        score = fraud_detection.calculate_risk_score(data)
        self.assertGreater(score, 0)
    
    def test_fraud_validation_pass(self):
        """Test fraud validation passes for normal transaction"""
        data = {
            "account_id": "ACC001",
            "amount": 10000,
            "purpose_code": "P0901",
            "device_binding_method": "Biometric",
            "account_age_days": 100
        }
        is_valid, score, reason = fraud_detection.validate_transaction(data)
        self.assertTrue(is_valid)
    
    def test_fraud_validation_fail(self):
        """Test fraud validation fails for high risk"""
        data = {
            "account_id": "ACC001",
            "amount": 500000,
            "purpose_code": "STK",
            "device_binding_method": "OTP",
            "account_age_days": 2
        }
        is_valid, score, reason = fraud_detection.validate_transaction(data)
        self.assertFalse(is_valid)


# Test Notification Engine
class TestNotificationEngine(unittest.TestCase):
    """Test customer notification engine"""
    
    def test_send_sms(self):
        """Test SMS notification"""
        result = notification_engine.send_sms("9999999999", "Test message")
        self.assertTrue(result)
    
    def test_send_push(self):
        """Test push notification"""
        result = notification_engine.send_push("device_token", "Title", "Message")
        self.assertTrue(result)
    
    def test_notification_on_block_creation(self):
        """Test notification sent on block creation"""
        block = BlockRecord(
            block_id="TEST001",
            account_id="ACC001",
            payer_vpa="test@upi",
            payee_vpa="merchant@upi",
            amount=10000
        )
        notification = notification_engine.send_notification(
            recipient="test@upi",
            event=NotificationEvent.BLOCK_CREATED,
            block=block
        )
        self.assertEqual(notification.event, NotificationEvent.BLOCK_CREATED.value)
    
    def test_webhook_registration(self):
        """Test webhook callback registration"""
        callback_called = []
        
        def callback(notification):
            callback_called.append(notification)
        
        notification_engine.register_webhook(NotificationEvent.BLOCK_CREATED, callback)
        
        block = BlockRecord(
            block_id="TEST002",
            account_id="ACC001",
            payer_vpa="test@upi",
            payee_vpa="merchant@upi",
            amount=10000
        )
        notification_engine.send_notification(
            recipient="test@upi",
            event=NotificationEvent.BLOCK_CREATED,
            block=block
        )
        
        self.assertEqual(len(callback_called), 1)


# Test DSC Validation
class TestDSCValidation(unittest.TestCase):
    """Test DSC validation middleware"""
    
    def test_valid_signature(self):
        """Test valid DSC signature"""
        is_valid, reason = dsc_validation.validate_dsc(
            "test payload",
            "TEST_signature123",
            "test_key"
        )
        self.assertTrue(is_valid)
    
    def test_missing_signature(self):
        """Test missing signature rejected"""
        is_valid, reason = dsc_validation.validate_dsc(
            "test payload",
            "",
            "test_key"
        )
        self.assertFalse(is_valid)
        self.assertIn("required", reason)
    
    def test_invalid_signature_format(self):
        """Test invalid signature format"""
        is_valid, reason = dsc_validation.validate_dsc(
            "test payload",
            "short",
            "test_key"
        )
        self.assertFalse(is_valid)


# Test Merchant Webhooks
class TestMerchantWebhooks(unittest.TestCase):
    """Test merchant webhook system"""
    
    def setUp(self):
        merchant_webhooks._webhooks.clear()
        merchant_webhooks._webhook_events.clear()
    
    def test_register_webhook(self):
        """Test webhook registration"""
        merchant_webhooks.register_webhook("MERCH001", "https://merchant.com/webhook")
        self.assertIn("MERCH001", merchant_webhooks._webhooks)
    
    def test_trigger_webhook(self):
        """Test webhook triggering"""
        merchant_webhooks.register_webhook("MERCH002", "https://merchant.com/webhook")
        
        block = BlockRecord(
            block_id="TEST_BLOCK",
            account_id="ACC001",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=10000,
            metadata={"merchant_id": "MERCH002"}
        )
        
        result = merchant_webhooks.trigger_webhook("DEBIT", block)
        self.assertTrue(result)
        self.assertTrue(block.merchant_webhook_sent)
    
    def test_trigger_webhook_no_merchant(self):
        """Test webhook fails without registered merchant"""
        block = BlockRecord(
            block_id="TEST_BLOCK2",
            account_id="ACC001",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=10000,
            metadata={"merchant_id": "UNKNOWN"}
        )
        
        result = merchant_webhooks.trigger_webhook("DEBIT", block)
        self.assertFalse(result)


# Test MIS Reports
class TestMISReports(unittest.TestCase):
    """Test MIS report generation"""
    
    def setUp(self):
        mis_reports._reports.clear()
        block_registry._blocks.clear()
        block_registry._account_blocks.clear()
    
    def test_generate_empty_report(self):
        """Test generating report with no blocks"""
        report = mis_reports.generate_daily_report()
        self.assertEqual(report.total_blocks, 0)
        self.assertEqual(report.total_amount, 0)
    
    def test_generate_report_with_blocks(self):
        """Test generating report with blocks"""
        core_transaction_api.create_block(
            account_id="ACC001",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=10000
        )
        
        report = mis_reports.generate_daily_report()
        self.assertEqual(report.total_blocks, 1)
        self.assertEqual(report.total_amount, 10000)
    
    def test_submit_to_npci(self):
        """Test NPCI submission"""
        report = mis_reports.generate_daily_report()
        result = mis_reports.submit_to_npci(report)
        self.assertTrue(result)


# Test Block Expiry Scheduler
class TestBlockExpiryScheduler(unittest.TestCase):
    """Test block expiry scheduler"""
    
    def setUp(self):
        block_registry._blocks.clear()
        block_registry._account_blocks.clear()
    
    def test_expiry_notification(self):
        """Test T-3 day expiry notification"""
        # Create block expiring in 2 days
        block = BlockRecord(
            block_id="EXPIRE001",
            account_id="ACC001",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=10000,
            expiry_at=datetime.now() + timedelta(days=2),
            status=BlockStatus.ACTIVE.value
        )
        block_registry.create_block(block)
        
        expiring = block_registry.get_blocks_for_expiry(days_ahead=3)
        self.assertEqual(len(expiring), 1)
        self.assertEqual(expiring[0].block_id, "EXPIRE001")
    
    def test_expired_blocks(self):
        """Test expired blocks detection"""
        block = BlockRecord(
            block_id="EXPIRE002",
            account_id="ACC002",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=10000,
            expiry_at=datetime.now() - timedelta(days=1),
            status=BlockStatus.ACTIVE.value
        )
        block_registry.create_block(block)
        
        expired = block_registry.get_expired_blocks()
        self.assertEqual(len(expired), 1)


# Test Block Registry
class TestBlockRegistry(unittest.TestCase):
    """Test block registry database"""
    
    def setUp(self):
        block_registry._blocks.clear()
        block_registry._account_blocks.clear()
    
    def test_create_and_get_block(self):
        """Test creating and retrieving block"""
        block = BlockRecord(
            block_id="REG001",
            account_id="ACC001",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=50000
        )
        created = block_registry.create_block(block)
        retrieved = block_registry.get_block("REG001")
        
        self.assertEqual(created.block_id, retrieved.block_id)
        self.assertEqual(retrieved.amount, 50000)
    
    def test_update_block_status(self):
        """Test updating block status"""
        block = BlockRecord(
            block_id="REG002",
            account_id="ACC001",
            payer_vpa="payer@upi",
            payee_vpa="payee@upi",
            amount=30000
        )
        block_registry.create_block(block)
        
        updated = block_registry.update_block_status("REG002", BlockStatus.DEBITED.value)
        self.assertEqual(updated.status, BlockStatus.DEBITED.value)
    
    def test_get_blocks_by_account(self):
        """Test getting blocks by account"""
        for i in range(3):
            block = BlockRecord(
                block_id=f"REG_ACC_{i}",
                account_id="ACC_MULTI",
                payer_vpa="payer@upi",
                payee_vpa="payee@upi",
                amount=10000
            )
            block_registry.create_block(block)
        
        blocks = block_registry.get_blocks_by_account("ACC_MULTI")
        self.assertEqual(len(blocks), 3)


# Keep existing tests
class TestGeoElement(unittest.TestCase):
    def test_geo_element_inclusion(self):
        credit_account(account_id="ACC123", amount=50000, purpose="Test purpose", mcc=ALLOWED_MCC,
                       device_binding_method="OTP")
        self.assertIn('geo_location', _SWITCH_HIGH_VALUE_STORE)

    def test_geo_values_fixed(self):
        captured = io.StringIO()
        with redirect_stdout(captured):
            credit_account(account_id="ACC123", amount=30000, purpose="Geo test", mcc=ALLOWED_MCC,
                           device_binding_method="OTP")
        output = captured.getvalue()
        self.assertIn("<Lat>12.97</Lat>", output)
        self.assertIn("<Long>77.59</Long>", output)

    def test_risk_score_calculation(self):
        credit_account(account_id="ACC123", amount=30000, purpose="Geo test", mcc=ALLOWED_MCC,
                       device_binding_method="OTP")
        self.assertEqual(_SWITCH_HIGH_VALUE_STORE.get('risk_score'), '10')
        credit_account(
            account_id="ACC124",
            amount=30000,
            purpose="Geo test",
            payer_address="risky address",
            mcc=ALLOWED_MCC,
            device_binding_method="OTP",
        )
        self.assertEqual(_SWITCH_HIGH_VALUE_STORE.get('risk_score'), '90')

    def test_rejection_when_risk_score_above_80(self):
        with self.assertRaises(RiskRejectionError) as ctx:
            credit_account(
                account_id="ACC125",
                amount=20000,
                purpose="High risk",
                payer_address="risky location",
                mcc=ALLOWED_MCC,
                device_binding_method="OTP",
            )
        self.assertIn("Risk score 90 exceeds threshold", str(ctx.exception))

    def test_switch_parses_geo_and_risk(self):
        credit_account(
            account_id="ACC126",
            amount=30000,
            purpose="Parsing test",
            payer_address="safe address",
            mcc=ALLOWED_MCC,
            device_binding_method="OTP",
        )
        self.assertIn('geo_location', _SWITCH_HIGH_VALUE_STORE)
        self.assertIn('risk_score', _SWITCH_HIGH_VALUE_STORE)
        self.assertEqual(_SWITCH_HIGH_VALUE_STORE['risk_score'], '10')


class TestHighValueFlag(unittest.TestCase):
    def test_high_value_flag_set_when_amount_exceeds_threshold(self):
        credit_account(account_id="ACC127", amount=150_000, purpose="High value test", mcc=ALLOWED_MCC,
                       device_binding_method="OTP")
        self.assertTrue(_SWITCH_HIGH_VALUE_STORE.get("ACC127"))
        self.assertTrue(_SWITCH_HIGH_VALUE_STORE.get('high_value'))

    def test_warning_logged_when_high_value(self):
        with self.assertLogs(level='WARNING') as cm:
            credit_account(account_id="ACC128", amount=200_000, purpose="Very high value", mcc=ALLOWED_MCC,
                           device_binding_method="OTP")
        self.assertIn("[Switch] Warning: HighValue transaction detected", cm.output[0])

    def test_amount_exceeds_new_limit_raises_error(self):
        with self.assertRaises(RiskRejectionError):
            credit_account(account_id="ACC129", amount=700_001, purpose="Exceeds limit", mcc=ALLOWED_MCC,
                           device_binding_method="OTP")

    def test_amount_exceeds_previous_limit_logs_warning(self):
        with self.assertLogs(level='WARNING') as cm:
            credit_account(account_id="ACC130", amount=600_000, purpose="Above old limit", mcc=ALLOWED_MCC,
                           device_binding_method="OTP")
        self.assertTrue(any("exceeds previous limit" in msg for msg in cm.output))

    def test_approach_ceiling_logging(self):
        with self.assertLogs(level='WARNING') as cm:
            credit_account(account_id="ACC1310", amount=640_000, purpose="Approach ceiling", mcc=ALLOWED_MCC,
                           device_binding_method="OTP")
        self.assertTrue(any("approaches maximum limit" in msg for msg in cm.output))


class TestAmountLimits(unittest.TestCase):
    def test_amount_at_previous_limit_no_warning(self):
        # Exactly at previous limit should not trigger warning
        with self.assertLogs(level='WARNING') as cm:
            credit_account(account_id="ACC140", amount=500_000, purpose="At previous limit", mcc=ALLOWED_MCC,
                           device_binding_method="OTP")
        self.assertFalse(any("exceeds previous limit" in msg for msg in cm.output))

    def test_amount_just_above_previous_limit_logs_warning(self):
        with self.assertLogs(level='WARNING') as cm:
            credit_account(account_id="ACC141", amount=500_001, purpose="Just above previous limit", mcc=ALLOWED_MCC,
                           device_binding_method="OTP")
        self.assertTrue(any("exceeds previous limit" in msg for msg in cm.output))

    def test_amount_at_new_limit_accepted(self):
        # Should be accepted without error
        credit_account(account_id="ACC142", amount=700_000, purpose="At new limit", mcc=ALLOWED_MCC,
                       device_binding_method="OTP")
        self.assertEqual(_SWITCH_HIGH_VALUE_STORE.get('high_value'), True)  # high_value flag still true (>100k)

    def test_amount_exceeds_new_limit_rejected(self):
        with self.assertRaises(RiskRejectionError):
            credit_account(account_id="ACC143", amount=700_001, purpose="Exceeds new limit", mcc=ALLOWED_MCC,
                           device_binding_method="OTP")


class TestMCCHandling(unittest.TestCase):
    def test_mcc_propagation(self):
        credit_account(account_id="ACC200", amount=30000, purpose="Test MCC", mcc=ALLOWED_MCC,
                       device_binding_method="OTP")
        self.assertEqual(_SWITCH_HIGH_VALUE_STORE.get('mcc'), ALLOWED_MCC)

    def test_invalid_mcc_rejection(self):
        with self.assertRaises(RiskRejectionError) as ctx:
            credit_account(account_id="ACC201", amount=30000, purpose="Bad MCC", mcc="9999",
                           device_binding_method="OTP")
        self.assertIn("MCC 9999 is not allowed", str(ctx.exception))

    def test_missing_mcc_rejection(self):
        with self.assertRaises(RiskRejectionError) as ctx:
            credit_account(account_id="ACC202", amount=30000, purpose="No MCC",
                           device_binding_method="OTP")
        self.assertIn("MCC element missing", str(ctx.exception))


class TestDeviceOSValidation(unittest.TestCase):
    def test_accept_known_os(self):
        xml = '''<ReqPay>
            <Account>ACC131</Account>
            <Amount>1000</Amount>
            <Purpose>Test</Purpose>
        </ReqPay>'''
        root = ET.fromstring(xml)
        device = ET.SubElement(root, 'Device')
        os_el = ET.SubElement(device, 'OS')
        os_el.text = 'Android'
        xml_with_os = ET.tostring(root, encoding='unicode')
        _extract_os_from_xml(xml_with_os)
        self.assertEqual(_SWITCH_HIGH_VALUE_STORE.get('device_os'), 'Android')

    def test_reject_unknown_os(self):
        xml = '''<ReqPay>
            <Account>ACC132</Account>
            <Amount>1000</Amount>
            <Purpose>Test</Purpose>
        </ReqPay>'''
        root = ET.fromstring(xml)
        device = ET.SubElement(root, 'Device')
        os_el = ET.SubElement(device, 'OS')
        os_el.text = 'Windows'
        xml_with_os = ET.tostring(root, encoding='unicode')
        with self.assertRaises(RiskRejectionError) as ctx:
            _extract_os_from_xml(xml_with_os)
        self.assertIn("Unknown OS 'Windows'", str(ctx.exception))

    def test_reject_missing_device_os(self):
        xml = '''<ReqPay>
            <Account>ACC133</Account>
            <Amount>1000</Amount>
            <Purpose>Test</Purpose>
        </ReqPay>'''
        with self.assertRaises(RiskRejectionError) as ctx:
            _extract_os_from_xml(xml)
        self.assertIn("Device/OS element missing", str(ctx.exception))


class TestLiteFlow(unittest.TestCase):
    def test_lite_elements_added(self):
        credit_account(
            account_id="ACC134",
            amount=25000,
            purpose="Lite purchase",
            lite=True,
            mcc=ALLOWED_MCC,
            device_binding_method="OTP",
        )
        self.assertIn('lite_tx_id', _SWITCH_LITE_STORE)
        self.assertIn('lite', _SWITCH_HIGH_VALUE_STORE)

    def test_lite_validation_successful(self):
        credit_account(
            account_id="ACC135",
            amount=15000,
            purpose="Lite grocery",
            lite=True,
            mcc=ALLOWED_MCC,
            device_binding_method="OTP",
        )
        self.assertIn('lite_tx_id', _SWITCH_LITE_STORE)

    def test_lite_rejection_on_missing_elements(self):
        xml = '''<ReqPay>
            <Account>ACC136</Account>
            <Amount>1000</Amount>
            <Purpose>Test</Purpose>
        </ReqPay>'''
        root = ET.fromstring(xml)
        for elem in list(root):
            root.remove(elem)
        ET.SubElement(root, 'Account').text = "ACC136"
        ET.SubElement(root, 'Amount').text = "1000"
        ET.SubElement(root, 'Purpose').text = "Test"
        xml_malformed = ET.tostring(root, encoding='unicode')
        with self.assertRaises(RiskRejectionError) as ctx:
            _validate_lite_schema(xml_malformed)
        self.assertIn("Lite request missing required", str(ctx.exception))

    def test_lite_flow_integration(self):
        credit_account(
            account_id="ACC137",
            amount=30000,
            purpose="Lite grocery",
            lite=True,
            payer_address="safe address",
            mcc=ALLOWED_MCC,
            device_binding_method="OTP",
        )
        self.assertIn('geo_location', _SWITCH_HIGH_VALUE_STORE)
        self.assertIn('lite_tx_id', _SWITCH_LITE_STORE)
        self.assertEqual(_SWITCH_HIGH_VALUE_STORE['risk_score'], '10')


class TestRecurringMandate(unittest.TestCase):
    def setUp(self):
        _MANDATE_STORE.clear()

    def test_valid_active_mandate(self):
        _MANDATE_STORE['MANDATE123'] = 'ACTIVE'
        credit_account(
            account_id="ACC138",
            amount=25000,
            purpose="Recurring grocery",
            recurring=True,
            mcc=ALLOWED_MCC,
            device_binding_method="OTP",
        )
        self.assertIn('recurring_mandate_status', _SWITCH_HIGH_VALUE_STORE)
        self.assertEqual(_SWITCH_HIGH_VALUE_STORE['recurring_mandate_status'], 'ACTIVE')

    def test_inactive_mandate_rejected(self):
        _MANDATE_STORE['MANDATE124'] = 'INACTIVE'
        with self.assertRaises(RiskRejectionError) as ctx:
            credit_account(
                account_id="ACC139",
                amount=25000,
                purpose="Recurring test",
                recurring=True,
                mcc=ALLOWED_MCC,
                device_binding_method="OTP",
            )
        self.assertIn("Mandate MANDATE124 status is INACTIVE, not ACTIVE", str(ctx.exception))

    def test_missing_mandate_id_rejected(self):
        xml = '''<ReqPay>
            <Account>ACC140</Account>
            <Amount>1000</Amount>
            <Purpose>Test</Purpose>
        </ReqPay>'''
        root = ET.fromstring(xml)
        recurring_elem = ET.SubElement(root, 'RecurringPay')
        xml_missing = ET.tostring(root, encoding='unicode')
        with self.assertRaises(RiskRejectionError) as ctx:
            _process_recurring_pay(xml_missing)
        self.assertIn("Missing MandateId in RecurringPay", str(ctx.exception))


class TestRecurringMandateIntegration(unittest.TestCase):
    def setUp(self):
        _MANDATE_STORE.clear()

    def test_active_mandate_allows_debit(self):
        _MANDATE_STORE['MANDATE_ACT'] = 'ACTIVE'
        credit_account(
            account_id="ACC141",
            amount=25000,
            purpose="Recurring grocery",
            recurring=True,
            recurring_mandate_id='MANDATE_ACT',
            mcc=ALLOWED_MCC,
            device_binding_method="OTP",
        )
        self.assertIn('Debit', _SWITCH_HIGH_VALUE_STORE.get('recurring_mandate_status', ''))

    def test_expired_mandate_is_rejected(self):
        _MANDATE_STORE['MANDATE_EXP'] = 'EXPIRED'
        with self.assertRaises(RiskRejectionError) as ctx:
            credit_account(
                account_id="ACC142",
                amount=25000,
                purpose="Recurring test",
                recurring=True,
                recurring_mandate_id='MANDATE_EXP',
                mcc=ALLOWED_MCC,
                device_binding_method="OTP",
            )
        self.assertIn("Mandate MANDATE_EXP status is EXPIRED, not ACTIVE", str(ctx.exception))

    def test_missing_mandate_is_rejected(self):
        with self.assertRaises(RiskRejectionError) as ctx:
            credit_account(
                account_id="ACC143",
                amount=25000,
                purpose="Recurring test",
                recurring=True,
                mcc=ALLOWED_MCC,
                device_binding_method="OTP",
            )
        self.assertIn("Missing MandateId in RecurringPay", str(ctx.exception))


class TestPurposeCode(unittest.TestCase):
    def test_purpose_code_p0901_allowed_only_for_pay(self):
        credit_account(
            account_id="ACC144",
            amount=50000,
            purpose="Education fee payment",
            purpose_code="P0901",
            transaction_type="PAY",
            mcc=ALLOWED_MCC,
            device_binding_method="OTP",
        )
        self.assertEqual(_SWITCH_HIGH_VALUE_STORE.get('purpose_code'), 'P0901')

        with self.assertRaises(RiskRejectionError) as ctx:
            credit_account(
                account_id="ACC145",
                amount=50000,
                purpose="Education fee",
                purpose_code="P0901",
                transaction_type="OTHER",
                mcc=ALLOWED_MCC,
                device_binding_method="OTP",
            )
        self.assertIn("Purpose code P0901 is only allowed for PAY transactions", str(ctx.exception))

    def test_p0901_amount_limit_enforcement(self):
        credit_account(
            account_id="ACC146",
            amount=500_000,
            purpose="Education fee",
            purpose_code="P0901",
            transaction_type="PAY",
            mcc=ALLOWED_MCC,
            device_binding_method="OTP",
        )
        self.assertTrue(True)

        with self.assertRaises(RiskRejectionError) as ctx:
            credit_account(
                account_id="ACC147",
                amount=600_000,
                purpose="Education fee",
                purpose_code="P0901",
                transaction_type="PAY",
                mcc=ALLOWED_MCC,
                device_binding_method="OTP",
            )
        self.assertIn("exceeds limit of", str(ctx.exception))

    def test_psp_handler_configuration_includes_p0901(self):
        self.assertIn("P0901", _PSP_HANDLERS)
        self.assertEqual(_PSP_HANDLERS["P0901"], "education_fee_handler")

    def test_stk_purpose_code_full_flow(self):
        credit_account(
            account_id="ACC200",
            amount=400_000,
            purpose="STK transaction test",
            purpose_code="STK",
            transaction_type="PAY",
            mcc=ALLOWED_MCC,
            device_binding_method="OTP",
        )
        self.assertEqual(_SWITCH_HIGH_VALUE_STORE.get('purpose_code'), 'STK')
        with self.assertRaises(RiskRejectionError):
            credit_account(
                account_id="ACC201",
                amount=600_000,
                purpose="STK transaction test",
                purpose_code="STK",
                transaction_type="PAY",
                mcc=ALLOWED_MCC,
                device_binding_method="OTP",
            )
        with self.assertRaises(RiskRejectionError):
            credit_account(
                account_id="ACC202",
                amount=100_000,
                purpose="STK transaction test",
                purpose_code="STK",
                transaction_type="REFUND",
                mcc=ALLOWED_MCC,
                device_binding_method="OTP",
            )

    def test_stk_mkt_purpose_code_full_flow(self):
        credit_account(
            account_id="ACC300",
            amount=400_000,
            purpose="Stock market purchase",
            purpose_code="STK_MMT",
            transaction_type="PAY",
            mcc=ALLOWED_MCC,
            device_binding_method="OTP",
        )
        self.assertEqual(_SWITCH_HIGH_VALUE_STORE.get('purpose_code'), 'STK_MMT')
        with self.assertRaises(RiskRejectionError):
            credit_account(
                account_id="ACC301",
                amount=600_000,
                purpose="Stock...",
                purpose_code="STK_MMT",
                transaction_type="PAY",
                mcc=ALLOWED_MCC,
                device_binding_method="OTP",
            )


# ---------------------------------------------------------------------------
# E2E Integration Tests
# ---------------------------------------------------------------------------
class TestE2EIntegration(unittest.TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        block_registry._blocks.clear()
        block_registry._account_blocks.clear()
        _MANDATE_STORE.clear()
    
    def test_full_block_lifecycle(self):
        """Test complete block lifecycle: create -> debit -> verify"""
        # Create block
        block = core_transaction_api.create_block(
            account_id="E2E001",
            payer_vpa="payer@upi",
            payee_vpa="merchant@upi",
            amount=50000,
            purpose_code="P0901"
        )
        self.assertEqual(block.status, BlockStatus.ACTIVE.value)
        
        # Execute debit
        debited = core_transaction_api.execute_debit(block.block_id)
        self.assertEqual(debited.status, BlockStatus.DEBITED.value)
        self.assertIsNotNone(debited.debited_at)
    
    def test_block_revocation_flow(self):
        """Test block revocation flow"""
        block = core_transaction_api.create_block(
            account_id="E2E002",
            payer_vpa="payer@upi",
            payee_vpa="merchant@upi",
            amount=25000
        )
        
        # Revoke block
        revoked = core_transaction_api.revoke_block(block.block_id, "Customer requested")
        self.assertEqual(revoked.status, BlockStatus.REVOKED.value)
        self.assertIsNotNone(revoked.revoked_at)
    
    def test_fraud_blocks_transaction(self):
        """Test fraud detection integration with block creation"""
        # This should fail due to high fraud risk
        with self.assertRaises(ValueError):
            core_transaction_api.create_block(
                account_id="E2E003",
                payer_vpa="payer@upi",
                payee_vpa="merchant@upi",
                amount=500000,  # Very high amount
                metadata={"account_age_days": 1}  # New account
            )
    
    def test_dsc_validated_block(self):
        """Test DSC validation in block creation"""
        block = core_transaction_api.create_block(
            account_id="E2E004",
            payer_vpa="payer@upi",
            payee_vpa="merchant@upi",
            amount=10000,
            dsc_signature="TEST_valid_signature",
            dsc_public_key_id="production_key"
        )
        self.assertTrue(block.dsc_validated)
    
    def test_mis_report_generation(self):
        """Test MIS report with multiple blocks"""
        # Create several blocks
        for i in range(5):
            core_transaction_api.create_block(
                account_id=f"E2E_MIS_{i}",
                payer_vpa="payer@upi",
                payee_vpa="merchant@upi",
                amount=10000 * (i + 1)
            )
        
        # Generate report
        report = mis_reports.generate_daily_report()
        self.assertEqual(report.total_blocks, 5)
        self.assertEqual(report.total_amount, 150000)
    
    def test_merchant_webhook_triggered(self):
        """Test merchant webhook is triggered on debit"""
        merchant_webhooks.register_webhook("E2E_MERCH", "https://merchant.com/webhook")
        
        block = core_transaction_api.create_block(
            account_id="E2E005",
            payer_vpa="payer@upi",
            payee_vpa="merchant@upi",
            amount=15000,
            metadata={"merchant_id": "E2E_MERCH"}
        )
        
        core_transaction_api.execute_debit(block.block_id)
        
        # Check webhook was triggered
        events = merchant_webhooks.get_webhook_events("E2E_MERCH")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "DEBIT")


if __name__ == "__main__":
    # Start expiry scheduler for testing
    expiry_scheduler.start()
    unittest.main()