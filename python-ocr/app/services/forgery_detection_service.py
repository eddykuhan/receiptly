
"""
Service for detecting forged or AI-generated receipts via metadata analysis.
"""
from PIL import Image, ExifTags
from typing import Dict, Any, List, Optional
import io
import logging

logger = logging.getLogger(__name__)


class ForgeryDetectionService:
    """
    Analyzes image metadata and properties to detect signs of forgery or AI generation.
    """
    
    # Software that often indicates editing/generation
    SUSPICIOUS_SOFTWARE = [
        "adobe", "photoshop", "gimp", "dall-e", "midjourney", 
        "stable diffusion", "paint.net", "canva", "procreate"
    ]
    
    def analyze_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze image for signs of forgery.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Dict containing risk score and flags
        """
        flags = []
        risk_score = 0.0
        details = {}
        
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            # 1. Check EXIF Metadata
            exif_data = image._getexif()
            if exif_data:
                exif = {
                    ExifTags.TAGS.get(k, k): v 
                    for k, v in exif_data.items() 
                    if k in ExifTags.TAGS
                }
                
                # Check Software tag
                software = str(exif.get("Software", "")).lower()
                details["software"] = software
                
                if any(s in software for s in self.SUSPICIOUS_SOFTWARE):
                    flags.append(f"Suspicious software detected: {software}")
                    risk_score += 0.8
                
                # Check for Camera Make/Model (Real receipts usually have this)
                make = exif.get("Make")
                model = exif.get("Model")
                if not make and not model:
                    flags.append("Missing camera Make/Model metadata")
                    risk_score += 0.3
            else:
                # No EXIF data is suspicious for a "phone photo" but common for web images
                flags.append("No EXIF metadata found")
                risk_score += 0.2
            
            # 2. Check Image Dimensions/Mode
            # Exact dimensions (e.g. 1024x1024) are common in AI generators
            width, height = image.size
            if width == 1024 and height == 1024:
                flags.append("Suspicious dimensions (1024x1024)")
                risk_score += 0.4
                
        except Exception as e:
            logger.error(f"Error checking forgery metadata: {e}")
            
        # Cap score at 1.0
        risk_score = min(1.0, risk_score)
        
        return {
            "risk_score": risk_score,
            "flags": flags,
            "details": details,
            "is_suspicious": risk_score > 0.6
        }
