import logging
import re
import unittest
import threading
import time
import json
import hashlib
import hmac
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET
from flask import Flask, jsonify, request, Response
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue
import uuid

# ----------------------------------------------------------------------
# Flask App
# ----------------------------------------------------------------------
app = Flask(__name__)

# ----------------------------------------------------------------------
# Database Schema (Block Registry) - TSD Section 3.1
# ----------------------------------------------------------------------
class BlockStatus(Enum):
    CREATED = "CREATED"
    DEBITED = "DEBITED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"

@dataclass
class BlockRecord:
    block_id: str
    payer_account_id: str
    payee_account_id: str
    amount: Decimal
    purpose_code: str
    status: BlockStatus
    created_at: datetime
    expires_at: datetime
    debited_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    risk_score: Optional[int] = None
    transaction_ref: Optional[str] = None
    dsc_validated: bool = False
    dsc_signature: Optional[str] = None

class BlockRegistry:
    """In-memory block registry database (would be replaced with actual DB in production)."""
    _blocks: Dict[str, BlockRecord] = {}
    _lock = threading.RLock()
    
    @classmethod
    def create_block(cls, block: BlockRecord) -> BlockRecord:
        with cls._lock:
            cls._blocks[block.block_id] = block
        return block
    
    @classmethod
    def get_block(cls, block_id: str) -> Optional[BlockRecord]:
        with cls._lock:
            return cls._blocks.get(block_id)
    
    @classmethod
    def update_block_status(cls, block_id: str, status: BlockStatus, 
                           transaction_ref: Optional[str] = None) -> Optional[BlockRecord]:
        with cls._lock:
            block = cls._blocks.get(block_id)
            if block:
                block.status = status
                if status == BlockStatus.DEBITED:
                    block.debited_at = datetime.utcnow()
                elif status == BlockStatus.REVOKED:
                    block.revoked_at = datetime.utcnow()
                if transaction_ref:
                    block.transaction_ref = transaction_ref
            return block
    
    @classmethod
    def get_blocks_by_status(cls, status: BlockStatus) -> List[BlockRecord]:
        with cls._lock:
            return [b for b in cls._blocks.values() if b.status == status]
    
    @classmethod
    def get_expiring_blocks(cls, days: int) -> List[BlockRecord]:
        """Get blocks expiring within given days."""
        with cls._lock:
            threshold = datetime.utcnow() + timedelta(days=days)
            return [b for b in cls._blocks.values() 
                    if b.status == BlockStatus.CREATED and b.expires_at <= threshold]
    
    @classmethod
    def get_all_blocks(cls) -> List[BlockRecord]:
        with cls._lock:
            return list(cls._blocks.values())

# ----------------------------------------------------------------------
# Fraud Detection Integration - TSD Section 5.3
# ----------------------------------------------------------------------
class FraudDetectionService:
    """Fraud detection integration with < 500ms risk scoring."""
    
    @staticmethod
    def calculate_risk_score(
        payer_account_id: str,
        payee_account_id: str,
        amount: Decimal,
        purpose_code: str,
        device_binding_method: str,
        payer_address: Optional[str] = None
    ) -> int:
        """
        Calculate risk score in < 500ms.
        Returns score 0-100.
        """
        start_time = time.time()
        
        score = 10  # Base score
        
        # Amount-based risk
        if amount > Decimal("100000"):
            score += 30
        elif amount > Decimal("50000"):
            score += 15
        
        # Purpose code risk
        high_risk_purposes = {"STK_MKT", "STOCK_MARKET", "IPO"}
        if purpose_code in high_risk_purposes:
            score += 25
        
        # Device binding risk
        if device_binding_method == "OTP":
            score += 10
        elif device_binding_method == "PIN":
            score += 5
        # Biometric is lowest risk (0 added)
        
        # Address-based risk (legacy pattern)
        if payer_address and "risk" in payer_address.lower():
            score += 30
        
        # Same account risk
        if payer_account_id == payee_account_id:
            score += 20
        
        # Cap at 100
        score = min(score, 100)
        
        # Ensure < 500ms response time
        elapsed = (time.time() - start_time) * 1000
        if elapsed > 500:
            logging.warning(f"Fraud detection took {elapsed}ms, exceeding 500ms target")
        
        return score

# ----------------------------------------------------------------------
# Customer Notification Engine (SMS + Push)
# ----------------------------------------------------------------------
class NotificationType(Enum):
    BLOCK_CREATED = "BLOCK_CREATED"
    BLOCK_DEBITED = "BLOCK_DEBITED"
    BLOCK_REVOKED = "BLOCK_REVOKED"
    BLOCK_EXPIRING_SOON = "BLOCK_EXPIRING_SOON"
    BLOCK_EXPIRED = "BLOCK_EXPIRED"

class NotificationChannel(Enum):
    SMS = "SMS"
    PUSH = "PUSH"
    EMAIL = "EMAIL"

@dataclass
class Notification:
    recipient: str
    notification_type: NotificationType
    channel: NotificationChannel
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    sent_at: Optional[datetime] = None
    status: str = "PENDING"

class NotificationEngine:
    """Customer notification engine for all lifecycle events."""
    
    _notification_queue: Queue = Queue()
    _notification_history: List[Notification] = []
    _lock = threading.Lock()
    
    @classmethod
    def send_notification(cls, notification: Notification) -> bool:
        """Send notification via appropriate channel."""
        try:
            # In production, integrate with SMS/Push providers
            if notification.channel == NotificationChannel.SMS:
                logging.info(f"[SMS] To: {notification.recipient}, Message: {notification.message}")
            elif notification.channel == NotificationChannel.PUSH:
                logging.info(f"[PUSH] To: {notification.recipient}, Message: {notification.message}")
            elif notification.channel == NotificationChannel.EMAIL:
                logging.info(f"[EMAIL] To: {notification.recipient}, Message: {notification.message}")
            
            notification.sent_at = datetime.utcnow()
            notification.status = "SENT"
            
            with cls._lock:
                cls._notification_history.append(notification)
            
            return True
        except Exception as e:
            logging.error(f"Failed to send notification: {e}")
            notification.status = "FAILED"
            return False
    
    @classmethod
    def notify_block_created(cls, block: BlockRecord) -> None:
        """Notify customer when block is created."""
        msg = f"Block created: {block.block_id}, Amount: {block.amount} INR, Expires: {block.expires_at}"
        cls.send_notification(Notification(
            recipient=block.payer_account_id,
            notification_type=NotificationType.BLOCK_CREATED,
            channel=NotificationChannel.SMS,
            message=msg,
            metadata={"block_id": block.block_id, "amount": str(block.amount)}
        ))
        cls.send_notification(Notification(
            recipient=block.payer_account_id,
            notification_type=NotificationType.BLOCK_CREATED,
            channel=NotificationChannel.PUSH,
            message=msg,
            metadata={"block_id": block.block_id, "amount": str(block.amount)}
        ))
    
    @classmethod
    def notify_block_debited(cls, block: BlockRecord) -> None:
        """Notify customer when block is debited."""
        msg = f"Block debited: {block.block_id}, Amount: {block.amount} INR, Ref: {block.transaction_ref}"
        cls.send_notification(Notification(
            recipient=block.payer_account_id,
            notification_type=NotificationType.BLOCK_DEBITED,
            channel=NotificationChannel.SMS,
            message=msg,
            metadata={"block_id": block.block_id, "amount": str(block.amount)}
        ))
        cls.send_notification(Notification(
            recipient=block.payee_account_id,
            notification_type=NotificationType.BLOCK_DEBITED,
            channel=NotificationChannel.PUSH,
            message=msg,
            metadata={"block_id": block.block_id, "amount": str(block.amount)}
        ))
    
    @classmethod
    def notify_block_revoked(cls, block: BlockRecord) -> None:
        """Notify customer when block is revoked."""
        msg = f"Block revoked: {block.block_id}, Amount: {block.amount} INR"
        cls.send_notification(Notification(
            recipient=block.payer_account_id,
            notification_type=NotificationType.BLOCK_REVOKED,
            channel=NotificationChannel.SMS,
            message=msg,
            metadata={"block_id": block.block_id, "amount": str(block.amount)}
        ))
    
    @classmethod
    def notify_block_expiring_soon(cls, block: BlockRecord, days_remaining: int) -> None:
        """Notify customer when block is expiring soon (T-3 days)."""
        msg = f"Block expiring in {days_remaining} days: {block.block_id}, Amount: {block.amount} INR"
        cls.send_notification(Notification(
            recipient=block.payer_account_id,
            notification_type=NotificationType.BLOCK_EXPIRING_SOON,
            channel=NotificationChannel.SMS,
            message=msg,
            metadata={"block_id": block.block_id, "days_remaining": days_remaining}
        ))
        cls.send_notification(Notification(
            recipient=block.payer_account_id,
            notification_type=NotificationType.BLOCK_EXPIRING_SOON,
            channel=NotificationChannel.PUSH,
            message=msg,
            metadata={"block_id": block.block_id, "days_remaining": days_remaining}
        ))
    
    @classmethod
    def notify_block_expired(cls, block: BlockRecord) -> None:
        """Notify customer when block has expired."""
        msg = f"Block expired: {block.block_id}, Amount: {block.amount} INR"
        cls.send_notification(Notification(
            recipient=block.payer_account_id,
            notification_type=NotificationType.BLOCK_EXPIRED,
            channel=NotificationChannel.SMS,
            message=msg,
            metadata={"block_id": block.block_id, "amount": str(block.amount)}
        ))
    
    @classmethod
    def get_notification_history(cls, recipient: Optional[str] = None) -> List[Notification]:
        with cls._lock:
            if recipient:
                return [n for n in cls._notification_history if n.recipient == recipient]
            return list(cls._notification_history)

# ----------------------------------------------------------------------
# DSC Validation Middleware
# ----------------------------------------------------------------------
class DSCValidator:
    """Digital Signature Certificate validation middleware."""
    
    # In production, would use actual certificate management
    _valid_certificates: Dict[str, str] = {}  # cert_id -> public_key
    
    @classmethod
    def register_certificate(cls, cert_id: str, public_key: str) -> None:
        cls._valid_certificates[cert_id] = public_key
    
    @classmethod
    def validate_signature(cls, data: str, signature: str, cert_id: str) -> bool:
        """Validate DSC signature for block creation requests."""
        if cert_id not in cls._valid_certificates:
            logging.warning(f"Certificate {cert_id} not registered")
            return False
        
        # In production, use proper cryptographic validation
        # This is a simplified implementation
        expected_signature = hmac.new(
            cls._valid_certificates[cert_id].encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    @classmethod
    def validate_block_creation_request(cls, block_data: str, cert_id: str, 
                                        signature: str) -> bool:
        """Validate DSC for block creation."""
        return cls.validate_signature(block_data, signature, cert_id)

# ----------------------------------------------------------------------
# Merchant Webhook System
# ----------------------------------------------------------------------
@dataclass
class WebhookEvent:
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    retry_count: int = 0
    status: str = "PENDING"

class MerchantWebhookSystem:
    """Merchant webhook system for debit and revocation events."""
    
    _webhooks: Dict[str, str] = {}  # merchant_id -> webhook_url
    _event_queue: Queue = Queue()
    _event_history: List[WebhookEvent] = []
    _lock = threading.Lock()
    
    @classmethod
    def register_webhook(cls, merchant_id: str, webhook_url: str) -> None:
        cls._webhooks[merchant_id] = webhook_url
    
    @classmethod
    def unregister_webhook(cls, merchant_id: str) -> None:
        cls._webhooks.pop(merchant_id, None)
    
    @classmethod
    def trigger_webhook(cls, merchant_id: str, event_type: str, 
                        payload: Dict[str, Any]) -> bool:
        """Trigger webhook for merchant."""
        webhook_url = cls._webhooks.get(merchant_id)
        if not webhook_url:
            logging.warning(f"No webhook registered for merchant {merchant_id}")
            return False
        
        event = WebhookEvent(
            event_type=event_type,
            payload=payload,
            timestamp=datetime.utcnow()
        )
        
        try:
            # In production, make HTTP request to webhook URL
            logging.info(f"[WEBHOOK] {event_type} to {merchant_id} at {webhook_url}")
            logging.info(f"[WEBHOOK] Payload: {json.dumps(payload)}")
            
            event.status = "SENT"
            with cls._lock:
                cls._event_history.append(event)
            return True
        except Exception as e:
            logging.error(f"Failed to trigger webhook: {e}")
            event.status = "FAILED"
            with cls._lock:
                cls._event_history.append(event)
            return False
    
    @classmethod
    def notify_debit_event(cls, block: BlockRecord, merchant_id: str) -> None:
        """Notify merchant of debit event."""
        payload = {
            "event": "BLOCK_DEBITED",
            "block_id": block.block_id,
            "payer_account_id": block.payer_account_id,
            "payee_account_id": block.payee_account_id,
            "amount": str(block.amount),
            "transaction_ref": block.transaction_ref,
            "timestamp": block.debited_at.isoformat() if block.debited_at else None
        }
        cls.trigger_webhook(merchant_id, "BLOCK_DEBITED", payload)
    
    @classmethod
    def notify_revocation_event(cls, block: BlockRecord, merchant_id: str) -> None:
        """Notify merchant of revocation event."""
        payload = {
            "event": "BLOCK_REVOKED",
            "block_id": block.block_id,
            "payer_account_id": block.payer_account_id,
            "payee_account_id": block.payee_account_id,
            "amount": str(block.amount),
            "timestamp": block.revoked_at.isoformat() if block.revoked_at else None
        }
        cls.trigger_webhook(merchant_id, "BLOCK_REVOKED", payload)
    
    @classmethod
    def get_event_history(cls, merchant_id: Optional[str] = None) -> List[WebhookEvent]:
        with cls._lock:
            if merchant_id:
                # Filter by merchant would require storing merchant_id in event
                return list(cls._event_history)
            return list(cls._event_history)

# ----------------------------------------------------------------------
# MIS Report Generation & NPCI Submission
# ----------------------------------------------------------------------
@dataclass
class MISReport:
    report_date: datetime
    total_blocks_created: int
    total_blocks_debited: int
    total_blocks_revoked: int
    total_blocks_expired: int
    total_amount_blocked: Decimal
    total_amount_debited: Decimal
    risk_score_distribution: Dict[int, int]
    purpose_code_distribution: Dict[str, int]

class MISReportGenerator:
    """Daily MIS report generation and NPCI submission job."""
    
    @classmethod
    def generate_daily_report(cls, report_date: datetime) -> MISReport:
        """Generate daily MIS report."""
        blocks = BlockRegistry.get_all_blocks()
        
        # Filter blocks for the report date
        day_start = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        daily_blocks = [b for b in blocks 
                       if day_start <= b.created_at < day_end]
        
        total_blocks_created = len(daily_blocks)
        total_blocks_debited = len([b for b in daily_blocks 
                                   if b.status == BlockStatus.DEBITED])
        total_blocks_revoked = len([b for b in daily_blocks 
                                    if b.status == BlockStatus.REVOKED])
        total_blocks_expired = len([b for b in daily_blocks 
                                   if b.status == BlockStatus.EXPIRED])
        
        total_amount_blocked = sum((b.amount for b in daily_blocks), Decimal("0"))
        total_amount_debited = sum((b.amount for b in daily_blocks 
                                   if b.status == BlockStatus.DEBITED), Decimal("0"))
        
        # Risk score distribution
        risk_score_dist = {}
        for b in daily_blocks:
            if b.risk_score is not None:
                bucket = (b.risk_score // 10) * 10
                risk_score_dist[bucket] = risk_score_dist.get(bucket, 0) + 1
        
        # Purpose code distribution
        purpose_code_dist = {}
        for b in daily_blocks:
            purpose_code_dist[b.purpose_code] = purpose_code_dist.get(b.purpose_code, 0) + 1
        
        return MISReport(
            report_date=report_date,
            total_blocks_created=total_blocks_created,
            total_blocks_debited=total_blocks_debited,
            total_blocks_revoked=total_blocks_revoked,
            total_blocks_expired=total_blocks_expired,
            total_amount_blocked=total_amount_blocked,
            total_amount_debited=total_amount_debited,
            risk_score_distribution=risk_score_dist,
            purpose_code_distribution=purpose_code_dist
        )
    
    @classmethod
    def generate_npc_submission_payload(cls, report: MISReport) -> Dict[str, Any]:
        """Generate NPCI submission payload."""
        return {
            "report_date": report.report_date.isoformat(),
            "summary": {
                "total_blocks_created": report.total_blocks_created,
                "total_blocks_debited": report.total_blocks_debited,
                "total_blocks_revoked": report.total_blocks_revoked,
                "total_blocks_expired": report.total_blocks_expired,
                "total_amount_blocked": str(report.total_amount_blocked),
                "total_amount_debited": str(report.total_amount_debited)
            },
            "risk_score_distribution": {str(k): v for k, v in report.risk_score_distribution.items()},
            "purpose_code_distribution": report.purpose_code_distribution,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    @classmethod
    def submit_to_npci(cls, report: MISReport) -> bool:
        """Submit report to NPCI (mock implementation)."""
        payload = cls.generate_npc_submission_payload(report)
        logging.info(f"[NPCI] Submitting daily report for {report.report_date.date()}")
        logging.info(f"[NPCI] Payload: {json.dumps(payload, indent=2)}")
        # In production, make actual API call to NPCI
        return True

# ----------------------------------------------------------------------
# Block Expiry Scheduler
# ----------------------------------------------------------------------
class BlockExpiryScheduler:
    """Block expiry scheduler with T-3 day and expiry notifications."""
    
    _scheduler_thread: Optional[threading.Thread] = None
    _running = False
    
    @classmethod
    def start(cls) -> None:
        """Start the expiry scheduler."""
        if cls._running:
            return
        
        cls._running = True
        cls._scheduler_thread = threading.Thread(target=cls._run_scheduler, daemon=True)
        cls._scheduler_thread.start()
        logging.info("Block expiry scheduler started")
    
    @classmethod
    def stop(cls) -> None:
        """Stop the expiry scheduler."""
        cls._running = False
        if cls._scheduler_thread:
            cls._scheduler_thread.join(timeout=5)
        logging.info("Block expiry scheduler stopped")
    
    @classmethod
    def _run_scheduler(cls) -> None:
        """Run scheduler loop."""
        while cls._running:
            try:
                cls._check_expiring_blocks()
                cls._check_expired_blocks()
            except Exception as e:
                logging.error(f"Scheduler error: {e}")
            
            # Check every hour
            time.sleep(3600)
    
    @classmethod
    def _check_expiring_blocks(cls) -> None:
        """Check for blocks expiring in T-3 days."""
        expiring_blocks = BlockRegistry.get_expiring_blocks(3)
        
        for block in expiring_blocks:
            days_remaining = (block.expires_at - datetime.utcnow()).days
            if days_remaining > 0:
                NotificationEngine.notify_block_expiring_soon(block, days_remaining)
                logging.info(f"Block {block.block_id} expiring in {days_remaining} days")
    
    @classmethod
    def _check_expired_blocks(cls) -> None:
        """Check for blocks that have expired."""
        now = datetime.utcnow()
        active_blocks = BlockRegistry.get_blocks_by_status(BlockStatus.CREATED)
        
        for block in active_blocks:
            if block.expires_at <= now:
                BlockRegistry.update_block_status(block.block_id, BlockStatus.EXPIRED)
                NotificationEngine.notify_block_expired(block)
                logging.info(f"Block {block.block_id} has expired")

# ----------------------------------------------------------------------
# Core Transaction API - TSD Section 2
# ----------------------------------------------------------------------
class CoreTransactionAPI:
    """Core transaction API for block creation, debit execution, and revocation."""
    
    @classmethod
    def create_block(
        cls,
        payer_account_id: str,
        payee_account_id: str,
        amount: Decimal,
        purpose_code: str,
        device_binding_method: str,
        payer_address: Optional[str] = None,
        dsc_cert_id: Optional[str] = None,
        dsc_signature: Optional[str] = None,
        expiry_days: int = 7
    ) -> BlockRecord:
        """Create a new block."""
        # Validate purpose code
        if purpose_code not in VALID_PURPOSE_CODES:
            raise ValueError(f"Unsupported purpose code '{purpose_code}'")
        
        # Validate amount against purpose code limit
        cfg = PURPOSE_CODE_CONFIG[purpose_code]
        if amount > cfg["max_amount"]:
            raise ValueError(
                f"PurposeCode {purpose_code} amount {amount} exceeds limit of {cfg['max_amount']}"
            )
        
        # Validate device binding method
        if device_binding_method not in ALLOWED_DEVICE_BINDING_METHODS:
            raise ValueError(
                f"DeviceBindingMethod '{device_binding_method}' is invalid"
            )
        
        # DSC validation if provided
        if dsc_cert_id and dsc_signature:
            block_data = f"{payer_account_id}:{payee_account_id}:{amount}:{purpose_code}"
            if not DSCValidator.validate_block_creation_request(block_data, dsc_cert_id, dsc_signature):
                raise ValueError("DSC validation failed")
        
        # Calculate risk score
        risk_score = FraudDetectionService.calculate_risk_score(
            payer_account_id=payer_account_id,
            payee_account_id=payee_account_id,
            amount=amount,
            purpose_code=purpose_code,
            device_binding_method=device_binding_method,
            payer_address=payer_address
        )
        
        # Check risk score threshold
        if risk_score > RISK_SCORE_THRESHOLD:
            raise UPITransactionError(
                f"RiskScore {risk_score} exceeds allowed threshold",
                error_code="RISK_SCORE_EXCEEDED"
            )
        
        # Create block record
        block_id = str(uuid.uuid4())
        now = datetime.utcnow()
        block = BlockRecord(
            block_id=block_id,
            payer_account_id=payer_account_id,
            payee_account_id=payee_account_id,
            amount=amount,
            purpose_code=purpose_code,
            status=BlockStatus.CREATED,
            created_at=now,
            expires_at=now + timedelta(days=expiry_days),
            risk_score=risk_score,
            dsc_validated=bool(dsc_cert_id and dsc_signature),
            dsc_signature=dsc_signature
        )
        
        # Save to registry
        BlockRegistry.create_block(block)
        
        # Send notifications
        NotificationEngine.notify_block_created(block)
        
        logging.info(f"Block created: {block_id}, Amount: {amount}, Risk: {risk_score}")
        
        return block
    
    @classmethod
    def execute_debit(cls, block_id: str, merchant_id: Optional[str] = None) -> BlockRecord:
        """Execute debit on an existing block."""
        block = BlockRegistry.get_block(block_id)
        
        if not block:
            raise ValueError(f"Block {block_id} not found")
        
        if block.status != BlockStatus.CREATED:
            raise ValueError(f"Block {block_id} is not in CREATED status")
        
        if block.expires_at <= datetime.utcnow():
            raise ValueError(f"Block {block_id} has expired")
        
        # Generate transaction reference
        transaction_ref = f"TXN-{block_id}-{int(time.time())}"
        
        # Update block status
        BlockRegistry.update_block_status(block_id, BlockStatus.DEBITED, transaction_ref)
        
        # Send notifications
        NotificationEngine.notify_block_debited(block)
        
        # Trigger merchant webhook if configured
        if merchant_id:
            MerchantWebhookSystem.notify_debit_event(block, merchant_id)
        
        logging.info(f"Block debited: {block_id}, Transaction: {transaction_ref}")
        
        return BlockRegistry.get_block(block_id)
    
    @classmethod
    def revoke_block(cls, block_id: str, merchant_id: Optional[str] = None) -> BlockRecord:
        """Revoke a block."""
        block = BlockRegistry.get_block(block_id)
        
        if not block:
            raise ValueError(f"Block {block_id} not found")
        
        if block.status != BlockStatus.CREATED:
            raise ValueError(f"Block {block_id} is not in CREATED status")
        
        # Update block status
        BlockRegistry.update_block_status(block_id, BlockStatus.REVOKED)
        
        # Send notifications
        NotificationEngine.notify_block_revoked(block)
        
        # Trigger merchant webhook if configured
        if merchant_id:
            MerchantWebhookSystem.notify_revocation_event(block, merchant_id)
        
        logging.info(f"Block revoked: {block_id}")
        
        return BlockRegistry.get_block(block_id)
    
    @classmethod
    def get_block(cls, block_id: str) -> Optional[BlockRecord]:
        """Get block by ID."""
        return BlockRegistry.get_block(block_id)
    
    @classmethod
    def get_active_reserves(cls, account_id: str) -> List[BlockRecord]:
        """Get active reserves for an account."""
        all_blocks = BlockRegistry.get_blocks_by_status(BlockStatus.CREATED)
        return [b for b in all_blocks if b.payer_account_id == account_id]

# ----------------------------------------------------------------------
# Version & Logging
# ----------------------------------------------------------------------
VERSION = "1.5"
logging.basicConfig(level=logging.INFO, format="%(message)s")

# ----------------------------------------------------------------------
# Constants & Configurations
# ----------------------------------------------------------------------
DUMMY_LAT = "12.97"
DUMMY_LON = "77.59"
DUMMY_OS = "Android"

WHITELIST_OS = {"Android", "iOS"}
VALID_CURRENCY = "INR"
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,50}$")

# New MCC requirement
ALLOWED_MCC = "5432"

# Updated global transaction amount limit (schema‑driven) – now 3 lakh
MAX_TRANSACTION_AMOUNT = Decimal("300000")
# Updated P2P limit (70 k) – configurable for future adjustments
P2P_LIMIT = Decimal("300000")  # updated per spec
# Updated P2P specific limit (new constant for future configurability)
# (kept for backward compatibility; mirrors P2P_LIMIT)
P2P_MAX_LIMIT = P2P_LIMIT

# Risk‑Score limits
RISK_SCORE_MAX = 100                     # schema range 0‑100
RISK_SCORE_THRESHOLD = 80                # configurable reject threshold

# DeviceBindingMethod enumeration
ALLOWED_DEVICE_BINDING_METHODS = {"OTP", "Biometric", "PIN"}

# Purpose code configuration (updated)
PURPOSE_CODE_CONFIG = {
    "P0901": {
        "description": "Education Fee",
        "max_amount": Decimal("300000"),
        "allowed_tx_type": "PAY",
    },
    "P0907": {
        "description": "New Purpose Code",
        "max_amount": Decimal("300000"),
        "allowed_tx_type": "PAY",
    },
    "IPO": {
        "description": "Initial Public Offering",
        "max_amount": Decimal("300000"),
        "allowed_tx_type": "PAY",
    },
    "STK": {
        "description": "STK",
        "max_amount": Decimal("300000"),
        "allowed_tx_type": "PAY",
    },
    # ------------------------------------------------------------------
    # New purpose code for stock‑market transactions
    # ------------------------------------------------------------------
    "STK_MKT": {
        "description": "Stock Market Transaction",
        "max_amount": Decimal("300000"),
        "allowed_tx_type": "PAY",
    },
    "STOCK_MARKET": {
        "description": "Stock Market Transaction",
        "max_amount": Decimal("300000"),
        "allowed_tx_type": "PAY",
    },
}
VALID_PURPOSE_CODES = set(PURPOSE_CODE_CONFIG.keys())

# Lite schema constants
LITE_TX = "LiteTx"
LITE_AMOUNT = "LiteAmount"

# XML Namespace
NS_URI = "http://npci.org/upi/schema/"
NS = {"ns": NS_URI}

# ----------------------------------------------------------------------
# Custom Exceptions
# ----------------------------------------------------------------------
class UPITransactionError(Exception):
    """Exception raised for UPI transaction rule violations."""

    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.error_code = error_code


# ----------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------
def _ns(tag: str) -> str:
    """Helper to qualify a tag with the default namespace."""
    return f"{{{NS_URI}}}{tag}"


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_PATTERN.match(session_id):
        raise ValueError(
            f"SessionId '{session_id}' is malformed or contains invalid characters."
        )


def _extract_geo_from_element(root: ET.Element) -> tuple[str, str]:
    geo_elem = root.find(_ns("Geo"))
    if geo_elem is None:
        raise ValueError("Geo element not found in XML")
    lat = geo_elem.findtext(_ns("Lat"))
    lon = geo_elem.findtext(_ns("Long"))
    return lat, lon


def _extract_mcc(root: ET.Element) -> str:
    """Extract top‑level MCC element."""
    mcc_elem = root.find(_ns("MCC"))
    if mcc_elem is None or (mcc_elem.text or "").strip() == "":
        raise ValueError("MCC element is missing or empty.")
    return mcc_elem.text.strip()


def _validate_mcc(root: ET.Element) -> None:
    """Validate presence and allowed value of MCC."""
    mcc_val = _extract_mcc(root)
    if mcc_val != ALLOWED_MCC:
        raise ValueError(
            f"MCC value '{mcc_val}' is not allowed. Expected '{ALLOWED_MCC}'."
        )


def _parse_risk_score(root: ET.Element) -> int | None:
    """Parse optional <RiskScore> element, enforce 0‑100 range."""
    txt = root.findtext(_ns("RiskScore"))
    if txt is None:
        return None
    try:
        score = int(txt.strip())
    except ValueError:
        raise ValueError("<RiskScore> must be an integer.")
    if not (0 <= score <= RISK_SCORE_MAX):
        raise ValueError(
            f"<RiskScore> must be between 0 and {RISK_SCORE_MAX} inclusive."
        )
    return score


def _extract_device_binding_method(root: ET.Element) -> str:
    """Extract and validate mandatory <DeviceBindingMethod> element."""
    dbm_elem = root.find(_ns("DeviceBindingMethod"))
    if dbm_elem is None or (dbm_elem.text or "").strip() == "":
        raise ValueError("<DeviceBindingMethod> element is missing or empty.")
    dbm_val = dbm_elem.text.strip()
    if dbm_val not in ALLOWED_DEVICE_BINDING_METHODS:
        raise ValueError(
            f"<DeviceBindingMethod> value '{dbm_val}' is invalid. Allowed: {sorted(ALLOWED_DEVICE_BINDING_METHODS)}."
        )
    return dbm_val


# ----------------------------------------------------------------------
# SwitchOrchestrator
# ----------------------------------------------------------------------
class SwitchOrchestrator:
    """Orchestrates processing of incoming ReqPay messages (standard & Lite)."""

    @staticmethod
    def process(req_pay_xml: str) -> str | None:
        """Parse XML, validate, log, and forward errors. Routes to standard or Lite flow."""
        try:
            root = ET.fromstring(req_pay_xml)

            # ------------------------------------------------------------------
            # Global transaction amount limit (new rule)
            # ------------------------------------------------------------------
            amount_elem = root.find(_ns("Amount"))
            amount_text = None
            if amount_elem is not None:
                amount_text = amount_elem.get("value")
            if amount_text is not None:
                try:
                    amount_val = Decimal(amount_text.strip())
                except InvalidOperation:
                    raise ValueError("Amount element must contain a decimal number.")
                if amount_val > MAX_TRANSACTION_AMOUNT:
                    logging.error(
                        f"Transaction blocked: amount {amount_val} exceeds MAX_TRANSACTION_AMOUNT {MAX_TRANSACTION_AMOUNT}"
                    )
                    return (
                        "<RespPay>"
                        "<Status>FAIL</Status>"
                        "<ErrorCode>AMT_EXCEEDS_LIMIT</ErrorCode>"
                        "<Message>Transaction amount exceeds allowed limit</Message>"
                        "</RespPay>"
                    )
                # Log warning if amount exceeds previous 5‑lakh ceiling
                if amount_val > Decimal("500000"):
                    logging.warning(
                        f"Amount {amount_val} exceeds previous ceiling of 500,000; new limit is {MAX_TRANSACTION_AMOUNT}"
                    )

            # ------------------------------------------------------------------
            # Common validations (Currency, SessionId, TxType, purposeCode, MCC)
            # ------------------------------------------------------------------
            currency = root.findtext(_ns("Currency"), namespaces=NS)
            if currency != VALID_CURRENCY:
                raise ValueError(
                    f"Currency must be '{VALID_CURRENCY}', got '{currency}'"
                )

            session_elem = root.find(_ns("SessionId"))
            if session_elem is None:
                raise ValueError("Missing <SessionId> element.")
            session_id = session_elem.text.strip()
            _validate_session_id(session_id)
            logging.info(f"SessionId extracted: {session_id}")

            # New <purpose> field validation
            purpose_elem = root.find(_ns("purpose"))
            if purpose_elem is None or (purpose_elem.text or "").strip() == "":
                raise ValueError("<purpose> element is missing or empty.")
            logging.info(f"Purpose extracted: {purpose_elem.text.strip()}")

            # MCC validation (new requirement)
            _validate_mcc(root)

            # DeviceBindingMethod validation (new requirement)
            dbm_val = _extract_device_binding_method(root)
            logging.info(f"DeviceBindingMethod extracted: {dbm_val}")

            # Transaction type and purpose code validation
            purpose_code_elem = root.find(_ns("purposeCode"))
            if purpose_code_elem is not None:
                purpose_code = purpose_code_elem.get("code")
                if purpose_code not in VALID_PURPOSE_CODES:
                    raise ValueError(f"Unsupported purposeCode '{purpose_code}'.")
                cfg = PURPOSE_CODE_CONFIG[purpose_code]

                # Enforce allowed TxType
                tx_type_elem = root.find(_ns("TxType"))
                if (
                    tx_type_elem is None
                    or tx_type_elem.text.strip().upper() != cfg["allowed_tx_type"]
                ):
                    raise ValueError(
                        f"PurposeCode {purpose_code} is only allowed when TxType is {cfg['allowed_tx_type']}."
                    )

                # Enforce amount limit (purpose‑specific)
                amount_elem = root.find(_ns("Amount"))
                if amount_elem is None:
                    raise ValueError("Missing <Amount> element.")
                try:
                    amount = Decimal(amount_elem.get("value").strip())
                except (InvalidOperation, AttributeError):
                    raise ValueError("Amount must be a decimal number.")
                if amount > cfg["max_amount"]:
                    raise ValueError(
                        f"PurposeCode {purpose_code} amount {amount} exceeds limit of {cfg['max_amount']}"
                    )

            # ------------------------------------------------------------------
            # New RiskScore rule – range validation & logging
            # ------------------------------------------------------------------
            risk_score = _parse_risk_score(root)
            if risk_score is not None:
                logging.info(f"RiskScore extracted: {risk_score}")

            # ------------------------------------------------------------------
            # Capture optional CustomerNote
            # ------------------------------------------------------------------
            customer_note = root.findtext(_ns("CustomerNote"), namespaces=NS)

            # ------------------------------------------------------------------
            # Determine flow: Lite vs Standard
            # ------------------------------------------------------------------
            if root.find(_ns(LITE_TX)) is not None:
                SwitchOrchestrator._process_lite(
                    root, session_id, risk_score, customer_note
                )
            else:
                SwitchOrchestrator._process_standard(
                    root, session_id, risk_score, customer_note
                )
            # Happy path returns None (no response needed)
            return None

        except Exception as e:
            logging.error(f"Failed to parse XML or validation failed: {e}")
            raise

    # ------------------------------------------------------------------
    # Standard flow
    # ------------------------------------------------------------------
    @staticmethod
    def _process_standard(
        root: ET.Element,
        session_id: str,
        risk_score: int | None,
        customer_note: str | None,
    ) -> None:
        """Standard (non‑Lite) processing path."""
        # Risk score validation (legacy <Risk><Score>)
        risk_elem = root.find(_ns("Risk"))
        if risk_elem is not None:
            score_text = risk_elem.findtext(_ns("Score"))
            risk_score_legacy = int(score_text) if score_text else 10
            if risk_score_legacy > 80:
                raise ValueError(
                    f"Transaction rejected: Risk score {risk_score_legacy} exceeds allowed limit."
                )

        # HighValue flag
        high_value_elem = root.find(_ns("HighValue"))
        high_value = (
            high_value_elem.findtext(_ns("HighValue"))
            if high_value_elem is not None
            else "false"
        )
        if high_value == "true":
            logging.warning("HighValue transaction detected")

        # Geo extraction & logging
        lat, lon = _extract_geo_from_element(root)
        logging.info(f"Switch received Geo location: lat={lat}, long={lon}")

        # Device/OS validation
        device_elem = root.find(_ns("Device"))
        if device_elem is None or device_elem.find(_ns("OS")) is None:
            raise ValueError("Required <Device><OS> element is missing.")
        os_value = device_elem.findtext(_ns("OS")).strip()
        if os_value not in WHITELIST_OS:
            raise ValueError(
                f"Transaction rejected: Unknown OS value '{os_value}'."
            )
        logging.info(f"Switch received OS: {os_value}")

        # MCC validation under Payee (existing rule)
        payee_elem = root.find(_ns("Payee"))
        if payee_elem is not None:
            mcc_elem = payee_elem.find(_ns("MCC"))
            if mcc_elem is not None:
                mcc_code = mcc_elem.get("code") or mcc_elem.findtext(_ns("code"))
                if mcc_code == "6011":
                    raise ValueError("Transaction rejected: MCC 6011 is not allowed.")

        # Log CustomerNote if present
        if customer_note:
            logging.info(f"CustomerNote received: {customer_note}")

        logging.info("Standard request processed successfully.")

    # ------------------------------------------------------------------
    # Lite flow
    # ------------------------------------------------------------------
    @staticmethod
    def _process_lite(
        root: ET.Element,
        session_id: str,
        risk_score: int | None,
        customer_note: str | None,
    ) -> None:
        """Validate Lite schema and log Lite‑specific fields."""
        # Required Lite elements
        lite_tx_elem = root.find(_ns(LITE_TX))
        lite_amount_elem = root.find(_ns(LITE_AMOUNT))
        if lite_tx_elem is None or lite_amount_elem is None:
            raise ValueError(
                f"Missing required Lite elements: <{LITE_TX}> and <{LITE_AMOUNT}>."
            )

        # Validate presence of <purpose> element (same as standard)
        purpose_elem = root.find(_ns("purpose"))
        if purpose_elem is None or (purpose_elem.text or "").strip() == "":
            raise ValueError("<purpose> element is missing or empty.")
        logging.info(f"Purpose extracted: {purpose_elem.text.strip()}")

        # Lite amount must be numeric (decimal)
        try:
            lite_amount = Decimal(lite_amount_elem.text.strip())
        except (InvalidOperation, AttributeError):
            raise ValueError(f"<{LITE_AMOUNT}> must contain a decimal value.")

        # Risk score validation (same rule as standard)
        risk_elem = root.find(_ns("Risk"))
        if risk_elem is not None:
            score_text = risk_elem.findtext(_ns("Score"))
            risk_score_legacy = int(score_text) if score_text else 10
            if risk_score_legacy > 80:
                raise ValueError(
                    f"Transaction rejected: Risk score {risk_score_legacy} exceeds allowed limit."
                )

        # HighValue flag (based on Lite amount)
        high_value = "true" if lite_amount > Decimal("100000") else "false"
        if high_value == "true":
            logging.warning(
                f"HighValue Lite transaction detected: amount={lite_amount}"
            )

        # Geo extraction & logging
        lat, lon = _extract_geo_from_element(root)
        logging.info(f"Lite request Geo location: lat={lat}, long={lon}")

        # Device/OS validation (same whitelist)
        device_elem = root.find(_ns("Device"))
        if device_elem is None or device_elem.find(_ns("OS")) is None:
            raise ValueError("Required <Device><OS> element is missing.")
        os_value = device_elem.findtext(_ns("OS")).strip()
        if os_value not in WHITELIST_OS:
            raise ValueError(
                f"Transaction rejected: Unknown OS value '{os_value}'."
            )
        logging.info(f"Lite request OS: {os_value}")

        # MCC validation (same rule)
        payee_elem = root.find(_ns("Payee"))
        if payee_elem is not None:
            mcc_elem = payee_elem.find(_ns("MCC"))
            if mcc_elem is not None:
                mcc_code = mcc_elem.get("code") or mcc_elem.findtext(_ns("code"))
                if mcc_code == "6011":
                    raise ValueError("Transaction rejected: MCC 6011 is not allowed.")

        # Log CustomerNote if present
        if customer_note:
            logging.info(f"CustomerNote received: {customer_note}")

        logging.info("Lite request processed successfully.")


# ----------------------------------------------------------------------
# debit_account – generates XML (standard or Lite)
# ----------------------------------------------------------------------
def debit_account(
    account_id,
    amount,
    purpose,
    receipt_id=None,
    secondary_user=None,
    delegation_limit=None,
    approval_required=False,
    payer_address=None,
    lite: bool = False,
    session_id: str = "test_session",
    tx_type: str = "PAY",
    purpose_code: str = "P0901",
    risk_score: int | None = None,
    customer_note: str | None = None,
    device_binding_method: str = "OTP",
):
    """
    Build a ReqPay XML payload.
    If ``lite=True`` the payload includes <LiteTx> and <LiteAmount> elements
    and follows the Lite schema; otherwise it follows the standard schema.
    The function injects a <purposeCode> element with the supplied code.
    Optionally injects a <RiskScore> element and a <CustomerNote> element.
    Adds mandatory <DeviceBindingMethod> element.
    """
    if purpose_code not in VALID_PURPOSE_CODES:
        raise ValueError(f"Unsupported purpose code '{purpose_code}'.")

    if device_binding_method not in ALLOWED_DEVICE_BINDING_METHODS:
        raise ValueError(
            f"DeviceBindingMethod '{device_binding_method}' is invalid. Allowed: {sorted(ALLOWED_DEVICE_BINDING_METHODS)}."
        )

    cfg = PURPOSE_CODE_CONFIG[purpose_code]

    # ------------------------------------------------------------------
    # MCC & Risk
    # ------------------------------------------------------------------
    # Top‑level MCC (new requirement)
    mcc_top_tag = f"<MCC>{ALLOWED_MCC}</MCC>"

    # Compute risk score based on payer address (legacy <Risk><Score>)
    risk_score_legacy = (
        90 if (payer_address and "risk" in payer_address.lower()) else 10
    )
    if risk_score_legacy > 80:
        raise ValueError(
            f"Transaction rejected: Risk score {risk_score_legacy} exceeds allowed limit."
        )

    # ------------------------------------------------------------------
    # PurposeCode amount limit validation (Payer PSP side)
    # ------------------------------------------------------------------
    if Decimal(amount) > cfg["max_amount"]:
        raise ValueError(
            f"PurposeCode {purpose_code} amount {amount} exceeds limit of {cfg['max_amount']}"
        )

    # ------------------------------------------------------------------
    # TxType validation (Payer PSP side)
    # ------------------------------------------------------------------
    if tx_type.upper() != cfg["allowed_tx_type"]:
        raise ValueError(
            f"PurposeCode {purpose_code} is only allowed when TxType is {cfg['allowed_tx_type']}."
        )

    # ------------------------------------------------------------------
    # Flags
    # ------------------------------------------------------------------
    high_value_flag = Decimal(amount) > Decimal("100000")
    lite_amount = Decimal(amount) if lite else None

    # ------------------------------------------------------------------
    # Fixed Geo coordinates
    # ------------------------------------------------------------------
    logging.info(f"Location: lat={DUMMY_LAT}, long={DUMMY_LON}")

    # ------------------------------------------------------------------
    # Build XML tags (standard vs Lite) respecting the required element order:
    # Head → Txn → purpose(opt) → purposeCode(opt) → Payer → Payees → RiskScore(opt) → HighValue(opt) → extensions
    # ------------------------------------------------------------------
    # Common tags
    session_tag = f"<SessionId>{session_id}</SessionId>"
    currency_tag = f"<Currency>{VALID_CURRENCY}</Currency>"
    account_tag = f"<account_id>{account_id}</account_id>"
    amount_formatted = f"{Decimal(amount):.2f}"
    amount_tag = f'<Amount value="{amount_formatted}" curr="{VALID_CURRENCY}"/>'
    purpose_tag = f"<purpose>{purpose}</purpose>"
    purpose_code_tag = f'<purposeCode code="{purpose_code}" description="{cfg["description"]}"/>'
    tx_type_tag = f"<TxType>{tx_type.upper()}</TxType>"
    risk_tag = f"<Risk><Score>{risk_score_legacy}</Score></Risk>"
    risk_score_tag = f"<RiskScore>{risk_score}</RiskScore>" if risk_score is not None else ""
    customer_note_tag = f"<CustomerNote>{customer_note}</CustomerNote>" if customer_note else ""
    device_binding_tag = f"<DeviceBindingMethod>{device_binding_method}</DeviceBindingMethod>"
    geo_tag = f"<Geo><Lat>{DUMMY_LAT}</Lat><Long>{DUMMY_LON}</Long></Geo>"
    device_tag = f"<Device><OS>{DUMMY_OS}</OS></Device>"
    high_value_tag = f"<HighValue>{str(high_value_flag).lower()}</HighValue>"
    receipt_tag = f"<receiptId>{receipt_id}</receiptId>" if receipt_id is not None else ""
    secondary_user_tag = (
        f"<secondaryUserId>{secondary_user}</secondaryUserId>"
        if secondary_user
        else ""
    )
    limit_tag = (
        f"<delegationLimit>{delegation_limit}</delegationLimit>"
        if delegation_limit is not None
        else ""
    )
    approval_tag = (
        f"<approvalRequired>{str(approval_required)}</approvalRequired>"
        if approval_required
        else ""
    )
    enc_data_tag = "<EncData>dummyBase64Value==</EncData>"
    # Payee tag (MCC as attribute – using dummy lat as placeholder per original code)
    payee_tag = f'<Payee><MCC code="{DUMMY_LAT}" /></Payee>'

    if lite:
        # Lite‑specific elements
        lite_tx_tag = f"<{LITE_TX}>True</{LITE_TX}>"
        lite_amount_tag = f"<{LITE_AMOUNT}>{lite_amount:.2f}</{LITE_AMOUNT}>"
        xml = f"""<ReqPay xmlns="{NS_URI}">
    {session_tag}
    {mcc_top_tag}
    {amount_tag}
    {purpose_tag}
    {purpose_code_tag}
    {tx_type_tag}
    {account_tag}
    {payee_tag}
    {risk_tag}
    {risk_score_tag}
    {customer_note_tag}
    {device_binding_tag}
    {geo_tag}
    {device_tag}
    {high_value_tag}
    {lite_tx_tag}
    {lite_amount_tag}
    {receipt_tag}
    {secondary_user_tag}
    {limit_tag}
    {approval_tag}
    {enc_data_tag}
</ReqPay>"""
    else:
        xml = f"""<ReqPay xmlns="{NS_URI}">
    {session_tag}
    {mcc_top_tag}
    {amount_tag}
    {purpose_tag}
    {purpose_code_tag}
    {tx_type_tag}
    {account_tag}
    {payee_tag}
    {risk_tag}
    {risk_score_tag}
    {customer_note_tag}
    {device_binding_tag}
    {geo_tag}
    {device_tag}
    {high_value_tag}
    {receipt_tag}
    {secondary_user_tag}
    {limit_tag}
    {approval_tag}
    {enc_data_tag}
</ReqPay>"""
    return xml


# ----------------------------------------------------------------------
# PSP Handlers (payer & payee) – new validation for MCC & RiskScore
# ----------------------------------------------------------------------
def _validate_stock_market_amount(purpose_code: str, amount: int) -> None:
    """Common validation used by both payer and payee PSP handlers."""
    if purpose_code in {"STK_MKT", "STOCK_MARKET"} and amount > 500_000:
        raise ValueError(
            "PurposeCode {} amount exceeds the 500,000 INR limit.".format(purpose_code),
            {"error_code": "ERR_STOCK_MARKET_AMOUNT_LIMIT"},
        )


def _validate_mcc_for_psp(mcc: str) -> None:
    """Validate MCC presence and allowed value for PSP handlers."""
    if mcc != ALLOWED_MCC:
        raise ValueError(
            f"MCC value '{mcc}' is not allowed for PSP processing. Expected '{ALLOWED_MCC}'."
        )


def _validate_risk_score(risk_score: int | None) -> None:
    """Validate the new RiskScore business rule."""
    if risk_score is not None:
        if not (0 <= risk_score <= RISK_SCORE_MAX):
            raise ValueError(
                f"RiskScore {risk_score} must be between 0 and {RISK_SCORE_MAX}."
            )
        if risk_score > RISK_SCORE_THRESHOLD:
            raise UPITransactionError(
                f"RiskScore {risk_score} exceeds allowed threshold.",
                error_code="RISK_SCORE_EXCEEDED",
            )


def _validate_device_binding_method_psp(device_binding_method: str) -> None:
    """Validate DeviceBindingMethod for PSP handlers."""
    if device_binding_method not in ALLOWED_DEVICE_BINDING_METHODS:
        raise ValueError(
            f"DeviceBindingMethod '{device_binding_method}' is invalid. Allowed: {sorted(ALLOWED_DEVICE_BINDING_METHODS)}."
        )


def payer_psp_handler(
    purpose_code: str,
    amount: int,
    mcc: str,
    risk_score: int | None = None,
    customer_note: str | None = None,
    device_binding_method: str = "OTP",
) -> None:
    """Validate transaction on the payer side."""
    # Global amount limit validation
    if amount > MAX_TRANSACTION_AMOUNT:
        raise ValueError(
            f"Amount {amount} exceeds the global limit of {MAX_TRANSACTION_AMOUNT}.",
            {"error_code": "ERR_GLOBAL_AMOUNT_LIMIT"},
        )
    # Warning for amounts exceeding 100,000 for additional risk checks
    if amount > 100_000:
        logging.warning(
            f"Amount {amount} exceeds 100,000; additional risk checks may be required."
        )

    _validate_stock_market_amount(purpose_code, amount)
    _validate_mcc_for_psp(mcc)
    _validate_risk_score(risk_score)
    _validate_device_binding_method_psp(device_binding_method)
    if customer_note:
        logging.info(f"Payer PSP received CustomerNote: {customer_note}")
    # Additional payer‑side logic would go here.


def payee_psp_handler(
    purpose_code: str,
    amount: int,
    mcc: str,
    risk_score: int | None = None,
    customer_note: str | None = None,
    device_binding_method: str = "OTP",
) -> None:
    """Validate transaction on the payee side."""
    _validate_stock_market_amount(purpose_code, amount)
    _validate_mcc_for_psp(mcc)
    _validate_risk_score(risk_score)
    _validate_device_binding_method_psp(device_binding_method)
    if customer_note:
        logging.info(f"Payee PSP received CustomerNote: {customer_note}")
    # Additional payee‑side logic would go here.


# ----------------------------------------------------------------------
# Bank Handlers – new validation & audit logging for STK_MKT & STOCK_MARKET
# ----------------------------------------------------------------------
def remitter_bank_handler(purpose_code: str, amount: int, risk_score: int | None = None) -> None:
    """Validate and debit the remitter's account."""
    # Global transaction limit (P2P limit)
    if Decimal(amount) > P2P_LIMIT:
        raise ValueError(
            f"Transaction amount {amount} exceeds the P2P limit of {P2P_LIMIT}.",
            {"error_code": "ERR_P2P_LIMIT_EXCEEDED"},
        )
    # Log when approaching the ceiling (e.g., >90% of limit)
    if Decimal(amount) > (P2P_LIMIT * Decimal("0.9")):
        logging.warning(
            f"Transaction amount {amount} is approaching the P2P limit of {P2P_LIMIT}."
        )
    # Existing stock‑market specific limit
    if purpose_code in {"STK_MKT", "STOCK_MARKET"} and amount > 500_000:
        raise ValueError(
            "PurposeCode {} amount exceeds the 500,000 INR limit.".format(purpose_code),
            {"error_code": "ERR_STOCK_MARKET_AMOUNT_LIMIT"},
        )
    _validate_risk_score(risk_score)
    # Debit logic would be implemented here.


def beneficiary_bank_handler(purpose_code: str, amount: int) -> None:
    """Process inbound transaction at the beneficiary bank."""
    if purpose_code in {"STK_MKT", "STOCK_MARKET"} and amount > 100_000:
        logging.info(
            f"High‑value STOCK_MARKET transaction flagged for audit: amount={amount}"
        )
    # Further processing would be implemented here.


# ----------------------------------------------------------------------
# API Routes for Core Transaction API
# ----------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/api/v1/blocks", methods=["POST"])
def create_block_api():
    """API endpoint to create a new block."""
    try:
        data = request.get_json()
        
        block = CoreTransactionAPI.create_block(
            payer_account_id=data["payer_account_id"],
            payee_account_id=data["payee_account_id"],
            amount=Decimal(str(data["amount"])),
            purpose_code=data["purpose_code"],
            device_binding_method=data.get("device_binding_method", "OTP"),
            payer_address=data.get("payer_address"),
            dsc_cert_id=data.get("dsc_cert_id"),
            dsc_signature=data.get("dsc_signature"),
            expiry_days=data.get("expiry_days", 7)
        )
        
        return jsonify({
            "status": "success",
            "block_id": block.block_id,
            "amount": str(block.amount),
            "status": block.status.value,
            "created_at": block.created_at.isoformat(),
            "expires_at": block.expires_at.isoformat(),
            "risk_score": block.risk_score
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error(f"Error creating block: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route("/api/v1/blocks/<block_id>/debit", methods=["POST"])
def execute_debit_api(block_id: str):
    """API endpoint to execute debit on a block."""
    try:
        data = request.get_json() or {}
        merchant_id = data.get("merchant_id")
        
        block = CoreTransactionAPI.execute_debit(block_id, merchant_id)
        
        return jsonify({
            "status": "success",
            "block_id": block.block_id,
            "status": block.status.value,
            "transaction_ref": block.transaction_ref,
            "debited_at": block.debited_at.isoformat() if block.debited_at else None
        }), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error(f"Error executing debit: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route("/api/v1/blocks/<block_id>/revoke", methods=["POST"])
def revoke_block_api(block_id: str):
    """API endpoint to revoke a block."""
    try:
        data = request.get_json() or {}
        merchant_id = data.get("merchant_id")
        
        block = CoreTransactionAPI.revoke_block(block_id, merchant_id)
        
        return jsonify({
            "status": "success",
            "block_id": block.block_id,
            "status": block.status.value,
            "revoked_at": block.revoked_at.isoformat() if block.revoked_at else None
        }), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error(f"Error revoking block: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route("/api/v1/blocks/<block_id>", methods=["GET"])
def get_block_api(block_id: str):
    """API endpoint to get block details."""
    block = CoreTransactionAPI.get_block(block_id)
    
    if not block:
        return jsonify({"status": "error", "message": "Block not found"}), 404
    
    return jsonify({
        "block_id": block.block_id,
        "payer_account_id": block.payer_account_id,
        "payee_account_id": block.payee_account_id,
        "amount": str(block.amount),
        "purpose_code": block.purpose_code,
        "status": block.status.value,
        "created_at": block.created_at.isoformat(),
        "expires_at": block.expires_at.isoformat(),
        "risk_score": block.risk_score,
        "dsc_validated": block.dsc_validated
    }), 200

@app.route("/api/v1/accounts/<account_id>/reserves", methods=["GET"])
def get_active_reserves_api(account_id: str):
    """API endpoint to get active reserves for an account."""
    reserves = CoreTransactionAPI.get_active_reserves(account_id)
    
    return jsonify({
        "account_id": account_id,
        "active_reserves": [
            {
                "block_id": r.block_id,
                "payee_account_id": r.payee_account_id,
                "amount": str(r.amount),
                "purpose_code": r.purpose_code,
                "expires_at": r.expires_at.isoformat()
            }
            for r in reserves
        ]
    }), 200

@app.route("/api/v1/webhooks", methods=["POST"])
def register_webhook_api():
    """API endpoint to register a merchant webhook."""
    try:
        data = request.get_json()
        MerchantWebhookSystem.register_webhook(
            data["merchant_id"],
            data["webhook_url"]
        )
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/api/v1/mis/report", methods=["GET"])
def generate_mis_report_api():
    """API endpoint to generate daily MIS report."""
    try:
        date_str = request.args.get("date")
        if date_str:
            report_date = datetime.fromisoformat(date_str)
        else:
            report_date = datetime.utcnow()
        
        report = MISReportGenerator.generate_daily_report(report_date)
        payload = MISReportGenerator.generate_npc_submission_payload(report)
        
        return jsonify(payload), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/mis/submit", methods=["POST"])
def submit_mis_report_api():
    """API endpoint to submit MIS report to NPCI."""
    try:
        data = request.get_json()
        report_date = datetime.fromisoformat(data["report_date"])
        
        report = MISReportGenerator.generate_daily_report(report_date)
        success = MISReportGenerator.submit_to_npci(report)
        
        if success:
            return jsonify({"status": "success", "message": "Report submitted to NPCI"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to submit report"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ----------------------------------------------------------------------
# Unit & Integration Tests
# ----------------------------------------------------------------------
class TestDebitAccountStandard(unittest.TestCase):
    def test_geo_element_contains_specified_coordinates(self):
        xml = debit_account(
            account_id="ACC123",
            amount=50000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=True,
            payer_address=None,
        )
        self.assertIn(f"<Lat>{DUMMY_LAT}</Lat>", xml)
        self.assertIn(f"<Long>{DUMMY_LON}</Long>", xml)
        self.assertIn("<HighValue>false</HighValue>", xml)
        self.assertIn('<Payee><MCC code="12.97" /></Payee>', xml)
        self.assertIn("<Device><OS>Android</OS></Device>", xml)
        self.assertIn("<Currency>INR</Currency>", xml)
        self.assertIn("<SessionId>test_session</SessionId>", xml)
        self.assertIn(
            '<purposeCode code="P0901" description="Education Fee"/>', xml
        )
        self.assertIn(f"<MCC>{ALLOWED_MCC}</MCC>", xml)
        self.assertIn("<DeviceBindingMethod>OTP</DeviceBindingMethod>", xml)

    def test_high_value_flag_set_correctly(self):
        xml = debit_account(
            account_id="ACC123",
            amount=150000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
        )
        self.assertIn("<HighValue>true</HighValue>", xml)

    def test_risk_score_injection_and_validation(self):
        xml = debit_account(
            account_id="ACC123",
            amount=50000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address="some risk address",
            risk_score=90,
        )
        self.assertIn(f"<Score>90</Score>", xml)
        self.assertIn(f"<RiskScore>90</RiskScore>", xml)

        # Clean address should not raise
        xml_clean = debit_account(
            account_id="ACC123",
            amount=50000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address="clean address",
            risk_score=10,
        )
        SwitchOrchestrator.process(xml_clean)  # should not raise

    def test_rejection_when_risk_score_exceeds_limit(self):
        xml = debit_account(
            account_id="ACC123",
            amount=50000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address="high risk address",
            risk_score=600,
        )
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(xml)
        self.assertIn("must be between 0 and 100", str(ctx.exception))

    def test_mcc_rejection_when_xml_contains_invalid_value(self):
        forbidden_xml = f"""<ReqPay xmlns="{NS_URI}">
    <MCC>9999</MCC>
    <Payee><MCC code="5411" /></Payee>
    <Currency>INR</Currency>
    <account_id>ACC123</account_id>
    <Amount value="50000.00" curr="INR"/>
    <purpose>test</purpose>
    <Risk><Score>10</Score></Risk>
    <HighValue>false</HighValue>
    <Geo><Lat>{DUMMY_LAT}</Lat><Long>{DUMMY_LON}</Long></Geo>
    <Device><OS>Android</OS></Device>
    <TxType>PAY</TxType>
    <purposeCode code="P0901" description="Education Fee"/>
    <receiptId>R1</receiptId>
</ReqPay>"""
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(forbidden_xml)
        self.assertIn("MCC value '9999' is not allowed", str(ctx.exception))

    def test_mcc_rejection_when_xml_contains_6011_under_payee(self):
        forbidden_xml = f"""<ReqPay xmlns="{NS_URI}">
    <MCC>{ALLOWED_MCC}</MCC>
    <Payee><MCC code="6011" /></Payee>
    <Currency>INR</Currency>
    <account_id>ACC123</account_id>
    <Amount value="50000.00" curr="INR"/>
    <purpose>test</purpose>
    <Risk><Score>10</Score></Risk>
    <HighValue>false</HighValue>
    <Geo><Lat>{DUMMY_LAT}</Lat><Long>{DUMMY_LON}</Long></Geo>
    <Device><OS>Android</OS></Device>
    <TxType>PAY</TxType>
    <purposeCode code="P0901" description="Education Fee"/>
    <receiptId>R1</receiptId>
</ReqPay>"""
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(forbidden_xml)
        self.assertIn("MCC 6011 is not allowed", str(ctx.exception))

    def test_currency_element_present_and_correct(self):
        xml = debit_account(
            account_id="ACC123",
            amount=50000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
        )
        self.assertIn("<Currency>INR</Currency>", xml)
        SwitchOrchestrator.process(xml)  # should succeed

    def test_invalid_currency_raises_error(self):
        invalid_xml = f"""<ReqPay xmlns="{NS_URI}">
    <MCC>{ALLOWED_MCC}</MCC>
    <Currency>USD</Currency>
    <Payee><MCC code="5411" /></Payee>
    <account_id>ACC123</account_id>
    <Amount value="50000.00" curr="INR"/>
    <purpose>test</purpose>
    <Risk><Score>10</Score></Risk>
    <HighValue>false</HighValue>
    <Geo><Lat>{DUMMY_LAT}</Lat><Long>{DUMMY_LON}</Long></Geo>
    <Device><OS>Android</OS></Device>
    <TxType>PAY</TxType>
    <purposeCode code="P0901" description="Education Fee"/>
    <receiptId>R1</receiptId>
</ReqPay>"""
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(invalid_xml)
        self.assertIn("Currency must be 'INR'", str(ctx.exception))

    def test_session_id_validation_successful(self):
        xml = debit_account(
            account_id="ACC123",
            amount=50000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            session_id="valid_session-123",
        )
        SwitchOrchestrator.process(xml)  # should succeed

    def test_session_id_validation_failure(self):
        invalid_xml = f"""<ReqPay xmlns="{NS_URI}">
    <MCC>{ALLOWED_MCC}</MCC>
    <SessionId>invalid@session</SessionId>
    <Payee><MCC code="5411" /></Payee>
    <account_id>ACC123</account_id>
    <Amount value="50000.00" curr="INR"/>
    <purpose>test</purpose>
    <Risk><Score>10</Score></Risk>
    <HighValue>false</HighValue>
    <Geo><Lat>{DUMMY_LAT}</Lat><Long>{DUMMY_LON}</Long></Geo>
    <Device><OS>Android</OS></Device>
    <TxType>PAY</TxType>
    <purposeCode code="P0901" description="Education Fee"/>
    <receiptId>R1</receiptId>
</ReqPay>"""
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(invalid_xml)
        self.assertIn("SessionId 'invalid@session' is malformed", str(ctx.exception))

    def test_purpose_code_p0901_with_pay_tx_type_passes(self):
        xml = debit_account(
            account_id="ACC123",
            amount=50000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            tx_type="PAY",
        )
        SwitchOrchestrator.process(xml)

    def test_purpose_code_p0901_with_non_pay_tx_type_fails(self):
        xml = debit_account(
            account_id="ACC123",
            amount=50000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            tx_type="OTHER",
        )
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(xml)
        self.assertIn("PurposeCode P0901 is only allowed when TxType is PAY", str(ctx.exception))

    def test_p0901_amount_limit_enforcement(self):
        # Amount exactly at limit should pass
        xml_at_limit = debit_account(
            account_id="ACC123",
            amount=300000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            tx_type="PAY",
        )
        SwitchOrchestrator.process(xml_at_limit)  # should succeed

        # Amount above limit should raise
        xml_over_limit = debit_account(
            account_id="ACC123",
            amount=300001,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            tx_type="PAY",
        )
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(xml_over_limit)
        self.assertIn("PurposeCode P0901 amount 300001 exceeds limit", str(ctx.exception))

    # ------------------------------------------------------------------
    # New tests for P0907
    # ------------------------------------------------------------------
    def test_purpose_code_p0907_with_pay_tx_type_passes(self):
        xml = debit_account(
            account_id="ACC123",
            amount=250000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            tx_type="PAY",
            purpose_code="P0907",
        )
        SwitchOrchestrator.process(xml)

    def test_purpose_code_p0907_with_non_pay_tx_type_fails(self):
        xml = debit_account(
            account_id="ACC123",
            amount=250000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            tx_type="REFUND",
            purpose_code="P0907",
        )
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(xml)
        self.assertIn("PurposeCode P0907 is only allowed when TxType is PAY", str(ctx.exception))

    def test_p0907_amount_limit_enforcement(self):
        # At limit
        xml_at_limit = debit_account(
            account_id="ACC123",
            amount=300000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            tx_type="PAY",
            purpose_code="P0907",
        )
        SwitchOrchestrator.process(xml_at_limit)  # should succeed

        # Over limit
        xml_over_limit = debit_account(
            account_id="ACC123",
            amount=300001,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            tx_type="PAY",
            purpose_code="P0907",
        )
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(xml_over_limit)
        self.assertIn("PurposeCode P0907 amount 300001 exceeds limit", str(ctx.exception))

    # ------------------------------------------------------------------
    # New tests for STK
    # ------------------------------------------------------------------
    def test_purpose_code_stk_with_pay_tx_type_passes(self):
        xml = debit_account(
            account_id="ACC123",
            amount=300000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            tx_type="PAY",
            purpose_code="STK",
        )
        SwitchOrchestrator.process(xml)

    def test_purpose_code_stk_with_non_pay_tx_type_fail(self):
        xml = debit_account(
            account_id="ACC123",
            amount=300000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            tx_type="REFUND",
            purpose_code="STK",
        )
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(xml)
        self.assertIn("PurposeCode STK is only allowed when TxType is PAY", str(ctx.exception))

    def test_stk_amount_limit_enforcement(self):
        # At limit
        xml_at_limit = debit_account(
            account_id="ACC123",
            amount=300000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            tx_type="PAY",
            purpose_code="STK",
        )
        SwitchOrchestrator.process(xml_at_limit)  # should succeed

        # Over limit
        xml_over_limit = debit_account(
            account_id="ACC123",
            amount=300001,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
            tx_type="PAY",
            purpose_code="STK",
        )
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(xml_over_limit)
        self.assertIn("PurposeCode STK amount 300001 exceeds limit", str(ctx.exception))

    # ------------------------------------------------------------------
    # New tests for STK_MKT
    # ------------------------------------------------------------------
    def test_purpose_code_stk_mkt_with_pay_tx_type_passes(self):
        xml = debit_account(
            account_id="ACC123",
            amount=300000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
        )
        SwitchOrchestrator.process(xml)

    def test_purpose_code_stk_mkt_with_non_pay_tx_type_fails(self):
        xml = debit_account(
            account_id="ACC123",
            amount=300000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
        )
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(xml)
        self.assertIn("PurposeCode STK_MKT is only allowed when TxType is PAY", str(ctx.exception))

    def test_stk_mkt_amount_limit_enforcement(self):
        # At limit
        xml_at_limit = debit_account(
            account_id="ACC123",
            amount=300000,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
        )
        SwitchOrchestrator.process(xml_at_limit)  # should succeed

        # Over limit
        xml_over_limit = debit_account(
            account_id="ACC123",
            amount=300001,
            purpose="test",
            receipt_id="R1",
            secondary_user="USR1",
            delegation_limit=1000,
            approval_required=False,
            payer_address=None,
        )
        with self.assertRaises(ValueError) as ctx:
            SwitchOrchestrator.process(xml_over_limit)
        self.assertIn("PurposeCode STK_MKT amount 300001 exceeds limit", str(ctx.exception))


# ------------------------------------------------------------------
# Core Transaction API Tests
# ------------------------------------------------------------------
class TestCoreTransactionAPI(unittest.TestCase):
    def setUp(self):
        """Clear block registry before each test."""
        BlockRegistry._blocks.clear()
        NotificationEngine._notification_history.clear()
        MerchantWebhookSystem._webhooks.clear()
        MerchantWebhookSystem._event_history.clear()
    
    def test_create_block_success(self):
        """Test successful block creation."""
        block = CoreTransactionAPI.create_block(
            payer_account_id="Payer123",
            payee_account_id="Payee456",
            amount=Decimal("50000"),
            purpose_code="P0901",
            device_binding_method="Biometric"
        )
        
        self.assertIsNotNone(block.block_id)
        self.assertEqual(block.payer_account_id, "Payer123")
        self.assertEqual(block.payee_account_id, "Payee456")
        self.assertEqual(block.amount, Decimal("50000"))
        self.assertEqual(block.status, BlockStatus.CREATED)
        self.assertIsNotNone(block.risk_score)
    
    def test_create_block_invalid_purpose_code(self):
        """Test block creation with invalid purpose code."""
        with self.assertRaises(ValueError) as ctx:
            CoreTransactionAPI.create_block(
                payer_account_id="Payer123",
                payee_account_id="Payee456",
                amount=Decimal("50000"),
                purpose_code="INVALID",
                device_binding_method="OTP"
            )
        self.assertIn("Unsupported purpose code", str(ctx.exception))
    
    def test_create_block_exceeds_limit(self):
        """Test block creation exceeding purpose code limit."""
        with self.assertRaises(ValueError) as ctx:
            CoreTransactionAPI.create_block(
                payer_account_id="Payer123",
                payee_account_id="Payee456",
                amount=Decimal("500000"),
                purpose_code="P0901",
                device_binding_method="OTP"
            )
        self.assertIn("exceeds limit", str(ctx.exception))
    
    def test_create_block_high_risk_score(self):
        """Test block creation with high risk score."""
        with self.assertRaises(UPITransactionError) as ctx:
            CoreTransactionAPI.create_block(
                payer_account_id="Payer123",
                payee_account_id="Payee456",
                amount=Decimal("50000"),
                purpose_code="STK_MKT",
                device_binding_method="OTP",
                payer_address="high risk address"
            )
        self.assertEqual(ctx.exception.error_code, "RISK_SCORE_EXCEEDED")
    
    def test_execute_debit_success(self):
        """Test successful debit execution."""
        block = CoreTransactionAPI.create_block(
            payer_account_id="Payer123",
            payee_account_id="Payee456",
            amount=Decimal("50000"),
            purpose_code="P0901",
            device_binding_method="Biometric"
        )
        
        debited_block = CoreTransactionAPI.execute_debit(block.block_id)
        
        self.assertEqual(debited_block.status, BlockStatus.DEBITED)
        self.assertIsNotNone(debited_block.transaction_ref)
        self.assertIsNotNone(debited_block.debited_at)
    
    def test_execute_debit_nonexistent_block(self):
        """Test debit on nonexistent block."""
        with self.assertRaises(ValueError) as ctx:
            CoreTransactionAPI.execute_debit("nonexistent-id")
        self.assertIn("not found", str(ctx.exception))
    
    def test_execute_debit_already_debited(self):
        """Test debit on already debited block."""
        block = CoreTransactionAPI.create_block(
            payer_account_id="Payer123",
            payee_account_id="Payee456",
            amount=Decimal("50000"),
            purpose_code="P0901",
            device_binding_method="Biometric"
        )
        
        CoreTransactionAPI.execute_debit(block.block_id)
        
        with self.assertRaises(ValueError) as ctx:
            CoreTransactionAPI.execute_debit(block.block_id)
        self.assertIn("not in CREATED status", str(ctx.exception))
    
    def test_revoke_block_success(self):
        """Test successful block revocation."""
        block = CoreTransactionAPI.create_block(
            payer_account_id="Payer123",
            payee_account_id="Payee456",
            amount=Decimal("50000"),
            purpose_code="P0901",
            device_binding_method="Biometric"
        )
        
        revoked_block = CoreTransactionAPI.revoke_block(block.block_id)
        
        self.assertEqual(revoked_block.status, BlockStatus.REVOKED)
        self.assertIsNotNone(revoked_block.revoked_at)
    
    def test_get_active_reserves(self):
        """Test getting active reserves for an account."""
        CoreTransactionAPI.create_block(
            payer_account_id="Payer123",
            payee_account_id="Payee456",
            amount=Decimal("50000"),
            purpose_code="P0901",
            device_binding_method="Biometric"
        )
        CoreTransactionAPI.create_block(
            payer_account_id="Payer123",
            payee_account_id="Payee789",
            amount=Decimal("30000"),
            purpose_code="P0907",
            device_binding_method="OTP"
        )
        
        reserves = CoreTransactionAPI.get_active_reserves("Payer123")
        
        self.assertEqual(len(reserves), 2)
    
    def test_dsc_validation(self):
        """Test DSC validation for block creation."""
        # Register a test certificate
        DSCValidator.register_certificate("cert123", "test_public_key")
        
        # Create block with valid DSC
        block_data = "Payer123:Payee456:50000:P0901"
        signature = hmac.new(
            b"test_public_key",
            block_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        block = CoreTransactionAPI.create_block(
            payer_account_id="Payer123",
            payee_account_id="Payee456",
            amount=Decimal("50000"),
            purpose_code="P0901",
            device_binding_method="Biometric",
            dsc_cert_id="cert123",
            dsc_signature=signature
        )
        
        self.assertTrue(block.dsc_validated)
    
    def test_fraud_detection_risk_score(self):
        """Test fraud detection risk score calculation."""
        score = FraudDetectionService.calculate_risk_score(
            payer_account_id="Payer123",
            payee_account_id="Payee456",
            amount=Decimal("150000"),
            purpose_code="STK_MKT",
            device_binding_method="OTP",
            payer_address="risk address"
        )
        
        self.assertGreater(score, 50)
        self.assertLessEqual(score, 100)


class TestNotificationEngine(unittest.TestCase):
    def setUp(self):
        NotificationEngine._notification_history.clear()
    
    def test_notification_sent(self):
        """Test notification is sent."""
        notification = Notification(
            recipient="TestUser",
            notification_type=NotificationType.BLOCK_CREATED,
            channel=NotificationChannel.SMS,
            message="Test message"
        )
        
        result = NotificationEngine.send_notification(notification)
        
        self.assertTrue(result)
        self.assertEqual(notification.status, "SENT")
    
    def test_notification_history(self):
        """Test notification history tracking."""
        notification = Notification(
            recipient="TestUser",
            notification_type=NotificationType.BLOCK_CREATED,
            channel=NotificationChannel.SMS,
            message="Test message"
        )
        
        NotificationEngine.send_notification(notification)
        history = NotificationEngine.get_notification_history("TestUser")
        
        self.assertEqual(len(history), 1)


class TestMerchantWebhookSystem(unittest.TestCase):
    def setUp(self):
        MerchantWebhookSystem._webhooks.clear()
        MerchantWebhookSystem._event_history.clear()
    
    def test_webhook_registration(self):
        """Test webhook registration."""
        MerchantWebhookSystem.register_webhook("merchant123", "https://example.com/webhook")
        
        self.assertEqual(MerchantWebhookSystem._webhooks["merchant123"], "https://example.com/webhook")
    
    def test_webhook_trigger(self):
        """Test webhook triggering."""
        MerchantWebhookSystem.register_webhook("merchant123", "https://example.com/webhook")
        
        result = MerchantWebhookSystem.trigger_webhook(
            "merchant123",
            "BLOCK_DEBITED",
            {"block_id": "test123", "amount": "50000"}
        )
        
        self.assertTrue(result)


class TestMISReportGenerator(unittest.TestCase):
    def setUp(self):
        BlockRegistry._blocks.clear()
    
    def test_generate_daily_report(self):
        """Test daily MIS report generation."""
        # Create some test blocks
        block = BlockRecord(
            block_id="test1",
            payer_account_id="Payer1",
            payee_account_id="Payee1",
            amount=Decimal("50000"),
            purpose_code="P0901",
            status=BlockStatus.CREATED,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            risk_score=50
        )
        BlockRegistry.create_block(block)
        
        report = MISReportGenerator.generate_daily_report(datetime.utcnow())
        
        self.assertEqual(report.total_blocks_created, 1)
        self.assertEqual(report.total_amount_blocked, Decimal("50000"))
    
    def test_npc_submission_payload(self):
        """Test NPCI submission payload generation."""
        report = MISReport(
            report_date=datetime.utcnow(),
            total_blocks_created=10,
            total_blocks_debited=5,
            total_blocks_revoked=1,
            total_blocks_expired=0,
            total_amount_blocked=Decimal("500000"),
            total_amount_debited=Decimal("250000"),
            risk_score_distribution={10: 5, 20: 3, 30: 2},
            purpose_code_distribution={"P0901": 6, "P0907": 4}
        )
        
        payload = MISReportGenerator.generate_npc_submission_payload(report)
        
        self.assertIn("report_date", payload)
        self.assertIn("summary", payload)
        self.assertEqual(payload["summary"]["total_blocks_created"], 10)


class TestBlockExpiryScheduler(unittest.TestCase):
    def setUp(self):
        BlockRegistry._blocks.clear()
    
    def test_expiring_blocks_check(self):
        """Test detection of expiring blocks."""
        # Create a block expiring in 2 days
        block = BlockRecord(
            block_id="test1",
            payer_account_id="Payer1",
            payee_account_id="Payee1",
            amount=Decimal("50000"),
            purpose_code="P0901",
            status=BlockStatus.CREATED,
            created_at=datetime.utcnow() - timedelta(days=5),
            expires_at=datetime.utcnow() + timedelta(days=2),
            risk_score=50
        )
        BlockRegistry.create_block(block)
        
        expiring = BlockRegistry.get_expiring_blocks(3)
        
        self.assertEqual(len(expiring), 1)
        self.assertEqual(expiring[0].block_id, "test1")


# ------------------------------------------------------------------
# E2E Integration Tests
# ------------------------------------------------------------------
class TestE2EIntegration(unittest.TestCase):
    def setUp(self):
        """Clear all registries before each test."""
        BlockRegistry._blocks.clear()
        NotificationEngine._notification_history.clear()
        MerchantWebhookSystem._webhooks.clear()
        MerchantWebhookSystem._event_history.clear()
    
    def test_full_transaction_flow(self):
        """Test complete transaction flow: create -> debit -> verify."""
        # Step 1: Create block
        block = CoreTransactionAPI.create_block(
            payer_account_id="Payer123",
            payee_account_id="Payee456",
            amount=Decimal("50000"),
            purpose_code="P0901",
            device_binding_method="Biometric"
        )
        
        self.assertEqual(block.status, BlockStatus.CREATED)
        
        # Step 2: Execute debit
        debited_block = CoreTransactionAPI.execute_debit(block.block_id)
        
        self.assertEqual(debited_block.status, BlockStatus.DEBITED)
        self.assertIsNotNone(debited_block.transaction_ref)
        
        # Step 3: Verify notifications sent
        notifications = NotificationEngine.get_notification_history("Payer123")
        self.assertGreaterEqual(len(notifications), 2)  # Created and Debited
    
    def test_block_with_webhook_flow(self):
        """Test block flow with merchant webhook."""
        # Register webhook
        MerchantWebhookSystem.register_webhook("merchant123", "https://example.com/hook")
        
        # Create and debit block
        block = CoreTransactionAPI.create_block(
            payer_account_id="Payer123",
            payee_account_id="Payee456",
            amount=Decimal("50000"),
            purpose_code="P0901",
            device_binding_method="Biometric"
        )
        
        CoreTransactionAPI.execute_debit(block.block_id, merchant_id="merchant123")
        
        # Verify webhook triggered
        events = MerchantWebhookSystem.get_event_history()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "BLOCK_DEBITED")
    
    def test_revocation_flow(self):
        """Test block revocation flow."""
        block = CoreTransactionAPI.create_block(
            payer_account_id="Payer123",
            payee_account_id="Payee456",
            amount=Decimal("50000"),
            purpose_code="P0901",
            device_binding_method="Biometric"
        )
        
        # Revoke block
        revoked_block = CoreTransactionAPI.revoke_block(block.block_id)
        
        self.assertEqual(revoked_block.status, BlockStatus.REVOKED)
        
        # Verify notification
        notifications = NotificationEngine.get_notification_history("Payer123")
        revoke_notifications = [n for n in notifications 
                               if n.notification_type == NotificationType.BLOCK_REVOKED]
        self.assertEqual(len(revoke_notifications), 1)


if __name__ == "__main__":
    # Start block expiry scheduler
    BlockExpiryScheduler.start()
    
    try:
        unittest.main(verbosity=2)
    finally:
        BlockExpiryScheduler.stop()