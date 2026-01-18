"""
Test script for enhanced validation service.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.validation_service import EnhancedValidationService
from app.models.validation import ConfidenceLevel
import time


def test_high_confidence_receipt():
    """Test validation with high confidence receipt."""
    print("\n=== Test 1: High Confidence Receipt ===")
    
    service = EnhancedValidationService()
    
    azure_result = {
        'confidence': 0.95,
        'doc_type': 'receipt.retail',
        'fields': {
            'MerchantName': {'value': 'Walmart', 'confidence': 0.92},
            'Total': {'value': 45.67, 'confidence': 0.90},
            'Items': {'value': [
                {'name': 'Milk', 'confidence': 0.88},
                {'name': 'Bread', 'confidence': 0.89},
                {'name': 'Eggs', 'confidence': 0.87}
            ]}
        }
    }
    
    validation = service.validate_receipt(
        azure_result,
        sources_used=['azure', 'llm_vision'],
        start_time=time.time()
    )
    
    print(f"Confidence Level: {validation.confidence_level}")
    print(f"Overall Confidence: {validation.overall_confidence:.2%}")
    print(f"Merchant Confidence: {validation.merchant_confidence:.2%}")
    print(f"Items Confidence: {validation.items_confidence:.2%}")
    print(f"Total Confidence: {validation.total_confidence:.2%}")
    print(f"Requires Review: {validation.requires_manual_review}")
    print(f"Issues Found: {len(validation.issues)}")
    print(f"Message: {validation.confidence_message}")
    
    assert validation.confidence_level == ConfidenceLevel.HIGH
    assert validation.overall_confidence >= 0.85
    assert not validation.requires_manual_review
    assert len(validation.issues) == 0
    print("✅ Test 1 PASSED")


def test_low_confidence_receipt():
    """Test validation with low confidence receipt."""
    print("\n=== Test 2: Low Confidence Receipt ===")
    
    service = EnhancedValidationService()
    
    azure_result = {
        'confidence': 0.55,
        'doc_type': 'receipt.retail',
        'fields': {
            'MerchantName': {'value': 'Unknown', 'confidence': 0.45},
            'Total': {'value': 0.0, 'confidence': 0.0},
            'Items': {'value': []}
        }
    }
    
    validation = service.validate_receipt(
        azure_result,
        sources_used=['azure'],
        start_time=time.time()
    )
    
    print(f"Confidence Level: {validation.confidence_level}")
    print(f"Overall Confidence: {validation.overall_confidence:.2%}")
    print(f"Requires Review: {validation.requires_manual_review}")
    print(f"Issues Found: {len(validation.issues)}")
    print(f"Message: {validation.confidence_message}")
    print(f"Next Steps: {validation.next_steps}")
    
    print("\nIssues:")
    for issue in validation.issues:
        print(f"  - {issue.field}: {issue.message}")
        print(f"    Suggested: {issue.suggested_action}")
    
    assert validation.confidence_level in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]
    assert validation.requires_manual_review
    assert len(validation.issues) > 0
    assert validation.next_steps is not None
    print("✅ Test 2 PASSED")


def test_suspicious_amount():
    """Test detection of suspicious amounts."""
    print("\n=== Test 3: Suspicious Amount Detection ===")
    
    service = EnhancedValidationService()
    
    azure_result = {
        'confidence': 0.85,
        'doc_type': 'receipt.retail',
        'fields': {
            'MerchantName': {'value': 'Store', 'confidence': 0.80},
            'Total': {'value': 999.99, 'confidence': 0.75},  # Suspicious!
            'Items': {'value': [{'name': 'Item', 'confidence': 0.80}]}
        }
    }
    
    validation = service.validate_receipt(
        azure_result,
        sources_used=['azure'],
        start_time=time.time()
    )
    
    print(f"Confidence Level: {validation.confidence_level}")
    print(f"Issues Found: {len(validation.issues)}")
    
    # Should detect suspicious amount
    suspicious_issues = [i for i in validation.issues if i.issue_type == "suspicious"]
    print(f"Suspicious issues: {len(suspicious_issues)}")
    
    for issue in suspicious_issues:
        print(f"  - {issue.message}")
        print(f"    Action: {issue.suggested_action}")
    
    assert len(suspicious_issues) > 0
    print("✅ Test 3 PASSED")


def test_medium_confidence():
    """Test medium confidence receipt."""
    print("\n=== Test 4: Medium Confidence Receipt ===")
    
    service = EnhancedValidationService()
    
    azure_result = {
        'confidence': 0.78,
        'doc_type': 'receipt.retail',
        'fields': {
            'MerchantName': {'value': 'McDonald\'s', 'confidence': 0.75},
            'Total': {'value': 12.50, 'confidence': 0.72},
            'Items': {'value': [
                {'name': 'Big Mac', 'confidence': 0.70},
                {'name': 'Fries', 'confidence': 0.71}
            ]}
        }
    }
    
    validation = service.validate_receipt(
        azure_result,
        sources_used=['azure', 'google_places'],
        start_time=time.time()
    )
    
    print(f"Confidence Level: {validation.confidence_level}")
    print(f"Overall Confidence: {validation.overall_confidence:.2%}")
    print(f"Requires Review: {validation.requires_manual_review}")
    print(f"Message: {validation.confidence_message}")
    
    assert validation.confidence_level == ConfidenceLevel.MEDIUM
    assert 0.70 <= validation.overall_confidence < 0.85
    print("✅ Test 4 PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Enhanced Validation Service")
    print("=" * 60)
    
    try:
        test_high_confidence_receipt()
        test_low_confidence_receipt()
        test_suspicious_amount()
        test_medium_confidence()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
