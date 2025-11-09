import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict
from datetime import datetime
import io
import json


class S3StorageService:
    """Service for uploading files to Amazon S3 with user-based organization."""
    
    def __init__(self):
        """Initialize the S3 client."""
        from ..core.config import get_settings
        settings = get_settings()
        
        self._validate_credentials(settings)
        self.s3_client = self._create_client(settings)
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
    
    def upload_receipt_data(
        self, 
        user_id: str,
        receipt_id: str,
        original_image: bytes,
        processed_image: bytes,
        raw_response: dict,
        extracted_data: dict,
        filename: str,
        content_type: str = "image/jpeg"
    ) -> Dict[str, str]:
        """
        Upload all receipt-related data to S3 with organized structure.
        
        Structure: 
        s3://bucket/users/{user_id}/receipts/{YYYY}/{MM}/{DD}/{receipt_id}/
            - original_image.{ext}
            - processed_image.png
            - raw_response.json
            - extracted_data.json
        
        Args:
            user_id: Unique identifier for the user
            receipt_id: Unique identifier for the receipt
            original_image: Original uploaded image bytes
            processed_image: Preprocessed image bytes
            raw_response: Raw Azure Document Intelligence response
            extracted_data: Extracted structured data
            filename: Original filename
            content_type: MIME type of the original image
            
        Returns:
            Dictionary with S3 keys for all uploaded files
        """
        try:
            # Create organized path structure
            now = datetime.now()
            base_path = self._get_receipt_path(user_id, receipt_id, now)
            
            s3_keys = {}
            
            # 1. Upload original image
            original_ext = self._get_file_extension(filename)
            original_key = f"{base_path}/original_image{original_ext}"
            
            print(f"Uploading original image: {len(original_image)} bytes, type: {content_type}")
            
            self._upload_file(
                key=original_key,
                body=original_image,
                content_type=content_type,
                metadata={
                    'user_id': user_id,
                    'receipt_id': receipt_id,
                    'upload_timestamp': now.isoformat(),
                    'original_filename': filename,
                    'file_type': 'original_image'
                }
            )
            s3_keys['original_image'] = original_key
            print(f"✓ Original image uploaded: {original_key}")
            
            # 2. Upload processed image (always PNG)
            processed_key = f"{base_path}/processed_image.png"
            
            print(f"Uploading processed image: {len(processed_image)} bytes")
            
            self._upload_file(
                key=processed_key,
                body=processed_image,
                content_type='image/png',
                metadata={
                    'user_id': user_id,
                    'receipt_id': receipt_id,
                    'upload_timestamp': now.isoformat(),
                    'file_type': 'processed_image'
                }
            )
            s3_keys['processed_image'] = processed_key
            print(f"✓ Processed image uploaded: {processed_key}")
            
            # 3. Upload raw Azure response
            raw_key = f"{base_path}/raw_response.json"
            self._upload_json(
                key=raw_key,
                data=raw_response,
                metadata={
                    'user_id': user_id,
                    'receipt_id': receipt_id,
                    'upload_timestamp': now.isoformat(),
                    'file_type': 'raw_response'
                }
            )
            s3_keys['raw_response'] = raw_key
            
            # 4. Upload extracted data
            extracted_key = f"{base_path}/extracted_data.json"
            self._upload_json(
                key=extracted_key,
                data=extracted_data,
                metadata={
                    'user_id': user_id,
                    'receipt_id': receipt_id,
                    'upload_timestamp': now.isoformat(),
                    'file_type': 'extracted_data'
                }
            )
            s3_keys['extracted_data'] = extracted_key
            
            # 5. Create index file for easy querying
            index_key = f"{base_path}/index.json"
            index_data = {
                'user_id': user_id,
                'receipt_id': receipt_id,
                'upload_timestamp': now.isoformat(),
                'upload_date': now.strftime('%Y-%m-%d'),
                'original_filename': filename,
                's3_keys': s3_keys,
                'merchant_name': extracted_data.get('merchant_name'),
                'total': extracted_data.get('total'),
                'transaction_date': extracted_data.get('transaction_date')
            }
            self._upload_json(
                key=index_key,
                data=index_data,
                metadata={
                    'user_id': user_id,
                    'receipt_id': receipt_id,
                    'file_type': 'index'
                }
            )
            s3_keys['index'] = index_key
            
            print(f"✓ All receipt data uploaded to S3: {base_path}")
            return s3_keys
            
        except ClientError as e:
            print(f"Error uploading receipt data to S3: {str(e)}")
            return {}
    
    def list_user_receipts(
        self, 
        user_id: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list:
        """
        List all receipts for a user, optionally filtered by date range.
        
        Args:
            user_id: User identifier
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
            
        Returns:
            List of receipt metadata dictionaries
        """
        try:
            prefix = f"users/{user_id}/receipts/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            receipts = []
            if 'Contents' in response:
                # Filter for index files only
                for obj in response['Contents']:
                    if obj['Key'].endswith('/index.json'):
                        # Download and parse index file
                        index_data = self._download_json(obj['Key'])
                        
                        # Apply date filtering if specified
                        if start_date or end_date:
                            upload_date = index_data.get('upload_date')
                            if start_date and upload_date < start_date:
                                continue
                            if end_date and upload_date > end_date:
                                continue
                        
                        receipts.append(index_data)
            
            return receipts
            
        except ClientError as e:
            print(f"Error listing user receipts: {str(e)}")
            return []
    
    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for accessing a file in S3.
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL or None if generation failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            print(f"Error generating presigned URL: {str(e)}")
            return None
    
    # Private methods
    
    @staticmethod
    def _get_receipt_path(user_id: str, receipt_id: str, timestamp: datetime) -> str:
        """
        Generate the S3 path for a receipt.
        Format: users/{user_id}/receipts/{YYYY}/{MM}/{DD}/{receipt_id}
        """
        return (
            f"users/{user_id}/receipts/"
            f"{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/"
            f"{receipt_id}"
        )
    
    @staticmethod
    def _get_file_extension(filename: str) -> str:
        """Extract file extension from filename."""
        if '.' in filename:
            return '.' + filename.rsplit('.', 1)[1].lower()
        return '.jpg'  # default
    
    def _upload_file(
        self, 
        key: str, 
        body: bytes, 
        content_type: str,
        metadata: Dict[str, str]
    ) -> None:
        """Upload a file to S3."""
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=body,
            ContentType=content_type,
            Metadata=metadata
        )
    
    def _upload_json(
        self, 
        key: str, 
        data: dict,
        metadata: Dict[str, str]
    ) -> None:
        """Upload JSON data to S3."""
        json_bytes = json.dumps(data, indent=2, default=str).encode('utf-8')
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=json_bytes,
            ContentType='application/json',
            Metadata=metadata
        )
    
    def _download_json(self, key: str) -> dict:
        """Download and parse JSON file from S3."""
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=key
        )
        return json.loads(response['Body'].read().decode('utf-8'))
    
    @staticmethod
    def _validate_credentials(settings) -> None:
        """Validate that AWS credentials are properly configured."""
        if not settings.AWS_S3_BUCKET_NAME:
            raise ValueError("AWS S3 bucket name not configured")
        
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            raise ValueError("AWS credentials not properly configured")
    
    @staticmethod
    def _create_client(settings):
        """Create and return an S3 client."""
        return boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
