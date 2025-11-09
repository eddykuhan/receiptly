from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
from PIL import Image
import io
import os
import time
from typing import Optional, Dict, Any, List

class AzureVisionService:
    def __init__(self):
        endpoint = os.getenv("AZURE_VISION_ENDPOINT")
        subscription_key = os.getenv("AZURE_VISION_KEY")
        
        if not endpoint or not subscription_key:
            raise ValueError("Azure Vision credentials not properly configured")
        
        self.client = ComputerVisionClient(
            endpoint=endpoint,
            credentials=CognitiveServicesCredentials(subscription_key)
        )

    async def analyze_receipt(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze a receipt image using Azure Computer Vision.
        
        Args:
            image_bytes: The receipt image in bytes
            
        Returns:
            Dictionary containing extracted receipt information
        """
        try:
            # Convert bytes to stream for Azure SDK
            image_stream = io.BytesIO(image_bytes)
            
            # Read the text from the image
            read_response = self.client.read_in_stream(image_stream, raw=True)
            
            # Get the operation location (URL with ID in the response)
            operation_location = read_response.headers["Operation-Location"]
            operation_id = operation_location.split("/")[-1]

            # Wait for the operation to complete
            while True:
                read_result = self.client.get_read_result(operation_id)
                if read_result.status not in [OperationStatusCodes.running, OperationStatusCodes.not_started]:
                    break
                time.sleep(1)

            # Extract the text results
            if read_result.status == OperationStatusCodes.succeeded:
                text_results = []
                for text_result in read_result.analyze_result.read_results:
                    for line in text_result.lines:
                        text_results.append(line.text)
                
                # Process the text results to extract structured data
                receipt_data = self._process_receipt_text(text_results)
                return receipt_data
            else:
                raise Exception("Text extraction failed")

        except Exception as e:
            raise Exception(f"Error processing receipt: {str(e)}")

    def _process_receipt_text(self, text_lines: List[str]) -> Dict[str, Any]:
        """
        Process extracted text lines to identify receipt information.
        
        Args:
            text_lines: List of text lines extracted from the receipt
            
        Returns:
            Dictionary containing structured receipt data
        """
        receipt_data = {
            "store_name": "",
            "store_address": "",
            "date": None,
            "total_amount": None,
            "items": [],
            "tax_amount": None
        }

        # Simple processing logic - can be enhanced with more sophisticated parsing
        for i, line in enumerate(text_lines):
            line_lower = line.lower()
            
            # Try to identify store name (usually in the first few lines)
            if i == 0:
                receipt_data["store_name"] = line
            
            # Look for total amount
            if "total" in line_lower and "$" in line:
                try:
                    # Extract amount using regex or string manipulation
                    amount = float(''.join(filter(lambda x: x.isdigit() or x == '.', line)))
                    receipt_data["total_amount"] = amount
                except:
                    pass
            
            # Look for tax
            if "tax" in line_lower and "$" in line:
                try:
                    tax = float(''.join(filter(lambda x: x.isdigit() or x == '.', line)))
                    receipt_data["tax_amount"] = tax
                except:
                    pass

        return receipt_data