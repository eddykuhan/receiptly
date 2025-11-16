from PIL import Image, ImageEnhance, ImageFilter
import io
import cv2
import numpy as np
from typing import Tuple


class ImagePreprocessor:
    """Preprocesses images to improve OCR accuracy."""
    
    # Processing parameters
    TARGET_DPI = 300
    MIN_WIDTH = 800
    MAX_FILE_SIZE_MB = 4  # Azure limit is 4MB for receipts
    CONTRAST_FACTOR = 1.3  # Reduced from 1.5 to be less aggressive
    SHARPNESS_FACTOR = 1.5  # Reduced from 2.0 to be less aggressive
    
    def __init__(self, enable_binarization: bool = False):
        """
        Initialize the image preprocessor.
        
        Args:
            enable_binarization: Whether to apply black/white conversion (can lose data)
        """
        self.enable_binarization = enable_binarization
    
    def process(self, image_bytes: bytes) -> bytes:
        """
        Apply preprocessing pipeline to improve OCR accuracy.
        
        Args:
            image_bytes: Original image in bytes
            
        Returns:
            Processed image in bytes
        """
        try:
            # Validate input
            if not image_bytes or len(image_bytes) == 0:
                print("Error: Empty image bytes received")
                return image_bytes
            
            # Check if it's a PDF - PDFs don't need image preprocessing
            if image_bytes.startswith(b'%PDF'):
                print("PDF detected - skipping image preprocessing")
                return image_bytes
            
            # Check input size
            input_size_mb = len(image_bytes) / 1024 / 1024
            print(f"Input image size: {input_size_mb:.2f}MB")
            
            # If image is already close to the limit, skip preprocessing to avoid expansion
            if input_size_mb > 3.5:
                print(f"Image is large ({input_size_mb:.2f}MB), skipping preprocessing to avoid size expansion")
                return image_bytes
            
            # Convert bytes to BytesIO and ensure position is at start
            image_stream = io.BytesIO(image_bytes)
            image_stream.seek(0)
            
            # Convert to PIL Image
            image = Image.open(image_stream)
            
            # Verify image was loaded successfully
            image.verify()
            
            # Reopen image after verify (verify() closes the file)
            image_stream.seek(0)
            image = Image.open(image_stream)
            
            # Apply preprocessing pipeline
            image = self._convert_to_rgb(image)
            image = self._resize_if_needed(image)
            image = self._enhance_contrast(image)
            image = self._enhance_sharpness(image)
            image = self._denoise(image)
            image = self._deskew(image)
            
            # Only apply binarization if explicitly enabled
            # Binarization can lose information like addresses
            if self.enable_binarization:
                image = self._binarize(image)
            
            # Convert back to bytes with compression
            processed_bytes = self._image_to_bytes(image, max_size_mb=self.MAX_FILE_SIZE_MB)
            processed_size_mb = len(processed_bytes) / 1024 / 1024
            print(f"Output image size: {processed_size_mb:.2f}MB")
            
            return processed_bytes
        except Exception as e:
            print(f"Error during image preprocessing: {str(e)}")
            print(f"Image bytes length: {len(image_bytes) if image_bytes else 0}")
            
            # Detect file type
            if image_bytes:
                if image_bytes.startswith(b'%PDF'):
                    print("File type: PDF (should have been skipped)")
                elif image_bytes.startswith(b'\xff\xd8\xff'):
                    print("File type: JPEG")
                elif image_bytes.startswith(b'\x89PNG'):
                    print("File type: PNG")
                else:
                    print(f"File type: Unknown - First 20 bytes: {image_bytes[:20]}")
            
            print("Returning original file without preprocessing")
            # Return original image if preprocessing fails
            return image_bytes
    
    # Private methods - Image processing steps
    
    @staticmethod
    def _convert_to_rgb(image: Image.Image) -> Image.Image:
        """Convert image to RGB mode if needed."""
        if image.mode != 'RGB':
            return image.convert('RGB')
        return image
    
    def _resize_if_needed(self, image: Image.Image) -> Image.Image:
        """
        Resize image if it's too small for good OCR.
        
        Args:
            image: PIL Image
            
        Returns:
            Resized image if needed, otherwise original
        """
        width, height = image.size
        
        if width < self.MIN_WIDTH:
            scale_factor = self.MIN_WIDTH / width
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def _enhance_contrast(self, image: Image.Image) -> Image.Image:
        """
        Enhance image contrast to make text more readable.
        
        Args:
            image: PIL Image
            
        Returns:
            Contrast-enhanced image
        """
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(self.CONTRAST_FACTOR)
    
    def _enhance_sharpness(self, image: Image.Image) -> Image.Image:
        """
        Enhance image sharpness to make text edges clearer.
        
        Args:
            image: PIL Image
            
        Returns:
            Sharpness-enhanced image
        """
        enhancer = ImageEnhance.Sharpness(image)
        return enhancer.enhance(self.SHARPNESS_FACTOR)
    
    def _denoise(self, image: Image.Image) -> Image.Image:
        """
        Remove noise from the image while preserving text.
        Uses a gentler approach to preserve all text including addresses.
        
        Args:
            image: PIL Image
            
        Returns:
            Denoised image
        """
        # Convert to OpenCV format
        img_array = np.array(image)
        
        # Apply lighter bilateral filter to preserve more detail
        denoised = cv2.bilateralFilter(img_array, 5, 50, 50)
        
        # Convert back to PIL Image
        return Image.fromarray(denoised)
    
    def _deskew(self, image: Image.Image) -> Image.Image:
        """
        Detect and correct image skew/rotation.
        
        Args:
            image: PIL Image
            
        Returns:
            Deskewed image
        """
        # Convert to OpenCV format
        img_array = np.array(image)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Detect lines using Hough transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is not None and len(lines) > 0:
            # Calculate the dominant angle
            angles = []
            for line in lines[:20]:  # Use first 20 lines
                rho, theta = line[0]
                angle = np.degrees(theta) - 90
                angles.append(angle)
            
            # Get median angle to avoid outliers
            median_angle = np.median(angles)
            
            # Only rotate if skew is significant (more than 0.5 degrees)
            if abs(median_angle) > 0.5:
                # Rotate image
                height, width = img_array.shape[:2]
                center = (width // 2, height // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                rotated = cv2.warpAffine(img_array, rotation_matrix, (width, height), 
                                        flags=cv2.INTER_CUBIC, 
                                        borderMode=cv2.BORDER_REPLICATE)
                return Image.fromarray(rotated)
        
        return image
    
    def _binarize(self, image: Image.Image) -> Image.Image:
        """
        Convert image to black and white using adaptive thresholding.
        This improves text recognition accuracy.
        
        Args:
            image: PIL Image
            
        Returns:
            Binarized image
        """
        # Convert to OpenCV format
        img_array = np.array(image)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            11, 
            2
        )
        
        # Convert back to RGB for consistency
        binary_rgb = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
        
        return Image.fromarray(binary_rgb)
    
    @staticmethod
    def _image_to_bytes(image: Image.Image, max_size_mb: float = 4.0) -> bytes:
        """
        Convert PIL Image to bytes with compression to stay under size limit.
        
        Args:
            image: PIL Image
            max_size_mb: Maximum file size in megabytes (default 4MB for Azure)
            
        Returns:
            Image as bytes in JPEG format with appropriate compression
        """
        output = io.BytesIO()
        
        # Start with high quality JPEG compression
        quality = 95
        max_size_bytes = int(max_size_mb * 1024 * 1024)
        
        # Try different quality levels until we're under the size limit
        while quality >= 60:
            output.seek(0)
            output.truncate()
            
            # Save as JPEG with current quality
            image.save(output, format='JPEG', quality=quality, optimize=True)
            
            # Check size
            size = output.tell()
            if size <= max_size_bytes:
                print(f"Image compressed to {size / 1024 / 1024:.2f}MB with quality={quality}")
                break
            
            # Reduce quality for next iteration
            quality -= 5
            print(f"Image too large ({size / 1024 / 1024:.2f}MB), reducing quality to {quality}")
        
        if quality < 60:
            print(f"Warning: Had to compress to quality={quality} to meet size limit")
        
        return output.getvalue()
