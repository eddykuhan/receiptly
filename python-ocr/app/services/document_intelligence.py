from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from typing import Dict, Any, Optional, List
import io
from .image_preprocessor import ImagePreprocessor
from ..utils.image_utils import download_image


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
    
    async def analyze_receipt_from_url(self, image_url: str) -> Dict[str, Any]:
        """
        Analyze a receipt from a URL using Azure Document Intelligence.
        Downloads the image, applies preprocessing, and returns raw Azure response.
        
        Args:
            image_url: URL to download the receipt image from
            
        Returns:
            Dictionary containing raw Azure Document Intelligence response
        """
        try:
            # Download image from URL
            print(f"Downloading image from URL: {image_url}")
            file_bytes = await download_image(image_url)
            print(f"Downloaded {len(file_bytes)} bytes")
            
            # Preprocess the image to improve OCR accuracy
            print("Preprocessing image...")
            processed_bytes = self.preprocessor.process(file_bytes)
            print(f"Image preprocessing complete. Output: {len(processed_bytes)} bytes\n")
            
            # Analyze the preprocessed image
            receipt = await self._analyze_document(processed_bytes)
            
            if not receipt:
                return {"error": "No receipt data found"}
            
            # Return raw Azure response
            return receipt.to_dict()
            
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