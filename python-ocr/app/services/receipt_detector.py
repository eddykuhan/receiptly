"""
Receipt boundary detection and cropping service.
Uses computer vision to detect receipt edges and crop to the receipt area only.
"""
import cv2
import numpy as np
from PIL import Image
import io
from typing import Optional, Tuple


class ReceiptDetector:
    """Detects and crops receipt boundaries from images."""
    
    def __init__(self):
        self.min_area_ratio = 0.1  # Minimum 10% of image should be receipt
        self.max_area_ratio = 0.95  # Maximum 95% of image (avoid full image detection)
    
    def detect_and_crop(self, image_bytes: bytes) -> bytes:
        """
        Detect receipt boundary and crop image to receipt area only.
        
        Args:
            image_bytes: Original image bytes
            
        Returns:
            Cropped image bytes (or original if detection fails)
        """
        try:
            # Convert bytes to numpy array
            image = self._bytes_to_image(image_bytes)
            original_shape = image.shape
            
            print(f"Original image size: {original_shape[1]}x{original_shape[0]}")
            
            # Detect receipt contour
            receipt_contour = self._detect_receipt_contour(image)
            
            if receipt_contour is None:
                print("No receipt boundary detected, using original image")
                return image_bytes
            
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(receipt_contour)
            
            # Calculate area ratio
            receipt_area = w * h
            total_area = original_shape[0] * original_shape[1]
            area_ratio = receipt_area / total_area
            
            print(f"Detected receipt area: {w}x{h} ({area_ratio*100:.1f}% of image)")
            
            # Validate detection
            if not self._validate_detection(area_ratio, w, h):
                print("Receipt detection validation failed, using original image")
                return image_bytes
            
            # Add padding to ensure we don't cut off edges
            padding = 10
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(original_shape[1] - x, w + 2*padding)
            h = min(original_shape[0] - y, h + 2*padding)
            
            # Crop image
            cropped = image[y:y+h, x:x+w]
            
            print(f"Cropped to: {w}x{h} with {padding}px padding")
            
            # Convert back to bytes
            return self._image_to_bytes(cropped)
            
        except Exception as e:
            print(f"Error in receipt detection: {str(e)}")
            print("Returning original image")
            return image_bytes
    
    def _bytes_to_image(self, image_bytes: bytes) -> np.ndarray:
        """Convert image bytes to OpenCV image (numpy array)."""
        # Convert to PIL Image first
        pil_image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Convert to numpy array (OpenCV format)
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    def _detect_receipt_contour(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect the main receipt contour in the image.
        
        Args:
            image: OpenCV image (BGR format)
            
        Returns:
            Receipt contour or None if not found
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection using multiple methods and combine results
        
        # Method 1: Canny edge detection
        edges_canny = cv2.Canny(blurred, 50, 150)
        
        # Method 2: Adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        edges_thresh = cv2.Canny(thresh, 50, 150)
        
        # Combine edges
        edges = cv2.bitwise_or(edges_canny, edges_thresh)
        
        # Dilate edges to close gaps
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return None
        
        # Find the largest contour by area
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Approximate the contour to reduce points
        epsilon = 0.02 * cv2.arcLength(largest_contour, True)
        approx = cv2.approxPolyDP(largest_contour, epsilon, True)
        
        return approx
    
    def _validate_detection(self, area_ratio: float, width: int, height: int) -> bool:
        """
        Validate if the detected area is likely a receipt.
        
        Args:
            area_ratio: Ratio of detected area to total image area
            width: Width of detected area
            height: Height of detected area
            
        Returns:
            True if validation passes
        """
        # Check area ratio
        if area_ratio < self.min_area_ratio or area_ratio > self.max_area_ratio:
            print(f"Area ratio {area_ratio:.2%} outside valid range "
                  f"({self.min_area_ratio:.0%}-{self.max_area_ratio:.0%})")
            return False
        
        # Check minimum dimensions (receipts should be at least 200x200 pixels)
        if width < 200 or height < 200:
            print(f"Detected area too small: {width}x{height}")
            return False
        
        # Check aspect ratio (receipts are typically taller than wide, but not always)
        aspect_ratio = max(width, height) / min(width, height)
        if aspect_ratio > 10:
            print(f"Aspect ratio too extreme: {aspect_ratio:.1f}:1")
            return False
        
        return True
    
    def _image_to_bytes(self, image: np.ndarray) -> bytes:
        """Convert OpenCV image to bytes."""
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(rgb_image)
        
        # Convert to bytes (JPEG format for efficiency)
        output = io.BytesIO()
        pil_image.save(output, format='JPEG', quality=95, optimize=True)
        
        return output.getvalue()
    
    def detect_with_visualization(self, image_bytes: bytes, output_path: str = None) -> Tuple[bytes, Optional[str]]:
        """
        Detect receipt and optionally save visualization showing detection.
        Useful for debugging and testing.
        
        Args:
            image_bytes: Original image bytes
            output_path: Path to save visualization (optional)
            
        Returns:
            Tuple of (cropped_image_bytes, visualization_path)
        """
        try:
            image = self._bytes_to_image(image_bytes)
            contour = self._detect_receipt_contour(image)
            
            # Draw contour on image for visualization
            vis_image = image.copy()
            if contour is not None:
                cv2.drawContours(vis_image, [contour], -1, (0, 255, 0), 3)
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(vis_image, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Save visualization if path provided
            if output_path:
                cv2.imwrite(output_path, vis_image)
                print(f"Visualization saved to: {output_path}")
            
            # Crop the image
            cropped_bytes = self.detect_and_crop(image_bytes)
            
            return cropped_bytes, output_path
            
        except Exception as e:
            print(f"Error in visualization: {str(e)}")
            return image_bytes, None
