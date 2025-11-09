from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from typing import Dict, Any, Optional, List
from datetime import datetime
import io
import uuid
from .image_preprocessor import ImagePreprocessor
from .s3_storage import S3StorageService


class DocumentIntelligenceService:
    """Service for analyzing receipts using Azure Document Intelligence."""
    
    RECEIPT_MODEL = "prebuilt-receipt"
    
    def __init__(self):
        """Initialize the Azure Document Intelligence client and image preprocessor."""
        from ..core.config import get_settings
        settings = get_settings()
        
        self._validate_credentials(settings)
        self.client = self._create_client(settings)
        self.preprocessor = ImagePreprocessor()
        
        # Initialize S3 storage (optional - gracefully handles missing config)
        try:
            self.s3_storage = S3StorageService()
            self.s3_enabled = True
            print("S3 storage enabled")
        except ValueError as e:
            print(f"S3 storage disabled: {str(e)}")
            self.s3_storage = None
            self.s3_enabled = False
    
    async def analyze_receipt(
        self, 
        file_bytes: bytes, 
        user_id: str,
        filename: str = "receipt.jpg",
        content_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        """
        Analyze a receipt using Azure Document Intelligence.
        Applies image preprocessing before analysis to improve accuracy.
        Stores all data in S3 with user-based organization.
        
        Args:
            file_bytes: The receipt file in bytes
            user_id: Unique identifier for the user uploading the receipt
            filename: Original filename (optional)
            content_type: MIME type of the uploaded file
            
        Returns:
            Dictionary containing structured receipt data with S3 references
        """
        try:
            # Generate unique receipt ID
            receipt_id = str(uuid.uuid4())
            
            # Preprocess the image to improve OCR accuracy
            print("Preprocessing image...")
            processed_bytes = self.preprocessor.process(file_bytes)
            print("Image preprocessing complete\n")
            
            # Analyze the preprocessed image
            receipt = await self._analyze_document(processed_bytes)
            
            if not receipt:
                return None
            
            # Extract structured data
            receipt_data = self._extract_receipt_data(receipt)
            receipt_data["receipt_id"] = receipt_id
            receipt_data["user_id"] = user_id
            
            # Upload all data to S3 if enabled
            s3_keys = {}
            if self.s3_enabled:
                s3_keys = self.s3_storage.upload_receipt_data(
                    user_id=user_id,
                    receipt_id=receipt_id,
                    original_image=file_bytes,
                    processed_image=processed_bytes,
                    raw_response=receipt.to_dict(),
                    extracted_data=receipt_data,
                    filename=filename,
                    content_type=content_type
                )
            
            # Add S3 references to response
            receipt_data["s3_keys"] = s3_keys
            
            return receipt_data
            
        except Exception as e:
            print(f"Error analyzing receipt: {str(e)}")
            raise
    
    # Private methods - Azure client operations
    
    @staticmethod
    def _validate_credentials(settings) -> None:
        """Validate that Azure credentials are properly configured."""
        if not settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT or not settings.AZURE_DOCUMENT_INTELLIGENCE_KEY:
            raise ValueError("Azure Document Intelligence credentials not properly configured")
    
    @staticmethod
    def _create_client(settings) -> DocumentAnalysisClient:
        """Create and return an Azure Document Analysis client."""
        return DocumentAnalysisClient(
            endpoint=settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_DOCUMENT_INTELLIGENCE_KEY)
        )
    
    async def _analyze_document(self, file_bytes: bytes) -> Optional[Any]:
        """
        Send document to Azure for analysis.
        
        Args:
            file_bytes: The document file in bytes
            
        Returns:
            The first analyzed document or None if no documents found
        """
        document_stream = io.BytesIO(file_bytes)
        
        poller = self.client.begin_analyze_document(
            self.RECEIPT_MODEL,
            document=document_stream
        )
        
        result = poller.result()
        
        return result.documents[0] if len(result.documents) > 0 else None
    
    # Private methods - Data extraction
    
    def _extract_receipt_data(self, receipt: Any) -> Dict[str, Any]:
        """
        Extract structured data from the analyzed receipt.
        
        Args:
            receipt: The analyzed receipt document
            
        Returns:
            Dictionary containing extracted receipt data
        """
        try:
            return {
                "merchant_name": self._extract_merchant_name(receipt),
                "store_location": self._extract_store_location(receipt),
                "transaction_date": self._extract_transaction_date(receipt),
                "total": self._extract_field_value(receipt, "Total"),
                "subtotal": self._extract_field_value(receipt, "Subtotal"),
                "tax": self._extract_field_value(receipt, "TotalTax"),
                "items": self._extract_items(receipt)
            }
        except Exception:
            # Return partial data if extraction fails
            return {}
    
    def _extract_merchant_name(self, receipt: Any) -> Optional[str]:
        """Extract merchant name from receipt."""
        return self._extract_field_value(receipt, "MerchantName")
    
    def _extract_store_location(self, receipt: Any) -> Optional[Dict[str, str]]:
        """Extract store location information from receipt."""
        location = {}
        
        # Debug: Print available merchant-related fields
        merchant_fields = [k for k in receipt.fields.keys() if 'Merchant' in k or 'Address' in k]
        if merchant_fields:
            print(f"Available merchant/address fields: {merchant_fields}")
        
        if "MerchantAddress" in receipt.fields:
            address_value = receipt.fields["MerchantAddress"].value
            print(f"MerchantAddress found: {address_value}")
            location["address"] = address_value
        else:
            print("MerchantAddress field not found in receipt")
        
        if "MerchantPhoneNumber" in receipt.fields:
            phone_value = receipt.fields["MerchantPhoneNumber"].value
            print(f"MerchantPhoneNumber found: {phone_value}")
            location["phone"] = phone_value
        else:
            print("MerchantPhoneNumber field not found in receipt")
        
        return location if location else None
    
    def _extract_transaction_date(self, receipt: Any) -> Optional[Dict[str, str]]:
        """Extract transaction date and time from receipt."""
        if "TransactionDate" not in receipt.fields:
            return None
        
        date_value = receipt.fields["TransactionDate"].value
        time_value = receipt.fields.get("TransactionTime", {}).value if "TransactionTime" in receipt.fields else None
        
        if isinstance(date_value, str):
            return {
                "date": date_value,
                "time": time_value
            }
        
        # Handle datetime objects
        return {
            "date": date_value.strftime("%Y-%m-%d") if date_value else None,
            "time": time_value or (date_value.strftime("%H:%M:%S") if date_value else None)
        }
    
    def _extract_items(self, receipt: Any) -> List[Dict[str, Any]]:
        """Extract line items from receipt."""
        if "Items" not in receipt.fields:
            return []
        
        items = []
        items_field = receipt.fields["Items"].value
        
        for item in items_field:
            item_data = self._extract_item_data(item)
            if item_data:
                items.append(item_data)
        
        return items
    
    def _extract_item_data(self, item: Any) -> Optional[Dict[str, Any]]:
        """
        Extract data from a single receipt item.
        
        Args:
            item: The item field from the receipt
            
        Returns:
            Dictionary containing item data or None if extraction fails
        """
        try:
            item_value = item.value if hasattr(item, 'value') else {}
            
            return {
                "name": item_value["Description"].value if "Description" in item_value else None,
                "quantity": item_value["Quantity"].value if "Quantity" in item_value else None,
                "unit_price": item_value["Price"].value if "Price" in item_value else None,
                "total_price": item_value["TotalPrice"].value if "TotalPrice" in item_value else None
            }
        except Exception:
            return None
    
    def _extract_field_value(self, receipt: Any, field_name: str) -> Optional[Any]:
        """
        Safely extract a field value from the receipt.
        
        Args:
            receipt: The receipt document
            field_name: The name of the field to extract
            
        Returns:
            The field value or None if not found
        """
        if field_name not in receipt.fields:
            return None
        
        try:
            return receipt.fields[field_name].value
        except Exception:
            return None