"""
Enhanced validation service with detailed confidence scoring.
"""
from typing import Dict, Any, List
from ..models.validation import (
    ReceiptValidation, 
    ConfidenceLevel, 
    ValidationIssue
)
import time
import logging

logger = logging.getLogger(__name__)


class EnhancedValidationService:
    """
    Enhanced validation service with detailed confidence scoring.
    """
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 0.85
    MEDIUM_CONFIDENCE = 0.70
    LOW_CONFIDENCE = 0.50
    
    # Suspicious patterns
    SUSPICIOUS_AMOUNTS = [999.99, 9999.99, 0.00]
    MAX_REASONABLE_TOTAL = 10000.00  # $10k per receipt
    
    # Non-receipt keywords (Bank Slips, Payment Proofs)
    NON_RECEIPT_KEYWORDS = [
        "transfer successful", "payment successful", "duitnow", "jompay", 
        "interbank giro", "instant transfer", "fund transfer", 
        "payment advice", "transaction advice", "reference id", 
        "recipient reference", "beneficiary name", "account number"
    ]
    
    def __init__(self):
        self.start_time = None
        
    def _check_is_bank_slip(self, content: str) -> bool:
        """Check if content contains bank slip keywords."""
        if not content:
            return False
        
        content_lower = content.lower()
        # Count how many keywords appear
        matches = sum(1 for keyword in self.NON_RECEIPT_KEYWORDS if keyword in content_lower)
        
        # If 2 or more keywords match, it's likely a bank slip
        return matches >= 1
    
    def validate_receipt(
        self,
        azure_result: Dict[str, Any],
        sources_used: List[str],
        start_time: float
    ) -> ReceiptValidation:
        """
        Comprehensive receipt validation.
        
        Args:
            azure_result: Processed receipt data
            sources_used: List of OCR sources used (azure, llm_vision, etc.)
            start_time: Processing start timestamp
            
        Returns:
            ReceiptValidation object with detailed confidence scores
        """
        
        fields = azure_result.get('fields', {})
        doc_confidence = azure_result.get('confidence', 0.0)
        doc_type = azure_result.get('doc_type', 'unknown')
        
        # Extract field confidences
        merchant_conf = self._get_field_confidence(fields, 'MerchantName')
        total_conf = self._get_field_confidence(fields, 'Total')
        items_conf = self._calculate_items_confidence(fields)
        
        # Calculate overall confidence (weighted average)
        overall_conf = self._calculate_overall_confidence(
            merchant_conf,
            items_conf,
            total_conf,
            doc_confidence
        )
        
        # Determine confidence level
        conf_level = self._get_confidence_level(overall_conf)
        
        # Validate fields and collect issues
        issues = []
        warnings = []
        
        # Check merchant name
        merchant_issues = self._validate_merchant(fields, merchant_conf)
        issues.extend(merchant_issues)
        
        # Check total amount
        total_issues = self._validate_total(fields, total_conf)
        issues.extend(total_issues)
        
        # Check items
        items_issues = self._validate_items(fields, items_conf)
        issues.extend(items_issues)
        
        # Check for suspicious patterns
        suspicious = self._check_suspicious_patterns(fields)
        issues.extend(suspicious)
        
        # Determine if manual review needed
        requires_review = (
            overall_conf < self.MEDIUM_CONFIDENCE or
            any(issue.severity == "error" for issue in issues) or
            len(issues) >= 3
        )
        
        # Generate user-friendly messages
        confidence_msg = self._generate_confidence_message(
            conf_level, 
            overall_conf
        )
        
        next_steps = self._generate_next_steps(
            conf_level, 
            issues, 
            requires_review
        ) if requires_review else None
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        # Check if receipt type is valid
        is_valid = 'receipt' in doc_type.lower() and doc_confidence >= 0.5
        
        # Check for bank slip / non-receipt keywords
        is_bank_slip = self._check_is_bank_slip(azure_result.get('content', ''))
        
        if is_bank_slip:
            issues.append(ValidationIssue(
                field="doc_type",
                issue_type="invalid_type",
                severity="error",
                message="Document appears to be a bank transfer/payment slip, not a receipt",
                confidence=1.0,
                suggested_action="Please upload a retail receipt with line items"
            ))
            # Force invalid
            is_valid = False
            overall_conf = 0.1
            conf_level = ConfidenceLevel.VERY_LOW
        
        # Enforce item presence for valid receipts
        items_count = len(fields.get('Items', {}).get('value', [])) if isinstance(fields.get('Items', {}), dict) else 0
        if is_valid and items_count == 0:
            # If no items but seemingly valid, downgrade confidence significantly
            # Unless it's a very clear single-amount receipt (e.g. Taxi) but even then usually has 1 item
            issues.append(ValidationIssue(
                field="items",
                issue_type="missing_critical",
                severity="error",
                message="No line items detected. Valid receipts must list purchased items.",
                confidence=0.8,
                suggested_action="Ensure the photo captures the list of items purchased"
            ))
            # Downgrade to require review, but maybe not fully invalid if we are unsure
            overall_conf = min(overall_conf, 0.4)
            conf_level = ConfidenceLevel.LOW
            requires_review = True
            is_valid = False # Treat 0 items as invalid for now to strict block bank slips

        if 'forgery_analysis' in azure_result:
            forgery_data = azure_result['forgery_analysis']
            is_forged = forgery_data.get('is_suspicious', False)
            forgery_conf = forgery_data.get('risk_score', 0.0)
            
            # Add flags as issues
            for flag in forgery_data.get('flags', []):
                issues.append(ValidationIssue(
                    field="image",
                    issue_type="suspicious",
                    severity="warning" if forgery_conf < 0.8 else "error",
                    message=f"Potential Manipulation: {flag}",
                    confidence=forgery_conf,
                    suggested_action="Verify if this is an original photo"
                ))
                
            # If high risk, lower confidence
            if is_forged and forgery_conf > 0.7:
                 # Cap overall confidence if likely forged
                overall_conf = min(overall_conf, 0.45) # Force LOW/VERY_LOW
                conf_level = self._get_confidence_level(overall_conf)
                requires_review = True
        else:
            is_forged = False
            forgery_conf = 0.0

        return ReceiptValidation(
            is_valid_receipt=is_valid,
            confidence_level=conf_level,
            overall_confidence=overall_conf,
            merchant_confidence=merchant_conf,
            items_confidence=items_conf,
            total_confidence=total_conf,
            issues=issues,
            warnings=warnings,
            requires_manual_review=requires_review,
            doc_type=doc_type,
            processing_time_ms=processing_time,
            sources_used=sources_used,
            confidence_message=confidence_msg,
            next_steps=next_steps,
            is_forged=is_forged,
            forgery_confidence=forgery_conf,
            forgery_reason=str(next((i.message for i in issues if i.issue_type == "suspicious"), "")) if is_forged else None
        )
    
    def _get_field_confidence(
        self, 
        fields: Dict, 
        field_name: str
    ) -> float:
        """Extract confidence score from field."""
        field_data = fields.get(field_name, {})
        if isinstance(field_data, dict):
            return field_data.get('confidence', 0.0)
        return 0.0
    
    def _calculate_items_confidence(self, fields: Dict) -> float:
        """Calculate average confidence for all items."""
        items = fields.get('Items', {})
        if isinstance(items, dict):
            items = items.get('value', [])
        
        if not items:
            return 0.0
        
        confidences = []
        for item in items:
            if isinstance(item, dict):
                item_conf = item.get('confidence', 0.0)
                confidences.append(item_conf)
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _calculate_overall_confidence(
        self,
        merchant_conf: float,
        items_conf: float,
        total_conf: float,
        doc_conf: float
    ) -> float:
        """
        Weighted average of all confidence scores.
        
        Weights:
        - Merchant: 30% (critical field)
        - Items: 30% (critical field)
        - Total: 25% (important)
        - Document: 15% (baseline)
        """
        weighted = (
            merchant_conf * 0.30 +
            items_conf * 0.30 +
            total_conf * 0.25 +
            doc_conf * 0.15
        )
        return min(1.0, max(0.0, weighted))
    
    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Map confidence score to level."""
        if confidence >= self.HIGH_CONFIDENCE:
            return ConfidenceLevel.HIGH
        elif confidence >= self.MEDIUM_CONFIDENCE:
            return ConfidenceLevel.MEDIUM
        elif confidence >= self.LOW_CONFIDENCE:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def _validate_merchant(
        self, 
        fields: Dict, 
        confidence: float
    ) -> List[ValidationIssue]:
        """Validate merchant name field."""
        issues = []
        merchant = fields.get('MerchantName', {})
        merchant_value = merchant.get('value', '') if isinstance(merchant, dict) else ''
        
        if not merchant_value or len(merchant_value.strip()) < 2:
            issues.append(ValidationIssue(
                field="merchant_name",
                issue_type="missing",
                severity="error",
                message="Merchant name not detected",
                confidence=confidence,
                suggested_action="Please verify and enter the store name manually"
            ))
        elif confidence < self.MEDIUM_CONFIDENCE:
            issues.append(ValidationIssue(
                field="merchant_name",
                issue_type="low_confidence",
                severity="warning",
                message=f"Low confidence merchant name: '{merchant_value}'",
                confidence=confidence,
                suggested_action="Please verify the store name is correct"
            ))
        
        return issues
    
    def _validate_total(
        self, 
        fields: Dict, 
        confidence: float
    ) -> List[ValidationIssue]:
        """Validate total amount field."""
        issues = []
        total = fields.get('Total', {})
        total_value = total.get('value', 0.0) if isinstance(total, dict) else 0.0
        
        if total_value == 0.0:
            issues.append(ValidationIssue(
                field="total",
                issue_type="missing",
                severity="error",
                message="Total amount not detected",
                confidence=confidence,
                suggested_action="Please verify and enter the total amount"
            ))
        elif confidence < self.MEDIUM_CONFIDENCE:
            issues.append(ValidationIssue(
                field="total",
                issue_type="low_confidence",
                severity="warning",
                message=f"Low confidence total: ${total_value:.2f}",
                confidence=confidence,
                suggested_action="Please verify the total amount is correct"
            ))
        
        # Check for suspicious amounts
        if total_value in self.SUSPICIOUS_AMOUNTS:
            issues.append(ValidationIssue(
                field="total",
                issue_type="suspicious",
                severity="warning",
                message=f"Suspicious total amount: ${total_value:.2f}",
                confidence=confidence,
                suggested_action="This looks like an OCR error. Please verify."
            ))
        
        if total_value > self.MAX_REASONABLE_TOTAL:
            issues.append(ValidationIssue(
                field="total",
                issue_type="suspicious",
                severity="warning",
                message=f"Unusually high total: ${total_value:.2f}",
                confidence=confidence,
                suggested_action="Please verify this is not an OCR error (e.g., '19.99' read as '1999')"
            ))
        
        return issues
    
    def _validate_items(
        self, 
        fields: Dict, 
        avg_confidence: float
    ) -> List[ValidationIssue]:
        """Validate items field."""
        issues = []
        items = fields.get('Items', {})
        if isinstance(items, dict):
            items = items.get('value', [])
        
        if not items:
            issues.append(ValidationIssue(
                field="items",
                issue_type="missing",
                severity="warning",
                message="No items detected on receipt",
                confidence=avg_confidence,
                suggested_action="Items may be added manually if needed"
            ))
        elif avg_confidence < self.MEDIUM_CONFIDENCE:
            issues.append(ValidationIssue(
                field="items",
                issue_type="low_confidence",
                severity="warning",
                message=f"Low confidence items (avg: {avg_confidence:.2f})",
                confidence=avg_confidence,
                suggested_action="Please review item names and prices"
            ))
        
        return issues
    
    def _check_suspicious_patterns(self, fields: Dict) -> List[ValidationIssue]:
        """Check for suspicious OCR patterns."""
        issues = []
        
        # Example: Check if all items have same price (unlikely)
        items = fields.get('Items', {})
        if isinstance(items, dict):
            items = items.get('value', [])
        
        if len(items) >= 3:
            prices = [
                item.get('TotalPrice', {}).get('value', 0) 
                for item in items 
                if isinstance(item, dict)
            ]
            if len(set(prices)) == 1 and prices[0] > 0:
                issues.append(ValidationIssue(
                    field="items",
                    issue_type="suspicious",
                    severity="warning",
                    message="All items have the same price - possible OCR error",
                    suggested_action="Please verify item prices are correct"
                ))
        
        return issues
    
    def _generate_confidence_message(
        self, 
        level: ConfidenceLevel, 
        score: float
    ) -> str:
        """Generate user-friendly confidence message."""
        messages = {
            ConfidenceLevel.HIGH: f"✅ High confidence ({score:.0%}) - Receipt data looks accurate",
            ConfidenceLevel.MEDIUM: f"⚠️ Medium confidence ({score:.0%}) - Please review the extracted data",
            ConfidenceLevel.LOW: f"⚠️ Low confidence ({score:.0%}) - Manual verification recommended",
            ConfidenceLevel.VERY_LOW: f"❌ Very low confidence ({score:.0%}) - Manual entry may be needed"
        }
        return messages.get(level, f"Confidence: {score:.0%}")
    
    def _generate_next_steps(
        self, 
        level: ConfidenceLevel, 
        issues: List[ValidationIssue],
        requires_review: bool
    ) -> str:
        """Generate actionable next steps for user."""
        if level == ConfidenceLevel.VERY_LOW:
            return "The image quality may be too poor. Try taking a clearer photo with better lighting."
        
        if len(issues) > 0:
            error_issues = [i for i in issues if i.severity == "error"]
            if error_issues:
                fields = ", ".join(set(i.field for i in error_issues))
                return f"Please manually enter: {fields}"
        
        if requires_review:
            return "Please review all extracted fields before saving."
        
        return "Review the highlighted fields and make corrections if needed."
