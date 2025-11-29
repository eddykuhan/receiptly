"""
Azure Document Intelligence Layout-based receipt boundary detection.
Uses Azure's Layout model to detect document boundaries more accurately.
"""
import io
from typing import Optional, Tuple, List
from PIL import Image
import numpy as np
import cv2
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient


class AzureReceiptDetector:
    """
    Detects receipt boundaries using Azure Document Intelligence Layout model.
    More accurate than pure OpenCV edge detection.
    """
    
    def __init__(self):
        """Initialize Azure Document Intelligence client."""
        from ..core.config import get_settings
        settings = get_settings()
        
        # Validate credentials
        if not settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT or not settings.AZURE_DOCUMENT_INTELLIGENCE_KEY:
            raise ValueError(
                "Azure Document Intelligence credentials not configured. "
                "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY"
            )
        
        # Create client
        self.client = DocumentAnalysisClient(
            endpoint=settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_DOCUMENT_INTELLIGENCE_KEY)
        )
    
    async def detect_and_crop(self, image_bytes: bytes) -> Tuple[bytes, Optional[dict]]:
        """
        Detect receipt boundary using Azure Layout model and crop.
        
        Args:
            image_bytes: Original image bytes
            
        Returns:
            Tuple of (cropped_image_bytes, boundary_info)
        """
        try:
            print("Using Azure Document Intelligence Layout model for boundary detection...")
            
            # Analyze document layout using the same SDK as document_intelligence.py
            document_stream = io.BytesIO(image_bytes)
            
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-layout",
                document=document_stream
            )
            
            result = poller.result()
            
            # Get document boundary polygon
            boundary_polygon = self._get_document_boundary(result)
            
            if not boundary_polygon:
                print("No document boundary detected by Azure Layout model")
                return image_bytes, None
            
            print(f"Detected document boundary with {len(boundary_polygon)} points")
            
            # Crop image using the polygon
            cropped_bytes = self._crop_to_polygon(image_bytes, boundary_polygon)
            
            boundary_info = {
                "polygon": boundary_polygon,
                "method": "azure_layout",
                "page_count": len(result.pages) if result.pages else 0
            }
            
            return cropped_bytes, boundary_info
            
        except Exception as e:
            print(f"Error in Azure layout detection: {str(e)}")
            print("Falling back to original image")
            return image_bytes, None
    
    def _get_document_boundary(self, result) -> Optional[List[Tuple[float, float]]]:
        """
        Extract document boundary polygon from Azure Layout result.
        
        Args:
            result: Azure Document Intelligence analysis result
            
        Returns:
            List of (x, y) coordinates defining the document boundary
        """
        if not result.pages or len(result.pages) == 0:
            return None
        
        # Get the first page
        page = result.pages[0]
        
        # Azure provides page dimensions
        page_width = page.width
        page_height = page.height
        
        print(f"Page dimensions from Azure: {page_width}x{page_height}")
        
        # Option 1: Use bounding polygon if available
        if hasattr(page, 'polygon') and page.polygon:
            polygon = [(point.x, point.y) for point in page.polygon]
            return polygon
        
        # Option 2: Find the bounding box of all content
        if page.lines:
            # Get all line bounding boxes
            all_points = []
            for line in page.lines:
                if hasattr(line, 'polygon') and line.polygon:
                    all_points.extend([(p.x, p.y) for p in line.polygon])
            
            if all_points:
                # Calculate bounding box
                x_coords = [p[0] for p in all_points]
                y_coords = [p[1] for p in all_points]
                
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                
                # Add small padding
                padding = 0.02  # 2% padding
                width = max_x - min_x
                height = max_y - min_y
                
                min_x = max(0, min_x - width * padding)
                max_x = min(page_width, max_x + width * padding)
                min_y = max(0, min_y - height * padding)
                max_y = min(page_height, max_y + height * padding)
                
                # Return as rectangle polygon
                return [
                    (min_x, min_y),  # Top-left
                    (max_x, min_y),  # Top-right
                    (max_x, max_y),  # Bottom-right
                    (min_x, max_y)   # Bottom-left
                ]
        
        # Option 3: Use full page dimensions as fallback
        return [
            (0, 0),
            (page_width, 0),
            (page_width, page_height),
            (0, page_height)
        ]
    
    def _crop_to_polygon(self, image_bytes: bytes, polygon: List[Tuple[float, float]]) -> bytes:
        """
        Crop image to the specified polygon boundary.
        
        Args:
            image_bytes: Original image bytes
            polygon: List of (x, y) coordinates (normalized 0-1 or absolute pixels)
            
        Returns:
            Cropped image bytes
        """
        # Convert bytes to PIL Image
        pil_image = Image.open(io.BytesIO(image_bytes))
        
        # Get image dimensions
        img_width, img_height = pil_image.size
        
        print(f"Image dimensions: {img_width}x{img_height}")
        
        # Convert polygon coordinates to pixel values
        # Azure returns normalized coordinates (0-1), so scale them
        pixel_polygon = []
        for x, y in polygon:
            # Check if coordinates are normalized (0-1) or already in pixels
            if x <= 1.0 and y <= 1.0:
                # Normalized coordinates
                pixel_x = int(x * img_width)
                pixel_y = int(y * img_height)
            else:
                # Already in pixels
                pixel_x = int(x)
                pixel_y = int(y)
            
            pixel_polygon.append((pixel_x, pixel_y))
        
        # Get bounding rectangle from polygon
        x_coords = [p[0] for p in pixel_polygon]
        y_coords = [p[1] for p in pixel_polygon]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        # Ensure coordinates are within image bounds
        min_x = max(0, min_x)
        min_y = max(0, min_y)
        max_x = min(img_width, max_x)
        max_y = min(img_height, max_y)
        
        print(f"Cropping to: ({min_x}, {min_y}) -> ({max_x}, {max_y})")
        
        # Crop image
        cropped = pil_image.crop((min_x, min_y, max_x, max_y))
        
        # Convert back to bytes
        output = io.BytesIO()
        cropped.save(output, format='JPEG', quality=95, optimize=True)
        
        cropped_bytes = output.getvalue()
        print(f"Cropped image size: {len(cropped_bytes) / 1024:.1f} KB")
        
        return cropped_bytes
    
    async def detect_with_visualization(
        self, 
        image_bytes: bytes, 
        output_path: str = None
    ) -> Tuple[bytes, Optional[str]]:
        """
        Detect receipt and save visualization showing Azure's detected boundary.
        
        Args:
            image_bytes: Original image bytes
            output_path: Path to save visualization (optional)
            
        Returns:
            Tuple of (cropped_image_bytes, visualization_path)
        """
        try:
            # Get boundary from Azure
            cropped_bytes, boundary_info = await self.detect_and_crop(image_bytes)
            
            if boundary_info and output_path:
                # Load original image
                pil_image = Image.open(io.BytesIO(image_bytes))
                img_array = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                
                img_width, img_height = pil_image.size
                
                # Draw polygon
                polygon = boundary_info['polygon']
                pixel_polygon = []
                for x, y in polygon:
                    if x <= 1.0 and y <= 1.0:
                        pixel_polygon.append((int(x * img_width), int(y * img_height)))
                    else:
                        pixel_polygon.append((int(x), int(y)))
                
                # Draw the polygon
                pts = np.array(pixel_polygon, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(img_array, [pts], True, (0, 255, 0), 3)
                
                # Draw bounding rectangle
                x_coords = [p[0] for p in pixel_polygon]
                y_coords = [p[1] for p in pixel_polygon]
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                cv2.rectangle(img_array, (min_x, min_y), (max_x, max_y), (255, 0, 0), 2)
                
                # Add label
                cv2.putText(
                    img_array, 
                    "Azure Layout Detection", 
                    (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    1, 
                    (0, 255, 0), 
                    2
                )
                
                # Save visualization
                cv2.imwrite(output_path, img_array)
                print(f"Visualization saved to: {output_path}")
            
            return cropped_bytes, output_path
            
        except Exception as e:
            print(f"Error in visualization: {str(e)}")
            return image_bytes, None
