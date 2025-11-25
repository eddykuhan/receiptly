"""
Integration Script - How to use the Receipt NER Model with OCR
This demonstrates how to integrate the model with your existing OCR system
"""

from train_model import ReceiptNERModel
import json



class ReceiptParser:
    """Parse receipt text to extract merchant and location"""
    
    def __init__(self, model_path='receipt_ner_model.pkl'):
        """Initialize with trained model"""
        self.model = ReceiptNERModel()
        self.model.load_model(model_path)
    
    def extract_header_from_ocr(self, ocr_text, num_lines=3):
        """
        Extract header text from OCR output
        Usually merchant and location are in the first few lines
        
        Args:
            ocr_text: Full OCR text from receipt
            num_lines: Number of lines to consider as header (default: 3)
        
        Returns:
            str: Header text
        """
        lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
        header_lines = lines[:num_lines]
        return ' '.join(header_lines)
    
    def parse_receipt(self, ocr_text):
        """
        Parse OCR text to extract merchant and location
        
        Args:
            ocr_text: Full text extracted from receipt via OCR
        
        Returns:
            dict: Parsed information with merchant, location, and confidence scores
        """
        # Extract header (first few lines usually contain merchant/location)
        header = self.extract_header_from_ocr(ocr_text)
        
        # Predict merchant and location
        result = self.model.predict(header)
        
        return {
            'header_text': header,
            'merchant': result['merchant'],
            'location': result['location'],
            'merchant_confidence': result['merchant_confidence'],
            'location_confidence': result['location_confidence']
        }


# Example usage with simulated OCR text
def example_basic():
    """Basic example of parsing receipt"""
    print("=" * 70)
    print("Example 1: Basic Receipt Parsing")
    print("=" * 70)
    
    # Simulated OCR output from a receipt
    ocr_text = """
    MYDIN WHOLESALE HYPERMARKET
    BUKIT MERTAJAM
    NO. 123, JALAN PERMAI
    
    Date: 23/11/2025
    Time: 14:30
    
    Item 1    RM 10.50
    Item 2    RM 25.00
    Total     RM 35.50
    """
    
    # Parse receipt
    parser = ReceiptParser()
    result = parser.parse_receipt(ocr_text)
    
    print("\nOCR Text (first 3 lines):")
    print(result['header_text'])
    print("\n" + "-" * 70)
    print(f"🏪 Merchant: {result['merchant']}")
    print(f"   Confidence: {result['merchant_confidence']:.2%}")
    print(f"\n📍 Location: {result['location']}")
    print(f"   Confidence: {result['location_confidence']:.2%}")
    print("-" * 70)


def example_multiple_receipts():
    """Example with multiple receipts"""
    print("\n\n" + "=" * 70)
    print("Example 2: Processing Multiple Receipts")
    print("=" * 70)
    
    receipts = [
        """
        JAYA GROCER
        KL EAST MALL
        Ground Floor
        Receipt #12345
        """,
        """
        Starbucks Coffee
        Pavilion KL
        Level 3
        """,
        """
        99 SPEEDMART
        TAMAN MELAWATI OUTLET
        TRX: 00123
        """
    ]
    
    parser = ReceiptParser()
    
    for i, receipt in enumerate(receipts, 1):
        print(f"\n--- Receipt {i} ---")
        result = parser.parse_receipt(receipt)
        print(f"Merchant: {result['merchant']} ({result['merchant_confidence']:.0%})")
        print(f"Location: {result['location']} ({result['location_confidence']:.0%})")


def example_with_azure_ocr():
    """Example showing integration with Azure OCR API"""
    print("\n\n" + "=" * 70)
    print("Example 3: Integration with Azure OCR (Pseudocode)")
    print("=" * 70)
    
    pseudocode = """
# Pseudocode for Azure OCR Integration

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from train_model import ReceiptNERModel

def process_receipt_image(image_path):
    # 1. Use Azure OCR to extract text
    vision_client = ComputerVisionClient(endpoint, credentials)
    with open(image_path, 'rb') as image:
        ocr_result = vision_client.read_in_stream(image, raw=True)
    
    # Get operation ID and wait for result
    operation_id = ocr_result.headers['Operation-Location'].split('/')[-1]
    result = vision_client.get_read_result(operation_id)
    
    # Extract text from result
    ocr_text = ""
    for page in result.analyze_result.read_results:
        for line in page.lines:
            ocr_text += line.text + "\\n"
    
    # 2. Use our NER model to extract merchant and location
    parser = ReceiptParser()
    parsed_data = parser.parse_receipt(ocr_text)
    
    # 3. Combine with other Azure-extracted fields
    receipt_data = {
        'merchant': parsed_data['merchant'],
        'location': parsed_data['location'],
        'total': result.analyze_result.documents[0].fields.get('Total'),
        'date': result.analyze_result.documents[0].fields.get('TransactionDate'),
        'items': result.analyze_result.documents[0].fields.get('Items'),
        'raw_ocr_text': ocr_text
    }
    
    return receipt_data
    """
    
    print(pseudocode)


def example_api_endpoint():
    """Example of creating an API endpoint"""
    print("\n\n" + "=" * 70)
    print("Example 4: Flask API Endpoint (Pseudocode)")
    print("=" * 70)
    
    pseudocode = """
# Flask API Example

from flask import Flask, request, jsonify
from train_model import ReceiptNERModel

app = Flask(__name__)
parser = ReceiptParser()

@app.route('/api/parse-receipt', methods=['POST'])
def parse_receipt():
    '''
    API endpoint to parse receipt text
    
    Request body:
    {
        "ocr_text": "MYDIN WHOLESALE HYPERMARKET\\nBUKIT MERTAJAM\\n..."
    }
    
    Response:
    {
        "success": true,
        "data": {
            "merchant": "MYDIN",
            "location": "BUKIT_MERTAJAM",
            "merchant_confidence": 0.95,
            "location_confidence": 0.92
        }
    }
    '''
    try:
        data = request.get_json()
        ocr_text = data.get('ocr_text', '')
        
        if not ocr_text:
            return jsonify({'success': False, 'error': 'No OCR text provided'}), 400
        
        result = parser.parse_receipt(ocr_text)
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    """
    
    print(pseudocode)


def main():
    """Run all examples"""
    example_basic()
    example_multiple_receipts()
    example_with_azure_ocr()
    example_api_endpoint()
    
    print("\n\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("""
The ReceiptParser class provides a simple interface to:
1. Extract header text from OCR output (usually first 3 lines)
2. Predict merchant and location from header text
3. Return confidence scores for predictions

Integration steps:
1. Get OCR text from your OCR system (Azure/Tesseract/etc)
2. Pass it to parser.parse_receipt(ocr_text)
3. Get structured merchant and location data
4. Use in your application!

For production use:
- Add more training data (50-100+ examples per merchant)
- Include OCR error variations in training data
- Consider using confidence thresholds (e.g., > 70%)
- Implement fallback logic for low-confidence predictions
    """)


if __name__ == "__main__":
    main()
