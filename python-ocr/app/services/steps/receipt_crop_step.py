"""Step 2-3: Auto-crop to receipt boundary"""

from typing import Optional, Tuple, Dict, Any
from ...services.receipt_detector import ReceiptDetector
from ...services.azure_receipt_detector import AzureReceiptDetector
from ...utils.debug import ImageDebugger


class ReceiptCropStep:
    """Step 2-3: Auto-crop to receipt boundary"""
    
    def __init__(self):
        self.opencv_detector = ReceiptDetector()
        self.azure_detector = AzureReceiptDetector()
    
    async def execute(
        self,
        file_bytes: bytes,
        auto_crop: bool,
        crop_method: str = "azure_layout",
        debugger: Optional[ImageDebugger] = None
    ) -> Tuple[bytes, Optional[Dict[str, Any]]]:
        """
        Auto-crop to receipt boundary (if enabled).
        
        Args:
            file_bytes: Image bytes
            auto_crop: Whether to enable cropping
            crop_method: "azure_layout" or "opencv"
            debugger: Optional debugger instance
            
        Returns:
            (cropped_image_bytes, boundary_info)
        """
        print("Step 2️⃣: Receipt boundary detection...")
        
        if not auto_crop:
            print("  ℹ️ Auto-crop disabled")
            return file_bytes, None
        
        boundary_info = None
        
        if crop_method == "azure_layout":
            try:
                print("  → Using Azure Layout model...")
                file_bytes, boundary_info = await self.azure_detector.detect_and_crop(file_bytes)
                print(f"  ✓ Cropped: {len(file_bytes)} bytes")
                
                if debugger:
                    debugger.save_image(file_bytes, "02_cropped_azure", {
                        "method": "azure_layout",
                        "size_bytes": len(file_bytes),
                        "boundary_info": boundary_info
                    })
            except Exception as e:
                print(f"  ⚠️ Azure Layout failed: {str(e)}")
                print("  → Falling back to OpenCV...")
                file_bytes = self.opencv_detector.detect_and_crop(file_bytes)
                print(f"  ✓ OpenCV cropped: {len(file_bytes)} bytes")
                
                if debugger:
                    debugger.save_image(file_bytes, "02_cropped_opencv_fallback", {
                        "method": "opencv_fallback",
                        "size_bytes": len(file_bytes),
                        "error": str(e)
                    })
        else:
            print("  → Using OpenCV...")
            file_bytes = self.opencv_detector.detect_and_crop(file_bytes)
            print(f"  ✓ Cropped: {len(file_bytes)} bytes")
            
            if debugger:
                debugger.save_image(file_bytes, "02_cropped_opencv", {
                    "method": "opencv",
                    "size_bytes": len(file_bytes)
                })
        
        return file_bytes, boundary_info
