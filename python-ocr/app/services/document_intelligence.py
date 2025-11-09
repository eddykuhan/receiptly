from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from typing import Dict, Any, Optional
import io

class DocumentIntelligenceService:
    def __init__(self):
        from ..core.config import get_settings
        settings = get_settings()
        
        if not settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT or not settings.AZURE_DOCUMENT_INTELLIGENCE_KEY:
            raise ValueError("Azure Document Intelligence credentials not properly configured")
        
        self.client = DocumentAnalysisClient(
            endpoint=settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_DOCUMENT_INTELLIGENCE_KEY)
        )

    async def analyze_receipt(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze a receipt using Azure Document Intelligence.
        
        Args:
            file_bytes: The receipt file in bytes
            
        Returns:
            Dictionary containing structured receipt data
        """
        try:
            # Convert bytes to stream
            document_stream = io.BytesIO(file_bytes)
            
            # Analyze the receipt
            poller = self.client.begin_analyze_document(
                "prebuilt-receipt",  # Using the prebuilt receipt model
                document=document_stream
            )
            
            # Wait for the analysis to complete
            result = poller.result()
            
            if len(result.documents) == 0:
                return None
                
            # Get the first document (receipt)
            receipt = result.documents[0]
            
            # Extract structured data
            receipt_data = {}
            
            # Print receipt properties for debugging
            print(f"Receipt fields: {receipt.fields.keys()}")
            print(f"Fields content: {receipt.fields}")
            if "TransactionDate" in receipt.fields:
                print(f"Transaction date field: {receipt.fields['TransactionDate']}")
                print(f"Transaction date type: {type(receipt.fields['TransactionDate'].value)}")
            if "TransactionTime" in receipt.fields:
                print(f"Transaction time field: {receipt.fields['TransactionTime']}")
            
            try:
                # Extract basic receipt information
                transaction_date = None
                if "TransactionDate" in receipt.fields:
                    date_value = receipt.fields["TransactionDate"].value
                    time_value = receipt.fields["TransactionTime"].value if "TransactionTime" in receipt.fields else None
                    
                    # Format the datetime information
                    if isinstance(date_value, str):
                        transaction_date = {
                            "date": date_value,
                            "time": time_value
                        }
                    else:
                        # If it's already a datetime object
                        transaction_date = {
                            "date": date_value.strftime("%Y-%m-%d") if date_value else None,
                            "time": date_value.strftime("%H:%M:%S") if date_value else None
                        }
                        if time_value:  # If there's a separate time field
                            transaction_date["time"] = time_value
                
                receipt_data = {
                    "merchant_name": receipt.fields["MerchantName"].value if "MerchantName" in receipt.fields else None,
                    "transaction_date": transaction_date,
                    "total": receipt.fields["Total"].value if "Total" in receipt.fields else None,
                    "subtotal": receipt.fields["Subtotal"].value if "Subtotal" in receipt.fields else None,
                    "tax": receipt.fields["TotalTax"].value if "TotalTax" in receipt.fields else None,
                    "items": []
                }
                # Extract items if available
                if "Items" in receipt.fields:
                    print("Found Items field")
                    items_field = receipt.fields["Items"]
                    print(f"Items field type: {type(items_field)}")
                    print(f"Items field value type: {type(items_field.value)}")
                    print(f"Items field value: {items_field.value}")
                    
                    items = items_field.value
                    for item in items:
                        print(f"Processing item: {item}")
                        item_value = item.value if hasattr(item, 'value') else {}
                        
                        item_data = {
                            "name": item_value["Description"].value if "Description" in item_value else None,
                            "quantity": item_value["Quantity"].value if "Quantity" in item_value else None,
                            "unit_price": item_value["Price"].value if "Price" in item_value else None,
                            "total_price": item_value["TotalPrice"].value if "TotalPrice" in item_value else None
                        }
                        
                        if item_data:  # Only append if we found any data
                            print(f"Extracted item data: {item_data}")
                            receipt_data["items"].append(item_data)
                else:
                    print("No Items field found in receipt")
            except Exception as e:
                print(f"Error extracting receipt data: {str(e)}")
                # Return whatever data we managed to extract
                
            return receipt_data

        except Exception as e:
            print(f"Error analyzing receipt: {str(e)}")
            raise

    def _get_field_value(self, field: Any) -> Optional[Any]:
        """Helper method to safely get field values"""
        try:
            return field.value if field is not None else None
        except Exception:
            return None