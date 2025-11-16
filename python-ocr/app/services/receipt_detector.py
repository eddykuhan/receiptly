"""
Receipt boundary detection and cropping service.
Uses computer vision to detect receipt edges and crop to the receipt area only.
"""
import cv2
import numpy as np
from PIL import Image
import io
from typing import Optional, Tuple, List


class ReceiptDetector:
    """Detects and crops receipt boundaries from images."""
    
    def __init__(self):
        self.min_area_ratio = 0.05  # Minimum 5% of image should be receipt
        self.max_area_ratio = 0.98  # Maximum 98% of image (allow mostly-filled images)
    
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
            
            # Smart padding based on image size and detection confidence
            # Smaller padding for high-confidence detections (centered, good size)
            center_x = x + w / 2
            center_y = y + h / 2
            img_center_x = original_shape[1] / 2
            img_center_y = original_shape[0] / 2
            
            dist_from_center = np.sqrt(
                ((center_x - img_center_x) / original_shape[1]) ** 2 + 
                ((center_y - img_center_y) / original_shape[0]) ** 2
            )
            
            # Adaptive padding: less padding for centered, well-detected receipts
            if dist_from_center < 0.1 and 0.3 <= area_ratio <= 0.9:
                padding = 5  # High confidence
            elif dist_from_center < 0.3 and 0.2 <= area_ratio <= 0.95:
                padding = 10  # Medium confidence
            else:
                padding = 20  # Lower confidence, use more padding
            
            print(f"Using {padding}px padding (distance from center: {dist_from_center:.2f})")
            
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
        Detect the main receipt contour in the image using improved multi-method approach.
        
        Args:
            image: OpenCV image (BGR format)
            
        Returns:
            Receipt contour or None if not found
        """
        height, width = image.shape[:2]
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Try multiple edge detection strategies and combine results
        all_contours = []
        
        # Strategy 1: Canny edge detection with multiple thresholds
        for low, high in [(30, 100), (50, 150), (70, 200)]:
            edges = cv2.Canny(filtered, low, high)
            kernel = np.ones((3, 3), np.uint8)
            dilated = cv2.dilate(edges, kernel, iterations=1)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            all_contours.extend(contours)
        
        # Strategy 2: Adaptive thresholding
        adaptive = cv2.adaptiveThreshold(
            filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        # Invert if needed (receipt is usually white on dark background or vice versa)
        if np.mean(adaptive) > 127:
            adaptive = cv2.bitwise_not(adaptive)
        
        kernel = np.ones((5, 5), np.uint8)
        morph = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        all_contours.extend(contours)
        
        # Strategy 3: Color-based detection (receipts are often white/light colored)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # Detect bright areas (potential receipt)
        _, saturation, value = cv2.split(hsv)
        bright_mask = cv2.threshold(value, 180, 255, cv2.THRESH_BINARY)[1]
        kernel = np.ones((7, 7), np.uint8)
        bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        all_contours.extend(contours)
        
        if not all_contours:
            return None
        
        # Filter contours by area and find the best candidate
        min_area = (width * height) * 0.05  # At least 5% of image
        valid_contours = [c for c in all_contours if cv2.contourArea(c) >= min_area]
        
        if not valid_contours:
            return None
        
        # Find the best contour based on multiple criteria
        best_contour = self._select_best_contour(valid_contours, width, height)
        
        if best_contour is None:
            return None
        
        # Approximate the contour to get cleaner polygon
        epsilon = 0.01 * cv2.arcLength(best_contour, True)
        approx = cv2.approxPolyDP(best_contour, epsilon, True)
        
        return approx
    
    def _select_best_contour(self, contours: List[np.ndarray], img_width: int, img_height: int) -> Optional[np.ndarray]:
        """
        Select the best contour from candidates using scoring system.
        
        Args:
            contours: List of candidate contours
            img_width: Image width
            img_height: Image height
            
        Returns:
            Best contour or None
        """
        if not contours:
            return None
        
        img_area = img_width * img_height
        scores = []
        
        for contour in contours:
            score = 0
            area = cv2.contourArea(contour)
            x, y, w, h = cv2.boundingRect(contour)
            
            # Score based on area (prefer substantial but not full-image contours)
            area_ratio = area / img_area
            if 0.1 <= area_ratio <= 0.85:
                score += 100
            elif 0.05 <= area_ratio < 0.1 or 0.85 < area_ratio <= 0.98:
                score += 50
            else:
                score += 10
            
            # Score based on aspect ratio (receipts are typically vertical)
            aspect = h / w if w > 0 else 0
            if 1.2 <= aspect <= 4.0:  # Vertical receipt
                score += 50
            elif 0.25 <= aspect <= 1.2:  # Horizontal or square
                score += 30
            
            # Score based on rectangularity (how close to a rectangle)
            rect_area = w * h
            if rect_area > 0:
                rectangularity = area / rect_area
                if rectangularity >= 0.8:
                    score += 40
                elif rectangularity >= 0.6:
                    score += 20
            
            # Score based on position (receipts tend to be centered)
            center_x = x + w / 2
            center_y = y + h / 2
            img_center_x = img_width / 2
            img_center_y = img_height / 2
            
            dist_from_center = np.sqrt(
                ((center_x - img_center_x) / img_width) ** 2 + 
                ((center_y - img_center_y) / img_height) ** 2
            )
            
            if dist_from_center < 0.2:  # Very centered
                score += 30
            elif dist_from_center < 0.4:  # Somewhat centered
                score += 15
            
            # Penalize if touching image borders (likely background)
            border_margin = 5
            touches_border = (
                x <= border_margin or 
                y <= border_margin or 
                x + w >= img_width - border_margin or 
                y + h >= img_height - border_margin
            )
            if touches_border:
                score -= 20
            
            scores.append((score, contour))
        
        # Return contour with highest score
        scores.sort(key=lambda x: x[0], reverse=True)
        best_score, best_contour = scores[0]
        
        # Only return if score is reasonable
        if best_score >= 50:
            return best_contour
        
        return None
    
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
        # Check area ratio - be more lenient
        if area_ratio < self.min_area_ratio:
            print(f"Area ratio {area_ratio:.2%} too small (minimum {self.min_area_ratio:.0%})")
            return False
        
        # Allow near-full image if it's a well-captured receipt
        if area_ratio > self.max_area_ratio:
            print(f"Area ratio {area_ratio:.2%} exceeds maximum ({self.max_area_ratio:.0%})")
            # Still return True if it's close to full image (likely a good receipt photo)
            if area_ratio >= 0.95:
                print("  But allowing it as it's likely a well-captured receipt")
                return True
            return False
        
        # Check minimum dimensions (receipts should be at least 100x100 pixels)
        if width < 100 or height < 100:
            print(f"Detected area too small: {width}x{height} (minimum 100x100)")
            return False
        
        # Check aspect ratio (receipts can vary, be more permissive)
        aspect_ratio = max(width, height) / min(width, height)
        if aspect_ratio > 15:
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
