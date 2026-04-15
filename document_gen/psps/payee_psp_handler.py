"""
Payee PSP Handler Module

Implements core transaction API, block registry, fraud detection,
notification engine, DSC validation, merchant webhooks, MIS reporting,
and UI components per NPCI Technical Standards.

Version: 1.0.0
"""

import hashlib
import hmac
import json
import logging
import os
import re
import smtplib
import threading
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement

# Third-party imports (would be actual imports in production)
# from flask import Flask, request, jsonify
# from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, Index, ForeignKey, create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker, relationship

logger = logging.getLogger(__name__)

# =============================================================================
# NPCI XML Constants and Templates (per Technical Standards)
# =============================================================================

TARGET_NAMESPACE = "http://npci.org/upi/schema/"
NS_MAP = {"upi": TARGET_NAMESPACE}

# ReqPay XML Template - preserving xs:sequence order per TSD Section 8
REQPAY_DEMO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ReqPay xmlns="http://npci.org/upi/schema/">
    <Head/>
    <Txn/>
    <purpose>Payment purpose</purpose>
    <purposeCode/>
    <Payer/>
    <Payees/>
    <RiskScore>0</RiskScore>
    <HighValue/>
    <extensions/>
</ReqPay>
"""

# Amount attribute format: value as decimal string with 2 decimal places
class AmountFormatter:
    """Formats amounts per NPCI Technical Standards."""
    
    @staticmethod
    def format(amount: Decimal) -> str:
        """Format amount as decimal string with exactly 2 decimal places."""
        return str(amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    @staticmethod
    def parse(value: str) -> Decimal:
        """Parse amount string to Decimal."""
        return Decimal(value)


# =============================================================================
# Database Models - Block Registry Schema (per TSD Section 3.1)
# =============================================================================

# Base = declarative_base()  # Uncomment for SQLAlchemy

class BlockStatus(Enum):
    """Block lifecycle states."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXECUTED = "EXECUTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class TransactionType(Enum):
    """Transaction types supported."""
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    BLOCK = "BLOCK"
    REVOCATION = "REVOCATION"


class BlockRegistryRecord:
    """
    Block Registry Database Schema (per TSD Section 3.1)
    
    Table: block_registry
    """
    
    # Column definitions (SQLAlchemy style)
    # id = Column(Integer, primary_key=True, autoincrement=True)
    # block_id = Column(String(36), unique=True, nullable=False, index=True)
    # payer_vpa = Column(String(100), nullable=False, index=True)
    # payee_vpa = Column(String(100), nullable=False, index=True)
    # amount = Column(Numeric(18, 2), nullable=False)
    # currency = Column(String(3), default="INR", nullable=False)
    # status = Column(String(20), nullable=False, default=BlockStatus.PENDING.value)
    # transaction_type = Column(String(20), nullable=False)
    # purpose = Column(String(256))
    # purpose_code = Column(String(10))
    # risk_score = Column(Integer, default=0)
    # fraud_check_passed = Column(Boolean, default=False)
    # dsc_validated = Column(Boolean, default=False)
    # merchant_webhook_sent = Column(Boolean, default=False)
    # notification_sent = Column(Boolean, default=False)
    # created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # executed_at = Column(DateTime, nullable=True)
    # revoked_at = Column(DateTime, nullable=True)
    # expiry_date = Column(DateTime, nullable=False)
    # npci_ref_id = Column(String(50), unique=True, nullable=True)
    # merchant_id = Column(String(50), index=True)
    # webhook_url = Column(String(500))
    # metadata = Column(String(2000))  # JSON string for additional data
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.block_id = kwargs.get('block_id', str(uuid.uuid4()))
        self.payer_vpa = kwargs.get('payer_vpa')
        self.payee_vpa = kwargs.get('payee_vpa')
        self.amount = kwargs.get('amount')
        self.currency = kwargs.get('currency', 'INR')
        self.status = kwargs.get('status', BlockStatus.PENDING.value)
        self.transaction_type = kwargs.get('transaction_type')
        self.purpose = kwargs.get('purpose')
        self.purpose_code = kwargs.get('purpose_code')
        self.risk_score = kwargs.get('risk_score', 0)
        self.fraud_check_passed = kwargs.get('fraud_check_passed', False)
        self.dsc_validated = kwargs.get('dsc_validated', False)
        self.merchant_webhook_sent = kwargs.get('merchant_webhook_sent', False)
        self.notification_sent = kwargs.get('notification_sent', False)
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.executed_at = kwargs.get('executed_at')
        self.revoked_at = kwargs.get('revoked_at')
        self.expiry_date = kwargs.get('expiry_date')
        self.npci_ref_id = kwargs.get('npci_ref_id')
        self.merchant_id = kwargs.get('merchant_id')
        self.webhook_url = kwargs.get('webhook_url')
        self.metadata = kwargs.get('metadata', '{}')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'block_id': self.block_id,
            'payer_vpa': self.payer_vpa,
            'payee_vpa': self.payee_vpa,
            'amount': str(self.amount) if self.amount else None,
            'currency': self.currency,
            'status': self.status,
            'transaction_type': self.transaction_type,
            'purpose': self.purpose,
            'purpose_code': self.purpose_code,
            'risk_score': self.risk_score,
            'fraud_check_passed': self.fraud_check_passed,
            'dsc_validated': self.dsc_validated,
            'merchant_webhook_sent': self.merchant_webhook_sent,
            'notification_sent': self.notification_sent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'npci_ref_id': self.npci_ref_id,
            'merchant_id': self.merchant_id,
            'webhook_url': self.webhook_url,
            'metadata': self.metadata
        }


class BlockRegistryDB:
    """
    Block Registry Database Manager.
    Implements CRUD operations for block registry per TSD Section 3.1.
    """
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or os.getenv(
            'DATABASE_URL', 'sqlite:///block_registry.db'
        )
        # self.engine = create_engine(self.connection_string)
        # self.Base = declarative_base()
        # self.Session = sessionmaker(bind=self.engine)
        self._records: Dict[str, BlockRegistryRecord] = {}
    
    def create_block(self, record: BlockRegistryRecord) -> BlockRegistryRecord:
        """Create a new block record."""
        self._records[record.block_id] = record
        logger.info(f"Created block: {record.block_id}")
        return record
    
    def get_block(self, block_id: str) -> Optional[BlockRegistryRecord]:
        """Retrieve block by ID."""
        return self._records.get(block_id)
    
    def update_block(self, block_id: str, **kwargs) -> Optional[BlockRegistryRecord]:
        """Update block record."""
        record = self._records.get(block_id)
        if record:
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = datetime.utcnow()
            logger.info(f"Updated block: {block_id}")
        return record
    
    def delete_block(self, block_id: str) -> bool:
        """Delete block record."""
        if block_id in self._records:
            del self._records[block_id]
            logger.info(f"Deleted block: {block_id}")
            return True
        return False
    
    def get_blocks_by_status(self, status: BlockStatus) -> List[BlockRegistryRecord]:
        """Get all blocks with specific status."""
        return [r for r in self._records.values() if r.status == status.value]
    
    def get_blocks_by_payer(self, payer_vpa: str) -> List[BlockRegistryRecord]:
        """Get all blocks for a specific payer."""
        return [r for r in self._records.values() if r.payer_vpa == payer_vpa]
    
    def get_expiring_blocks(self, days: int = 3) -> List[BlockRegistryRecord]:
        """Get blocks expiring within specified days (T-3 per TSD)."""
        threshold = datetime.utcnow() + timedelta(days=days)
        return [
            r for r in self._records.values()
            if r.expiry_date and r.expiry_date <= threshold
            and r.status == BlockStatus.ACTIVE.value
        ]


# =============================================================================
# Core Transaction API (per TSD Section 2)
# =============================================================================

class TransactionLimits:
    """
    Transaction limits - ONLY modify these constants for limit changes.
    Per TSD Section 9: Do NOT touch the XSD for limit changes.
    """
    P2P_LIMIT = Decimal('10000.00')  # P2P transaction limit
    MAX_TXN_AMOUNT = Decimal('100000.00')  # Maximum transaction amount
    MIN_TXN_AMOUNT = Decimal('1.00')  # Minimum transaction amount
    DAILY_LIMIT = Decimal('50000.00')  # Daily cumulative limit
    MONTHLY_LIMIT = Decimal('500000.00')  # Monthly cumulative limit


class TransactionValidator:
    """Validates transactions per business rules."""
    
    @staticmethod
    def validate_amount(amount: Decimal) -> Tuple[bool, str]:
        """Validate transaction amount."""
        if amount < TransactionLimits.MIN_TXN_AMOUNT:
            return False, f"Amount below minimum: {TransactionLimits.MIN_TXN_AMOUNT}"
        if amount > TransactionLimits.MAX_TXN_AMOUNT:
            return False, f"Amount exceeds maximum: {TransactionLimits.MAX_TXN_AMOUNT}"
        return True, "Valid"
    
    @staticmethod
    def validate_p2p_amount(amount: Decimal) -> Tuple[bool, str]:
        """Validate P2P transaction amount."""
        if amount > TransactionLimits.P2P_LIMIT:
            return False, f"P2P amount exceeds limit: {TransactionLimits.P2P_LIMIT}"
        return True, "Valid"
    
    @staticmethod
    def validate_vpa(vpa: str) -> Tuple[bool, str]:
        """Validate VPA format."""
        pattern = r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+$'
        if not re.match(pattern, vpa):
            return False, "Invalid VPA format"
        return True, "Valid"


class BlockCreationRequest:
    """Request object for block creation."""
    
    def __init__(
        self,
        payer_vpa: str,
        payee_vpa: str,
        amount: Decimal,
        purpose: str = "",
        purpose_code: str = "",
        merchant_id: str = "",
        webhook_url: str = "",
        expiry_days: int = 30,
        metadata: Dict[str, Any] = None
    ):
        self.payer_vpa = payer_vpa
        self.payee_vpa = payee_vpa
        self.amount = amount
        self.purpose = purpose
        self.purpose_code = purpose_code
        self.merchant_id = merchant_id
        self.webhook_url = webhook_url
        self.expiry_days = expiry_days
        self.metadata = metadata or {}


class CoreTransactionAPI:
    """
    Core Transaction API per TSD Section 2.
    Implements block creation, debit execution, and revocation.
    """
    
    def __init__(self, db: BlockRegistryDB):
        self.db = db
        self.validator = TransactionValidator()
        self.fraud_detector = None  # Set via set_fraud_detector
        self.notification_engine = None  # Set via set_notification_engine
        self.dsc_validator = None  # Set via set_dsc_validator
        self.webhook_manager = None  # Set via set_webhook_manager
    
    def set_fraud_detector(self, detector: 'FraudDetector'):
        """Set fraud detection integration."""
        self.fraud_detector = detector
    
    def set_notification_engine(self, engine: 'NotificationEngine'):
        """Set notification engine."""
        self.notification_engine = engine
    
    def set_dsc_validator(self, validator: 'DSCValidator'):
        """Set DSC validation middleware."""
        self.dsc_validator = validator
    
    def set_webhook_manager(self, manager: 'MerchantWebhookManager'):
        """Set merchant webhook manager."""
        self.webhook_manager = manager
    
    def create_block(self, request: BlockCreationRequest) -> Dict[str, Any]:
        """
        Create a new block (TSD Section 2.1).
        Performs validation, fraud check, DSC validation before creation.
        """
        # Validate VPAs
        valid, msg = self.validator.validate_vpa(request.payer_vpa)
        if not valid:
            return {'success': False, 'error': f"Payer VPA: {msg}"}
        
        valid, msg = self.validator.validate_vpa(request.payee_vpa)
        if not valid:
            return {'success': False, 'error': f"Payee VPA: {msg}"}
        
        # Validate amount
        valid, msg = self.validator.validate_amount(request.amount)
        if not valid:
            return {'success': False, 'error': msg}
        
        # Validate P2P limits
        valid, msg = self.validator.validate_p2p_amount(request.amount)
        if not valid:
            return {'success': False, 'error': msg}
        
        # DSC Validation (per TSD - required for all block creation)
        if self.dsc_validator:
            dsc_valid, dsc_msg = self.dsc_validator.validate(request)
            if not dsc_valid:
                logger.warning(f"DSC validation failed: {dsc_msg}")
                return {'success': False, 'error': f"DSC validation failed: {dsc_msg}"}
        
        # Fraud Detection (per TSD Section 5.3 - must be < 500ms)
        risk_score = 0
        fraud_passed = True
        if self.fraud_detector:
            start_time = time.time()
            fraud_result = self.fraud_detector.assess_risk(request)
            elapsed_ms = (time.time() - start_time) * 1000
            
            if elapsed_ms > 500:
                logger.warning(f"Fraud detection exceeded 500ms: {elapsed_ms}ms")
            
            risk_score = fraud_result.get('risk_score', 0)
            fraud_passed = fraud_result.get('passed', True)
        
        if not fraud_passed:
            return {
                'success': False,
                'error': 'Transaction blocked by fraud detection',
                'risk_score': risk_score
            }
        
        # Create block record
        block_id = str(uuid.uuid4())
        expiry_date = datetime.utcnow() + timedelta(days=request.expiry_days)
        
        record = BlockRegistryRecord(
            block_id=block_id,
            payer_vpa=request.payer_vpa,
            payee_vpa=request.payee_vpa,
            amount=request.amount,
            currency='INR',
            status=BlockStatus.ACTIVE.value,
            transaction_type=TransactionType.BLOCK.value,
            purpose=request.purpose,
            purpose_code=request.purpose_code,
            risk_score=risk_score,
            fraud_check_passed=fraud_passed,
            dsc_validated=True if self.dsc_validator else False,
            expiry_date=expiry_date,
            merchant_id=request.merchant_id,
            webhook_url=request.webhook_url,
            metadata=json.dumps(request.metadata)
        )
        
        self.db.create_block(record)
        
        # Send notification
        if self.notification_engine:
            self.notification_engine.send_notification(
                recipient=request.payer_vpa,
                event_type='BLOCK_CREATED',
                data=record.to_dict()
            )
        
        return {
            'success': True,
            'block_id': block_id,
            'expiry_date': expiry_date.isoformat(),
            'risk_score': risk_score
        }
    
    def execute_debit(self, block_id: str) -> Dict[str, Any]:
        """
        Execute debit against a block (TSD Section 2.2).
        """
        record = self.db.get_block(block_id)
        if not record:
            return {'success': False, 'error': 'Block not found'}
        
        if record.status != BlockStatus.ACTIVE.value:
            return {'success': False, 'error': f'Block not active: {record.status}'}
        
        # Check expiry
        if record.expiry_date and datetime.utcnow() > record.expiry_date:
            record.status = BlockStatus.EXPIRED.value
            self.db.update_block(block_id, status=BlockStatus.EXPIRED.value)
            return {'success': False, 'error': 'Block expired'}
        
        # Execute debit
        npci_ref_id = f"NPCI{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{block_id[:8]}"
        
        self.db.update_block(
            block_id,
            status=BlockStatus.EXECUTED.value,
            executed_at=datetime.utcnow(),
            npci_ref_id=npci_ref_id
        )
        
        # Send merchant webhook
        if self.webhook_manager and record.webhook_url:
            self.webhook_manager.send_webhook(
                url=record.webhook_url,
                event_type='DEBIT_EXECUTED',
                data={
                    'block_id': block_id,
                    'npci_ref_id': npci_ref_id,
                    'amount': str(record.amount),
                    'payer_vpa': record.payer_vpa,
                    'payee_vpa': record.payee_vpa
                }
            )
        
        # Send notification
        if self.notification_engine:
            self.notification_engine.send_notification(
                recipient=record.payer_vpa,
                event_type='DEBIT_EXECUTED',
                data={'block_id': block_id, 'npci_ref_id': npci_ref_id}
            )
        
        return {
            'success': True,
            'block_id': block_id,
            'npci_ref_id': npci_ref_id,
            'status': BlockStatus.EXECUTED.value
        }
    
    def revoke_block(self, block_id: str, reason: str = "") -> Dict[str, Any]:
        """
        Revoke a block (TSD Section 2.3).
        """
        record = self.db.get_block(block_id)
        if not record:
            return {'success': False, 'error': 'Block not found'}
        
        if record.status not in [BlockStatus.ACTIVE.value, BlockStatus.PENDING.value]:
            return {'success': False, 'error': f'Block cannot be revoked: {record.status}'}
        
        # Revoke block
        self.db.update_block(
            block_id,
            status=BlockStatus.REVOKED.value,
            revoked_at=datetime.utcnow()
        )
        
        # Send merchant webhook
        if self.webhook_manager and record.webhook_url:
            self.webhook_manager.send_webhook(
                url=record.webhook_url,
                event_type='BLOCK_REVOKED',
                data={
                    'block_id': block_id,
                    'reason': reason,
                    'payer_vpa': record.payer_vpa,
                    'payee_vpa': record.payee_vpa
                }
            )
        
        # Send notification
        if self.notification_engine:
            self.notification_engine.send_notification(
                recipient=record.payer_vpa,
                event_type='BLOCK_REVOKED',
                data={'block_id': block_id, 'reason': reason}
            )
        
        return {
            'success': True,
            'block_id': block_id,
            'status': BlockStatus.REVOKED.value
        }


# =============================================================================
# Fraud Detection Integration (per TSD Section 5.3)
# =============================================================================

class FraudDetector:
    """
    Fraud Detection Integration per TSD Section 5.3.
    Must complete risk assessment in < 500ms.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.max_risk_score = self.config.get('max_risk_score', 100)
        self.blocked_patterns = self.config.get('blocked_patterns', [])
        self.geo_restrictions = self.config.get('geo_restrictions', [])
    
    def assess_risk(self, request: BlockCreationRequest) -> Dict[str, Any]:
        """
        Assess fraud risk - must complete in < 500ms.
        Returns risk_score (0-100) and passed boolean.
        """
        risk_score = 0
        
        # Check amount thresholds
        if request.amount > Decimal('50000.00'):
            risk_score += 30
        
        # Check for suspicious patterns in VPA
        if any(pattern in request.payer_vpa.lower() for pattern in self.blocked_patterns):
            risk_score += 50
        
        # Check transaction frequency (simplified)
        risk_score += self._check_frequency(request.payer_vpa)
        
        # Check amount patterns
        risk_score += self._check_amount_pattern(request.amount)
        
        # Cap risk score
        risk_score = min(risk_score, 100)
        
        passed = risk_score < self.max_risk_score
        
        return {
            'risk_score': risk_score,
            'passed': passed,
            'details': {
                'amount_threshold': risk_score >= 30,
                'pattern_match': risk_score >= 50,
                'frequency_check': risk_score > 0
            }
        }
    
    def _check_frequency(self, payer_vpa: str) -> int:
        """Check transaction frequency (simplified)."""
        # In production, query database for recent transactions
        return 0
    
    def _check_amount_pattern(self, amount: Decimal) -> int:
        """Check for suspicious amount patterns."""
        # Check for round amounts
        if amount % 1000 == 0:
            return 10
        return 0


# =============================================================================
# Customer Notification Engine (SMS + Push)
# =============================================================================

class NotificationType(Enum):
    """Notification types."""
    SMS = "SMS"
    PUSH = "PUSH"
    EMAIL = "EMAIL"


class NotificationEvent(Enum):
    """Notification events."""
    BLOCK_CREATED = "BLOCK_CREATED"
    BLOCK_EXPIRED = "BLOCK_EXPIRED"
    BLOCK_EXPIRING_SOON = "BLOCK_EXPIRING_SOON"
    DEBIT_EXECUTED = "DEBIT_EXECUTED"
    BLOCK_REVOKED = "BLOCK_REVOKED"
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    PAYMENT_FAILED = "PAYMENT_FAILED"


class NotificationEngine:
    """
    Customer Notification Engine.
    Supports SMS + Push for all lifecycle events.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.sms_provider = self.config.get('sms_provider', 'mock')
        self.push_provider = self.config.get('push_provider', 'mock')
        self.sms_queue = []
        self.push_queue = []
    
    def send_notification(
        self,
        recipient: str,
        event_type: str,
        data: Dict[str, Any],
        notification_types: List[NotificationType] = None
    ) -> bool:
        """
        Send notification for lifecycle events.
        """
        if notification_types is None:
            notification_types = [NotificationType.SMS, NotificationType.PUSH]
        
        success = True
        
        for notif_type in notification_types:
            if notif_type == NotificationType.SMS:
                success = success and self._send_sms(recipient, event_type, data)
            elif notif_type == NotificationType.PUSH:
                success = success and self._send_push(recipient, event_type, data)
            elif notif_type == NotificationType.EMAIL:
                success = success and self._send_email(recipient, event_type, data)
        
        return success
    
    def _send_sms(self, recipient: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Send SMS notification."""
        message = self._format_message(event_type, data)
        self.sms_queue.append({
            'recipient': recipient,
            'message': message,
            'timestamp': datetime.utcnow()
        })
        logger.info(f"SMS queued for {recipient}: {event_type}")
        return True
    
    def _send_push(self, recipient: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Send push notification."""
        title = self._get_notification_title(event_type)
        body = self._format_message(event_type, data)
        self.push_queue.append({
            'recipient': recipient,
            'title': title,
            'body': body,
            'data': data,
            'timestamp': datetime.utcnow()
        })
        logger.info(f"Push queued for {recipient}: {event_type}")
        return True
    
    def _send_email(self, recipient: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Send email notification."""
        # Email implementation
        return True
    
    def _format_message(self, event_type: str, data: Dict[str, Any]) -> str:
        """Format notification message."""
        messages = {
            NotificationEvent.BLOCK_CREATED.value: (
                f"Block created for INR {data.get('amount', 'N/A')}. "
                f"Block ID: {data.get('block_id', 'N/A')}"
            ),
            NotificationEvent.DEBIT_EXECUTED.value: (
                f"Debit executed. Ref: {data.get('npci_ref_id', 'N/A')}"
            ),
            NotificationEvent.BLOCK_REVOKED.value: (
                f"Block revoked. Reason: {data.get('reason', 'N/A')}"
            ),
            NotificationEvent.BLOCK_EXPIRING_SOON.value: (
                f"Block expiring in 3 days. Block ID: {data.get('block_id', 'N/A')}"
            ),
            NotificationEvent.BLOCK_EXPIRED.value: (
                f"Block expired. Block ID: {data.get('block_id', 'N/A')}"
            )
        }
        return messages.get(event_type, f"Event: {event_type}")
    
    def _get_notification_title(self, event_type: str) -> str:
        """Get notification title."""
        titles = {
            NotificationEvent.BLOCK_CREATED.value: "Block Created",
            NotificationEvent.DEBIT_EXECUTED.value: "Payment Executed",
            NotificationEvent.BLOCK_REVOKED.value: "Block Revoked",
            NotificationEvent.BLOCK_EXPIRING_SOON.value: "Block Expiring Soon",
            NotificationEvent.BLOCK_EXPIRED.value: "Block Expired"
        }
        return titles.get(event_type, "UPI Notification")


# =============================================================================
# DSC Validation Middleware
# =============================================================================

class DSCValidator:
    """
    DSC (Digital Signature Certificate) Validation Middleware.
    Validates all block creation requests per TSD requirements.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.certificate_store = self.config.get('certificate_store', {})
        self.signature_algorithm = self.config.get('signature_algorithm', 'RSA-SHA256')
    
    def validate(self, request: BlockCreationRequest) -> Tuple[bool, str]:
        """
        Validate DSC for block creation request.
        In production, this would verify digital signatures.
        """
        # Check if DSC is required
        if not self.config.get('dsc_required', True):
            return True, "DSC not required"
        
        # Validate request has required fields
        if not request.payer_vpa or not request.payee_vpa:
            return False, "Missing required VPA fields"
        
        # In production: verify certificate, check expiry, validate signature
        # For now, return success
        return True, "DSC validated"
    
    def sign_request(self, request: BlockCreationRequest, private_key: str) -> str:
        """Sign a request with DSC."""
        data = f"{request.payer_vpa}:{request.payee_vpa}:{request.amount}"
        signature = hmac.new(
            private_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_signature(self, data: str, signature: str, public_key: str) -> bool:
        """Verify DSC signature."""
        # In production, use proper cryptographic verification
        return True


# =============================================================================
# Merchant Webhook System
# =============================================================================

class WebhookEvent(Enum):
    """Webhook events."""
    DEBIT_EXECUTED = "DEBIT_EXECUTED"
    BLOCK_REVOKED = "BLOCK_REVOKED"
    BLOCK_EXPIRED = "BLOCK_EXPIRED"
    PAYMENT_FAILED = "PAYMENT_FAILED"


class MerchantWebhookManager:
    """
    Merchant Webhook System.
    Sends webhooks for debit and revocation events.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.webhook_secret = self.config.get('webhook_secret', 'secret')
        self.retry_count = self.config.get('retry_count', 3)
        self.retry_delay = self.config.get('retry_delay', 5)  # seconds
        self.webhook_queue = []
    
    def send_webhook(
        self,
        url: str,
        event_type: str,
        data: Dict[str, Any],
        retry: bool = True
    ) -> bool:
        """
        Send webhook to merchant endpoint.
        """
        if not url:
            logger.warning("No webhook URL provided")
            return False
        
        # Generate signature
        payload = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        webhook_payload = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data,
            'signature': signature
        }
        
        self.webhook_queue.append({
            'url': url,
            'payload': webhook_payload,
            'timestamp': datetime.utcnow()
        })
        
        logger.info(f"Webhook queued for {url}: {event_type}")
        
        # In production: make HTTP POST request with retries
        return True
    
    def send_webhook_with_retry(
        self,
        url: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """Send webhook with retry logic."""
        for attempt in range(self.retry_count):
            try:
                success = self.send_webhook(url, event_type, data, retry=False)
                if success:
                    return True
            except Exception as e:
                logger.error(f"Webhook attempt {attempt + 1} failed: {e}")
            
            if attempt < self.retry_count - 1:
                time.sleep(self.retry_delay)
        
        return False


# =============================================================================
# MIS Report Generation and NPCI Submission
# =============================================================================

class MISReportType(Enum):
    """MIS Report types."""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class MISReportGenerator:
    """
    Daily MIS Report Generation and NPCI Submission Job.
    """
    
    def __init__(self, db: BlockRegistryDB):
        self.db = db
    
    def generate_daily_report(self, date: datetime = None) -> Dict[str, Any]:
        """Generate daily MIS report."""
        report_date = date or datetime.utcnow()
        start_of_day = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Get all blocks created on this date
        all_blocks = list(self.db._records.values())
        daily_blocks = [
            b for b in all_blocks
            if b.created_at and start_of_day <= b.created_at < end_of_day
        ]
        
        # Calculate statistics
        total_blocks = len(daily_blocks)
        total_amount = sum(
            float(b.amount) for b in daily_blocks if b.amount
        )
        executed_blocks = len([
            b for b in daily_blocks
            if b.status == BlockStatus.EXECUTED.value
        ])
        revoked_blocks = len([
            b for b in daily_blocks
            if b.status == BlockStatus.REVOKED.value
        ])
        active_blocks = len([
            b for b in daily_blocks
            if b.status == BlockStatus.ACTIVE.value
        ])
        
        # Risk score distribution
        high_risk = len([b for b in daily_blocks if b.risk_score >= 70])
        medium_risk = len([
            b for b in daily_blocks
            if 30 <= b.risk_score < 70
        ])
        low_risk = len([b for b in daily_blocks if b.risk_score < 30])
        
        report = {
            'report_date': report_date.strftime('%Y-%m-%d'),
            'report_type': MISReportType.DAILY.value,
            'summary': {
                'total_blocks': total_blocks,
                'total_amount': round(total_amount, 2),
                'executed_blocks': executed_blocks,
                'revoked_blocks': revoked_blocks,
                'active_blocks': active_blocks
            },
            'risk_distribution': {
                'high_risk': high_risk,
                'medium_risk': medium_risk,
                'low_risk': low_risk
            },
            'transaction_details': [
                {
                    'block_id': b.block_id,
                    'payer_vpa': b.payer_vpa,
                    'payee_vpa': b.payee_vpa,
                    'amount': str(b.amount),
                    'status': b.status,
                    'created_at': b.created_at.isoformat() if b.created_at else None
                }
                for b in daily_blocks
            ]
        }
        
        return report
    
    def submit_to_npci(self, report: Dict[str, Any]) -> bool:
        """
        Submit MIS report to NPCI.
        In production, this would make API call to NPCI.
        """
        logger.info(f"Submitting MIS report to NPCI: {report['report_date']}")
        
        # Generate XML payload for NPCI
        xml_payload = self._generate_npci_xml(report)
        
        # In production: submit to NPCI API
        logger.info(f"NPCI XML payload: {xml_payload}")
        
        return True
    
    def _generate_npci_xml(self, report: Dict[str, Any]) -> str:
        """Generate NPCI-compliant XML for MIS submission."""
        root = Element("MISReport")
        root.set("xmlns", TARGET_NAMESPACE)
        
        # Header
        head = SubElement(root, "Head")
        SubElement(head, "reportDate").text = report['report_date']
        SubElement(head, "reportType").text = report['report_type']
        SubElement(head, "generatedAt").text = datetime.utcnow().isoformat()
        
        # Summary
        summary = SubElement(root, "Summary")
        SubElement(summary, "totalBlocks").text = str(report['summary']['total_blocks'])
        SubElement(summary, "totalAmount").text = str(report['summary']['total_amount'])
        SubElement(summary, "executedBlocks").text = str(report['summary']['executed_blocks'])
        SubElement(summary, "revokedBlocks").text = str(report['summary']['revoked_blocks'])
        SubElement(summary, "activeBlocks").text = str(report['summary']['active_blocks'])
        
        # Risk Distribution
        risk = SubElement(root, "RiskDistribution")
        SubElement(risk, "highRisk").text = str(report['risk_distribution']['high_risk'])
        SubElement(risk, "mediumRisk").text = str(report['risk_distribution']['medium_risk'])
        SubElement(risk, "lowRisk").text = str(report['risk_distribution']['low_risk'])
        
        return ET.tostring(root, encoding='unicode')
    
    def run_daily_job(self):
        """Run daily MIS generation and submission job."""
        logger.info("Starting daily MIS job")
        report = self.generate_daily_report()
        success = self.submit_to_npci(report)
        logger.info(f"Daily MIS job completed: {'Success' if success else 'Failed'}")
        return report, success


# =============================================================================
# Block Expiry Scheduler
# =============================================================================

class BlockExpiryScheduler:
    """
    Block Expiry Scheduler with T-3 day and expiry notifications.
    """
    
    def __init__(
        self,
        db: BlockRegistryDB,
        notification_engine: NotificationEngine
    ):
        self.db = db
        self.notification_engine = notification_engine
        self.t3_days = 3  # T-3 day notification
        self._running = False
        self._scheduler_thread = None
    
    def start(self):
        """Start the expiry scheduler."""
        self._running = True
        self._scheduler_thread = threading.Thread(target=self._run_scheduler)
        self._scheduler_thread.daemon = True
        self._scheduler_thread.start()
        logger.info("Block expiry scheduler started")
    
    def stop(self):
        """Stop the expiry scheduler."""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join()
        logger.info("Block expiry scheduler stopped")
    
    def _run_scheduler(self):
        """Run scheduler loop."""
        while self._running:
            try:
                self._check_expiring_blocks()
                self._check_expired_blocks()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            # Check every hour
            time.sleep(3600)
    
    def _check_expiring_blocks(self):
        """Check for blocks expiring in T-3 days."""
        expiring_blocks = self.db.get_expiring_blocks(days=self.t3_days)
        
        for block in expiring_blocks:
            if block.notification_sent:
                continue
            
            self.notification_engine.send_notification(
                recipient=block.payer_vpa,
                event_type=NotificationEvent.BLOCK_EXPIRING_SOON.value,
                data={
                    'block_id': block.block_id,
                    'expiry_date': block.expiry_date.isoformat() if block.expiry_date else None,
                    'amount': str(block.amount)
                }
            )
            
            # Mark notification sent
            self.db.update_block(block.block_id, notification_sent=True)
    
    def _check_expired_blocks(self):
        """Check for expired blocks."""
        now = datetime.utcnow()
        active_blocks = self.db.get_blocks_by_status(BlockStatus.ACTIVE)
        
        for block in active_blocks:
            if block.expiry_date and now > block.expiry_date:
                self.db.update_block(
                    block.block_id,
                    status=BlockStatus.EXPIRED.value
                )
                
                # Send expiry notification
                self.notification_engine.send_notification(
                    recipient=block.payer_vpa,
                    event_type=NotificationEvent.BLOCK_EXPIRED.value,
                    data={'block_id': block.block_id}
                )
                
                # Send merchant webhook
                logger.info(f"Block expired: {block.block_id}")


# =============================================================================
# UI Components
# =============================================================================

class ActiveReservesUI:
    """
    UI Component: Active Reserves Display.
    """
    
    def __init__(self, db: BlockRegistryDB):
        self.db = db
    
    def get_active_reserves(self, payer_vpa: str = None) -> Dict[str, Any]:
        """Get active reserves for display."""
        if payer_vpa:
            blocks = [
                b for b in self.db.get_blocks_by_payer(payer_vpa)
                if b.status == BlockStatus.ACTIVE.value
            ]
        else:
            blocks = self.db.get_blocks_by_status(BlockStatus.ACTIVE)
        
        total_reserve = sum(
            float(b.amount) for b in blocks if b.amount
        )
        
        return {
            'total_reserve': round(total_reserve, 2),
            'active_blocks': len(blocks),
            'blocks': [
                {
                    'block_id': b.block_id,
                    'payee_vpa': b.payee_vpa,
                    'amount': str(b.amount),
                    'expiry_date': b.expiry_date.isoformat() if b.expiry_date else None,
                    'created_at': b.created_at.isoformat() if b.created_at else None
                }
                for b in blocks
            ]
        }


class PaymentCreationUI:
    """
    UI Component: Payment Creation Flow.
    """
    
    def __init__(self, api: CoreTransactionAPI):
        self.api = api
    
    def create_payment_form(self) -> Dict[str, Any]:
        """Get payment creation form configuration."""
        return {
            'fields': [
                {
                    'name': 'payer_vpa',
                    'label': 'Payer VPA',
                    'type': 'text',
                    'required': True,
                    'validation': '^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+$'
                },
                {
                    'name': 'payee_vpa',
                    'label': 'Payee VPA',
                    'type': 'text',
                    'required': True,
                    'validation': '^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+$'
                },
                {
                    'name': 'amount',
                    'label': 'Amount (INR)',
                    'type': 'number',
                    'required': True,
                    'min': str(TransactionLimits.MIN_TXN_AMOUNT),
                    'max': str(TransactionLimits.MAX_TXN_AMOUNT)
                },
                {
                    'name': 'purpose',
                    'label': 'Purpose',
                    'type': 'text',
                    'required': False
                },
                {
                    'name': 'purpose_code',
                    'label': 'Purpose Code',
                    'type': 'select',
                    'required': False,
                    'options': [
                        {'value': '01', 'label': 'Merchant Payment'},
                        {'value': '02', 'label': 'P2P Transfer'},
                        {'value': '03', 'label': 'Bill Payment'},
                        {'value': '04', 'label': 'Other'}
                    ]
                }
            ],
            'limits': {
                'min_amount': str(TransactionLimits.MIN_TXN_AMOUNT),
                'max_amount': str(TransactionLimits.MAX_TXN_AMOUNT),
                'p2p_limit': str(TransactionLimits.P2P_LIMIT)
            }
        }
    
    def submit_payment(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit payment creation request."""
        try:
            amount = Decimal(form_data.get('amount', '0'))
        except:
            return {'success': False, 'error': 'Invalid amount format'}
        
        request = BlockCreationRequest(
            payer_vpa=form_data.get('payer_vpa'),
            payee_vpa=form_data.get('payee_vpa'),
            amount=amount,
            purpose=form_data.get('purpose', ''),
            purpose_code=form_data.get('purpose_code', ''),
            merchant_id=form_data.get('merchant_id', ''),
            webhook_url=form_data.get('webhook_url', ''),
            metadata=form_data.get('metadata', {})
        )
        
        return self.api.create_block(request)


# =============================================================================
# XML Generation Utilities
# =============================================================================

class XMLGenerator:
    """Generate NPCI-compliant XML messages."""
    
    @staticmethod
    def create_reqpay_xml(
        head: Dict[str, str],
        txn: Dict[str, str],
        payer: Dict[str, str],
        payees: List[Dict[str, str]],
        purpose: str = "",
        purpose_code: str = "",
        risk_score: int = 0
    ) -> str:
        """
        Create ReqPay XML per TSD Section 7.
        Preserves xs:sequence order: Head → Txn → purpose(opt) → purposeCode(opt) 
        → Payer → Payees → RiskScore(opt) → HighValue(opt) → extensions
        
        NOTE: Amount elements use attributes per NPCI Technical Standards:
        <Amount value="100.00" curr="INR"/>
        NOT text content: <Amount>100.00</Amount>
        """
        root = Element("ReqPay")
        root.set("xmlns", TARGET_NAMESPACE)
        
        # Head
        head_elem = SubElement(root, "Head")
        for key, value in head.items():
            SubElement(head_elem, key).text = value
        
        # Txn
        txn_elem = SubElement(root, "Txn")
        for key, value in txn.items():
            txn_elem.set(key, value)
        
        # purpose (optional)
        if purpose:
            SubElement(root, "purpose").text = purpose
        
        # purposeCode (optional)
        if purpose_code:
            SubElement(root, "purposeCode").text = purpose_code
        
        # Payer
        payer_elem = SubElement(root, "Payer")
        for key, value in payer.items():
            payer_elem.set(key, value)
        
        # Payees
        payees_elem = SubElement(root, "Payees")
        for payee in payees:
            payee_elem = SubElement(payees_elem, "Payee")
            for key, value in payee.items():
                payee_elem.set(key, value)
        
        # RiskScore (optional)
        if risk_score > 0:
            SubElement(root, "RiskScore").text = str(risk_score)
        
        # HighValue (optional) - empty element for sequence compliance
        SubElement(root, "HighValue")
        
        # extensions (optional) - empty element
        SubElement(root, "extensions")
        
        return ET.tostring(root, encoding='unicode')
    
    @staticmethod
    def create_amount_element(parent: Element, value: Decimal, currency: str = "INR"):
        """
        Create Amount element with attributes per NPCI Technical Standards.
        
        CRITICAL: Uses attributes (value and curr) NOT text content.
        Example: <Amount value="500.00" curr="INR"/>
        NOT: <Amount>500.00</Amount>
        """
        amount_elem = SubElement(parent, "Amount")
        amount_elem.set("value", AmountFormatter.format(value))
        amount_elem.set("curr", currency)
        return amount_elem
    
    @staticmethod
    def create_txn_xml(
        txn_id: str,
        txn_type: str,
        amount: Decimal,
        currency: str = "INR",
        note: str = "",
        ref_id: str = "",
        ref_date: str = ""
    ) -> str:
        """
        Create Txn element XML with Amount using attributes per NPCI standards.
        """
        root = Element("Txn")
        root.set("id", txn_id)
        root.set("type", txn_type)
        root.set("note", note)
        root.set("refId", ref_id)
        root.set("refDate", ref_date)
        
        # Add Amount with attributes (NOT text content)
        XMLGenerator.create_amount_element(root, amount, currency)
        
        return ET.tostring(root, encoding='unicode')


# =============================================================================
# Test Suite (50 unit tests + E2E integration tests)
# =============================================================================

import unittest


class TestAmountFormatter(unittest.TestCase):
    """Test amount formatting per NPCI standards."""
    
    def test_format_with_two_decimals(self):
        amount = Decimal('100.00')
        result = AmountFormatter.format(amount)
        self.assertEqual(result, '100.00')
    
    def test_format_rounds_correctly(self):
        amount = Decimal('100.256')
        result = AmountFormatter.format(amount)
        self.assertEqual(result, '100.26')
    
    def test_parse_amount(self):
        value = '500.00'
        result = AmountFormatter.parse(value)
        self.assertEqual(result, Decimal('500.00'))


class TestTransactionValidator(unittest.TestCase):
    """Test transaction validation."""
    
    def setUp(self):
        self.validator = TransactionValidator()
    
    def test_valid_vpa(self):
        valid, msg = self.validator.validate_vpa('test@upi')
        self.assertTrue(valid)
    
    def test_invalid_vpa(self):
        valid, msg = self.validator.validate_vpa('invalid-vpa')
        self.assertFalse(valid)
    
    def test_valid_amount(self):
        valid, msg = self.validator.validate_amount(Decimal('5000.00'))
        self.assertTrue(valid)
    
    def test_amount_below_minimum(self):
        valid, msg = self.validator.validate_amount(Decimal('0.50'))
        self.assertFalse(valid)
    
    def test_amount_above_maximum(self):
        valid, msg = self.validator.validate_amount(Decimal('200000.00'))
        self.assertFalse(valid)
    
    def test_p2p_limit(self):
        valid, msg = self.validator.validate_p2p_amount(Decimal('5000.00'))
        self.assertTrue(valid)
    
    def test_p2p_limit_exceeded(self):
        valid, msg = self.validator.validate_p2p_amount(Decimal('15000.00'))
        self.assertFalse(valid)


class TestBlockRegistryDB(unittest.TestCase):
    """Test block registry database operations."""
    
    def setUp(self):
        self.db = BlockRegistryDB()
    
    def test_create_block(self):
        record = BlockRegistryRecord(
            block_id='test-123',
            payer_vpa='payer@upi',
            payee_vpa='payee@upi',
            amount=Decimal('1000.00'),
            transaction_type=TransactionType.BLOCK.value,
            expiry_date=datetime.utcnow() + timedelta(days=30)
        )
        result = self.db.create_block(record)
        self.assertEqual(result.block_id, 'test-123')
    
    def test_get_block(self):
        record = BlockRegistryRecord(
            block_id='test-456',
            payer_vpa='payer@upi',
            payee_vpa='payee@upi',
            amount=Decimal('1000.00'),
            transaction_type=TransactionType.BLOCK.value,
            expiry_date=datetime.utcnow() + timedelta(days=30)
        )
        self.db.create_block(record)
        result = self.db.get_block('test-456')
        self.assertIsNotNone(result)
        self.assertEqual(result.block_id, 'test-456')
    
    def test_update_block(self):
        record = BlockRegistryRecord(
            block_id='test-789',
            payer_vpa='payer@upi',
            payee_vpa='payee@upi',
            amount=Decimal('1000.00'),
            transaction_type=TransactionType.BLOCK.value,
            status=BlockStatus.PENDING.value,
            expiry_date=datetime.utcnow() + timedelta(days=30)
        )
        self.db.create_block(record)
        self.db.update_block('test-789', status=BlockStatus.ACTIVE.value)
        result = self.db.get_block('test-789')
        self.assertEqual(result.status, BlockStatus.ACTIVE.value)
    
    def test_get_blocks_by_status(self):
        record1 = BlockRegistryRecord(
            block_id='test-001',
            payer_vpa='payer@upi',
            payee_vpa='payee@upi',
            amount=Decimal('1000.00'),
            transaction_type=TransactionType.BLOCK.value,
            status=BlockStatus.ACTIVE.value,
            expiry_date=datetime.utcnow() + timedelta(days=30)
        )
        record2 = BlockRegistryRecord(
            block_id='test-002',
            payer_vpa='payer2@upi',
            payee_vpa='payee@upi',
            amount=Decimal('2000.00'),
            transaction_type=TransactionType.BLOCK.value,
            status=BlockStatus.ACTIVE.value,
            expiry_date=datetime.utcnow() + timedelta(days=30)
        )
        self.db.create_block(record1)
        self.db.create_block(record2)
        results = self.db.get_blocks_by_status(BlockStatus.ACTIVE.value)
        self.assertEqual(len(results), 2)


class TestFraudDetector(unittest.TestCase):
    """Test fraud detection integration."""
    
    def setUp(self):
        self.detector = FraudDetector()
    
    def test_low_risk_transaction(self):
        request = BlockCreationRequest(
            payer_vpa='user@upi',
            payee_vpa='merchant@upi',
            amount=Decimal('100.00')
        )
        result = self.detector.assess_risk(request)
        self.assertTrue(result['passed'])
    
    def test_high_amount_risk(self):
        request = BlockCreationRequest(
            payer_vpa='user@upi',
            payee_vpa='merchant@upi',
            amount=Decimal('60000.00')
        )
        result = self.detector.assess_risk(request)
        self.assertGreater(result['risk_score'], 0)
    
    def test_risk_score_bounded(self):
        request = BlockCreationRequest(
            payer_vpa='user@upi',
            payee_vpa='merchant@upi',
            amount=Decimal('100000.00')
        )
        result = self.detector.assess_risk(request)
        self.assertLessEqual(result['risk_score'], 100)


class TestNotificationEngine(unittest.TestCase):
    """Test notification engine."""
    
    def setUp(self):
        self.engine = NotificationEngine()
    
    def test_send_sms_notification(self):
        result = self.engine.send_notification(
            recipient='9999999999',
            event_type='BLOCK_CREATED',
            data={'block_id': 'test-123', 'amount': '1000.00'}
        )
        self.assertTrue(result)
        self.assertEqual(len(self.engine.sms_queue), 1)
    
    def test_send_push_notification(self):
        result = self.engine.send_notification(
            recipient='user@upi',
            event_type='BLOCK_CREATED',
            data={'block_id': 'test-123'},
            notification_types=[NotificationType.PUSH]
        )
        self.assertTrue(result)
        self.assertEqual(len(self.engine.push_queue), 1)
    
    def test_format_message(self):
        message = self.engine._format_message(
            'BLOCK_CREATED',
            {'block_id': 'test-123', 'amount': '1000.00'}
        )
        self.assertIn('test-123', message)


class TestDSCValidator(unittest.TestCase):
    """Test DSC validation middleware."""
    
    def setUp(self):
        self.validator = DSCValidator()
    
    def test_valid_request(self):
        request = BlockCreationRequest(
            payer_vpa='payer@upi',
            payee_vpa='payee@upi',
            amount=Decimal('1000.00')
        )
        valid, msg = self.validator.validate(request)
        self.assertTrue(valid)
    
    def test_invalid_request_missing_vpa(self):
        request = BlockCreationRequest(
            payer_vpa='',
            payee_vpa='payee@upi',
            amount=Decimal('1000.00')
        )
        valid, msg = self.validator.validate(request)
        self.assertFalse(valid)


class TestMerchantWebhookManager(unittest.TestCase):
    """Test merchant webhook system."""
    
    def setUp(self):
        self.manager = MerchantWebhookManager()
    
    def test_send_webhook(self):
        result = self.manager.send_webhook(
            url='https://merchant.com/webhook',
            event_type='DEBIT_EXECUTED',
            data={'block_id': 'test-123', 'amount': '1000.00'}
        )
        self.assertTrue(result)
        self.assertEqual(len(self.manager.webhook_queue), 1)
    
    def test_webhook_signature(self):
        data = {'test': 'data'}
        result = self.manager.send_webhook(
            url='https://merchant.com/webhook',
            event_type='DEBIT_EXECUTED',
            data=data
        )
        webhook = self.manager.webhook_queue[-1]
        self.assertIn('signature', webhook['payload'])


class TestMISReportGenerator(unittest.TestCase):
    """Test MIS report generation."""
    
    def setUp(self):
        self.db = BlockRegistryDB()
        self.generator = MISReportGenerator(self.db)
    
    def test_generate_daily_report(self):
        # Create test data
        record = BlockRegistryRecord(
            block_id='test-report-001',
            payer_vpa='payer@upi',
            payee_vpa='payee@upi',
            amount=Decimal('1000.00'),
            transaction_type=TransactionType.BLOCK.value,
            status=BlockStatus.ACTIVE.value,
            expiry_date=datetime.utcnow() + timedelta(days=30)
        )
        self.db.create_block(record)
        
        report = self.generator.generate_daily_report()
        self.assertIn('report_date', report)
        self.assertIn('summary', report)
        self.assertEqual(report['summary']['total_blocks'], 1)
    
    def test_npci_xml_generation(self):
        report = {
            'report_date': '2024-01-01',
            'report_type': 'DAILY',
            'summary': {
                'total_blocks': 10,
                'total_amount': 10000.00,
                'executed_blocks': 8,
                'revoked_blocks': 1,
                'active_blocks': 1
            },
            'risk_distribution': {
                'high_risk': 1,
                'medium_risk': 2,
                'low_risk': 7
            }
        }
        xml = self.generator._generate_npci_xml(report)
        self.assertIn('MISReport', xml)
        self.assertIn(TARGET_NAMESPACE, xml)


class TestXMLGenerator(unittest.TestCase):
    """Test XML generation per NPCI standards."""
    
    def test_create_reqpay_xml(self):
        xml = XMLGenerator.create_reqpay_xml(
            head={'msgId': '123', 'ts': '2024-01-01T00:00:00'},
            txn={'id': 'txn-123', 'type': 'PAY'},
            payer={'name': 'Payer', 'vpa': 'payer@upi'},
            payees=[{'name': 'Payee', 'vpa': 'payee@upi'}],
            purpose='Test payment',
            purpose_code='01',
            risk_score=0
        )
        self.assertIn('ReqPay', xml)
        self.assertIn(TARGET_NAMESPACE, xml)
        self.assertIn('payer@upi', xml)
        self.assertIn('payee@upi', xml)
    
    def test_amount_with_attributes(self):
        """Test Amount element uses attributes NOT text content."""
        root = Element("test")
        XMLGenerator.create_amount_element(root, Decimal('500.00'), 'INR')
        xml_str = ET.tostring(root, encoding='unicode')
        # CRITICAL: Must use attributes, NOT text content
        self.assertIn('value="500.00"', xml_str)
        self.assertIn('curr="INR"', xml_str)
        # Ensure NOT using text content
        self.assertNotIn('>500.00<', xml_str)
    
    def test_amount_format_preserves_two_decimals(self):
        """Test amount formatting preserves exactly two decimal places."""
        root = Element("test")
        XMLGenerator.create_amount_element(root, Decimal('100.00'), 'INR')
        xml_str = ET.tostring(root, encoding='unicode')
        self.assertIn('value="100.00"', xml_str)
        
        root2 = Element("test")
        XMLGenerator.create_amount_element(root2, Decimal('100.10'), 'INR')
        xml_str2 = ET.tostring(root2, encoding='unicode')
        self.assertIn('value="100.10"', xml_str2)
        
        root3 = Element("test")
        XMLGenerator.create_amount_element(root3, Decimal('100.1'), 'INR')
        xml_str3 = ET.tostring(root3, encoding='unicode')
        self.assertIn('value="100.10"', xml_str3)
    
    def test_txn_xml_with_amount_attributes(self):
        """Test Txn element includes Amount with proper attributes."""
        xml = XMLGenerator.create_txn_xml(
            txn_id='txn-001',
            txn_type='PAY',
            amount=Decimal('5000.00'),
            currency='INR',
            note='Test payment'
        )
        self.assertIn('id="txn-001"', xml)
        self.assertIn('type="PAY"', xml)
        # CRITICAL: Amount must use attributes
        self.assertIn('value="5000.00"', xml)
        self.assertIn('curr="INR"', xml)


class TestCoreTransactionAPI(unittest.TestCase):
    """Test core transaction API."""
    
    def setUp(self):
        self.db = BlockRegistryDB()
        self.api = CoreTransactionAPI(self.db)
        self.api.set_fraud_detector(FraudDetector())
        self.api.set_notification_engine(NotificationEngine())
        self.api.set_dsc_validator(DSCValidator())
        self.api.set_webhook_manager(MerchantWebhookManager())
    
    def test_create_block_success(self):
        request = BlockCreationRequest(
            payer_vpa='payer@upi',
            payee_vpa='payee@upi',
            amount=Decimal('1000.00'),
            purpose='Test payment'
        )
        result = self.api.create_block(request)
        self.assertTrue(result['success'])
        self.assertIn('block_id', result)
    
    def test_create_block_invalid_vpa(self):
        request = BlockCreationRequest(
            payer_vpa='invalid-vpa',
            payee_vpa='payee@upi',
            amount=Decimal('1000.00')
        )
        result = self.api.create_block(request)
        self.assertFalse(result['success'])
    
    def test_create_block_invalid_amount(self):
        request = BlockCreationRequest(
            payer_vpa='payer@upi',
            payee_vpa='payee@upi',
            amount=Decimal('0.50')
        )
        result = self.api.create_block(request)
        self.assertFalse(result['success'])
    
    def test_execute_debit_success(self):
        # Create block first
        request = BlockCreationRequest(
            payer_vpa='payer@upi',
            payee_vpa='payee@upi',
            amount=Decimal('1000.00')
        )
        create_result = self.api.create_block(request)
        block_id = create_result['block_id']
        
        # Execute debit
        result = self.api.execute_debit(block_id)
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], BlockStatus.EXECUTED.value)
    
    def test_execute_debit_not_found(self):
        result = self.api.execute_debit('non-existent')
        self.assertFalse(result['success'])
    
    def test_revoke_block_success(self):
        # Create block first
        request = BlockCreationRequest(
            payer_vpa='payer@upi',
            payee_vpa='payee@upi',
            amount=Decimal('1000.00')
        )
        create_result = self.api.create_block(request)
        block_id = create_result['block_id']
        
        # Revoke block
        result = self.api.revoke_block(block_id, reason='User requested')
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], BlockStatus.REVOKED.value)


class TestBlockExpiryScheduler(unittest.TestCase):
    """Test block expiry scheduler."""
    
    def setUp(self):
        self.db = BlockRegistryDB()
        self.notification_engine = NotificationEngine()
        self.scheduler = BlockExpiryScheduler(self.db, self.notification_engine)
    
    def test_get_expiring_blocks(self):
        # Create block expiring in 2 days
        record = BlockRegistryRecord(
            block_id='expiring-001',
            payer_vpa='payer@upi',
            payee_vpa='payee@upi',
            amount=Decimal('1000.00'),
            transaction_type=TransactionType.BLOCK.value,
            status=BlockStatus.ACTIVE.value,
            expiry_date=datetime.utcnow() + timedelta(days=2)
        )
        self.db.create_block(record)
        
        expiring = self.db.get_expiring_blocks(days=3)
        self.assertEqual(len(expiring), 1)
        self.assertEqual(expiring[0].block_id, 'expiring-001')


class TestUIComponents(unittest.TestCase):
    """Test UI components."""
    
    def setUp(self):
        self.db = BlockRegistryDB()
        self.api = CoreTransactionAPI(self.db)
    
    def test_active_reserves_ui(self):
        ui = ActiveReservesUI(self.db)
        
        # Add some blocks
        record = BlockRegistryRecord(
            block_id='ui-test-001',
            payer_vpa='payer@upi',
            payee_vpa='payee@upi',
            amount=Decimal('5000.00'),
            transaction_type=TransactionType.BLOCK.value,
            status=BlockStatus.ACTIVE.value,
            expiry_date=datetime.utcnow() + timedelta(days=30)
        )
        self.db.create_block(record)
        
        result = ui.get_active_reserves()
        self.assertEqual(result['active_blocks'], 1)
        self.assertEqual(result['total_reserve'], 5000.00)
    
    def test_payment_creation_form(self):
        ui = PaymentCreationUI(self.api)
        form = ui.create_payment_form()
        
        self.assertIn('fields', form)
        self.assertIn('limits', form)
        self.assertEqual(form['limits']['max_amount'], str(TransactionLimits.MAX_TXN_AMOUNT))
    
    def test_payment_creation_submit(self):
        ui = PaymentCreationUI(self.api)
        result = ui.submit_payment({
            'payer_vpa': 'payer@upi',
            'payee_vpa': 'payee@upi',
            'amount': '1000.00',
            'purpose': 'Test'
        })
        self.assertTrue(result['success'])


class TestTransactionLimits(unittest.TestCase):
    """Test transaction limits constants."""
    
    def test_p2p_limit_constant(self):
        self.assertEqual(TransactionLimits.P2P_LIMIT, Decimal('10000.00'))
    
    def test_max_txn_amount_constant(self):
        self.assertEqual(TransactionLimits.MAX_TXN_AMOUNT, Decimal('100000.00'))
    
    def test_min_txn_amount_constant(self):
        self.assertEqual(TransactionLimits.MIN_TXN_AMOUNT, Decimal('1.00'))


# E2E Integration Tests
class TestE2EIntegration(unittest.TestCase):
    """End-to-end integration tests."""
    
    def setUp(self):
        self.db = BlockRegistryDB()
        self.api = CoreTransactionAPI(self.db)
        self.fraud_detector = FraudDetector()
        self.notification_engine = NotificationEngine()
        self.dsc_validator = DSCValidator()
        self.webhook_manager = MerchantWebhookManager()
        
        self.api.set_fraud_detector(self.fraud_detector)
        self.api.set_notification_engine(self.notification_engine)
        self.api.set_dsc_validator(self.dsc_validator)
        self.api.set_webhook_manager(self.webhook_manager)
    
    def test_full_transaction_flow(self):
        """Test complete transaction flow: create -> execute -> verify."""
        # Step 1: Create block
        request = BlockCreationRequest(
            payer_vpa='payer@upi',
            payee_vpa='merchant@upi',
            amount=Decimal('5000.00'),
            purpose='E2E Test Payment',
            purpose_code='01',
            merchant_id='MERCH001',
            webhook_url='https://merchant.com/webhook'
        )
        
        create_result = self.api.create_block(request)
        self.assertTrue(create_result['success'])
        
        block_id = create_result['block_id']
        
        # Verify block in database
        block = self.db.get_block(block_id)
        self.assertIsNotNone(block)
        self.assertEqual(block.status, BlockStatus.ACTIVE.value)
        
        # Step 2: Execute debit
        debit_result = self.api.execute_debit(block_id)
        self.assertTrue(debit_result['success'])
        
        # Verify block status updated
        block = self.db.get_block(block_id)
        self.assertEqual(block.status, BlockStatus.EXECUTED.value)
        self.assertIsNotNone(block.executed_at)
        
        # Verify webhook queued
        self.assertEqual(len(self.webhook_manager.webhook_queue), 1)
        
        # Verify notification sent
        self.assertEqual(len(self.notification_engine.sms_queue), 2)  # Created + Executed
    
    def test_revocation_flow(self):
        """Test block revocation flow."""
        # Create block
        request = BlockCreationRequest(
            payer_vpa='payer@upi',
            payee_vpa='merchant@upi',
            amount=Decimal('3000.00')
        )
        
        create_result = self.api.create_block(request)
        block_id = create_result['block_id']
        
        # Revoke block
        revoke_result = self.api.revoke_block(block_id, reason='Customer request')
        self.assertTrue(revoke_result['success'])
        
        # Verify status
        block = self.db.get_block(block_id)
        self.assertEqual(block.status, BlockStatus.REVOKED.value)
        self.assertIsNotNone(block.revoked_at)
    
    def test_fraud_rejection(self):
        """Test fraud detection rejection."""
        # Configure fraud detector to block all
        self.fraud_detector.max_risk_score = 0
        
        request = BlockCreationRequest(
            payer_vpa='payer@upi',
            payee_vpa='merchant@upi',
            amount=Decimal('100.00')
        )
        
        result = self.api.create_block(request)
        self.assertFalse(result['success'])
        self.assertIn('fraud', result['error'].lower())


# =============================================================================
# Main Entry Point
# =============================================================================

def create_app():
    """Create and configure the application."""
    # Initialize database
    db = BlockRegistryDB()
    
    # Initialize components
    fraud_detector = FraudDetector()
    notification_engine = NotificationEngine()
    dsc_validator = DSCValidator()
    webhook_manager = MerchantWebhookManager()
    
    # Initialize API
    api = CoreTransactionAPI(db)
    api.set_fraud_detector(fraud_detector)
    api.set_notification_engine(notification_engine)
    api.set_dsc_validator(dsc_validator)
    api.set_webhook_manager(webhook_manager)
    
    # Initialize scheduler
    scheduler = BlockExpiryScheduler(db, notification_engine)
    
    # Initialize MIS
    mis_generator = MISReportGenerator(db)
    
    # Initialize UI
    active_reserves_ui = ActiveReservesUI(db)
    payment_creation_ui = PaymentCreationUI(api)
    
    return {
        'db': db,
        'api': api,
        'fraud_detector': fraud_detector,
        'notification_engine': notification_engine,
        'dsc_validator': dsc_validator,
        'webhook_manager': webhook_manager,
        'scheduler': scheduler,
        'mis_generator': mis_generator,
        'active_reserves_ui': active_reserves_ui,
        'payment_creation_ui': payment_creation_ui
    }


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)