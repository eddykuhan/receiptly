"""
Receipt Text Prediction Script
Use this script to predict merchant and location from new receipt text
"""

import joblib
import numpy as np
import re
from typing import Dict, Any, Optional


class ReceiptPredictor:
    """Predicts merchant and location from receipt text using trained models"""
    
    def __init__(self):
        self.embedder = None
        self.clf_merchant = None
        self.clf_location = None
    
    def extract_street_name(self, text: str) -> Optional[str]:
        """
        Extract street name from receipt text using pattern matching
        
        Args:
            text: Receipt text to analyze
            
        Returns:
            Extracted street name or None if not found
        """
        # Common street patterns
        street_patterns = [
            # Street types: St, Street, Ave, Avenue, Rd, Road, Blvd, Boulevard, etc.
            r'\d+\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:St(?:reet)?|Ave(?:nue)?|Rd|Road|Blvd|Boulevard|Dr(?:ive)?|Ln|Lane|Way|Ct|Court|Pl|Place|Pkwy|Parkway)\b',
            # Canadian/UK: Street name before number
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:St(?:reet)?|Ave(?:nue)?|Rd|Road)\s+\d+',
            # Street without number
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+(?:St(?:reet)?|Ave(?:nue)?|Rd|Road|Blvd|Boulevard)',
        ]
        
        for pattern in street_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_address_components(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract all address components from receipt text
        
        Args:
            text: Receipt text to analyze
            
        Returns:
            Dictionary with street, city, postal_code, and full_address
        """
        result = {
            "street": None,
            "city": None,
            "postal_code": None,
            "full_address": None
        }
        
        # Extract postal code (Canadian format: A1A 1A1)
        postal_match = re.search(r'\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b', text, re.IGNORECASE)
        if postal_match:
            result["postal_code"] = postal_match.group(0)
        
        # Extract US ZIP code
        zip_match = re.search(r'\b\d{5}(?:-\d{4})?\b', text)
        if zip_match and not postal_match:
            result["postal_code"] = zip_match.group(0)
        
        # Extract street
        result["street"] = self.extract_street_name(text)
        
        # Extract city (usually before postal/zip code)
        if result["postal_code"]:
            city_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*,?\s*[A-Z]{2}\s*' + re.escape(result["postal_code"])
            city_match = re.search(city_pattern, text)
            if city_match:
                result["city"] = city_match.group(1)
        
        # Try to extract full address line
        address_pattern = r'\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:St|Street|Ave|Avenue|Rd|Road).*?(?=\n|$)'
        address_match = re.search(address_pattern, text, re.MULTILINE)
        if address_match:
            result["full_address"] = address_match.group(0).strip()
        
        return result
        
    def load_models(self):
        """Load trained models from disk"""
        try:
            self.embedder = joblib.load("embedding_model.pkl")
            self.clf_merchant = joblib.load("merchant_classifier.pkl")
            self.clf_location = joblib.load("location_classifier.pkl")
            print("✓ Models loaded successfully")
        except FileNotFoundError as e:
            print(f"\n❌ Error: Model files not found!")
            print(f"   {e}")
            print("\nPlease run 'python train_model.py' first to train the models.")
            raise
    
    def predict(self, text: str) -> Dict[str, Any]:
        """
        Predict merchant and location from receipt header text
        
        Args:
            text: Receipt header text to analyze
            
        Returns:
            Dictionary containing:
            - merchant: Predicted merchant name
            - merchant_confidence: Confidence score (0-1)
            - location: Predicted location
            - location_confidence: Confidence score (0-1)
        """
        if not all([self.embedder, self.clf_merchant, self.clf_location]):
            raise RuntimeError("Models not loaded. Call load_models() first.")
        
        # Convert text to embedding
        embedding = self.embedder.encode([text])
        
        # Predict merchant
        merchant_pred = self.clf_merchant.predict(embedding)[0]
        merchant_proba = self.clf_merchant.predict_proba(embedding)[0]
        merchant_confidence = np.max(merchant_proba)
        
        # Predict location
        location_pred = self.clf_location.predict(embedding)[0]
        location_proba = self.clf_location.predict_proba(embedding)[0]
        location_confidence = np.max(location_proba)
        
        # Extract address components
        address_info = self.extract_address_components(text)
        
        return {
            "merchant": merchant_pred,
            "merchant_confidence": float(merchant_confidence),
            "location": location_pred,
            "location_confidence": float(location_confidence),
            "address": address_info
        }


def predict_from_receipt(text: str) -> Dict[str, Any]:
    """
    Convenience function to predict merchant and location from receipt text
    
    Args:
        text: Receipt header text
        
    Returns:
        Prediction results dictionary
    """
    predictor = ReceiptPredictor()
    predictor.load_models()
    return predictor.predict(text)


def main():
    """Interactive prediction script"""
    print("=" * 60)
    print("Receipt Merchant & Location Predictor")
    print("=" * 60)
    print("Enter receipt header text to extract merchant and location")
    print("Type 'quit' to exit")
    print("=" * 60)
    
    # Load models once at startup
    predictor = ReceiptPredictor()
    try:
        predictor.load_models()
    except FileNotFoundError:
        return
    
    while True:
        print("\n")
        text = input("Enter receipt text: ").strip()
        
        if text.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not text:
            print("Please enter some text")
            continue
        
        # Make prediction
        try:
            result = predictor.predict(text)
            
            print("\n" + "-" * 60)
            print(f"📍 Merchant: {result['merchant']}")
            print(f"   Confidence: {result['merchant_confidence']:.2%}")
            print(f"\n📌 Location: {result['location']}")
            print(f"   Confidence: {result['location_confidence']:.2%}")
            
            # Show address components
            if result.get('address'):
                addr = result['address']
                if any([addr['street'], addr['city'], addr['postal_code'], addr['full_address']]):
                    print(f"\n🏠 Address Details:")
                    if addr['street']:
                        print(f"   Street: {addr['street']}")
                    if addr['city']:
                        print(f"   City: {addr['city']}")
                    if addr['postal_code']:
                        print(f"   Postal: {addr['postal_code']}")
                    if addr['full_address']:
                        print(f"   Full: {addr['full_address']}")
            
            print("-" * 60)
        except Exception as e:
            print(f"\n❌ Error during prediction: {e}")


if __name__ == "__main__":
    main()