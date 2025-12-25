"""Step 1: Download image from URL"""

from typing import Optional
from ...utils.image_utils import download_image
from ...utils.debug import ImageDebugger


class ImageDownloadStep:
    """Step 1: Download image from URL"""
    
    async def execute(
        self, 
        image_url: str,
        debugger: Optional[ImageDebugger] = None
    ) -> bytes:
        """
        Download image from provided URL.
        
        Args:
            image_url: URL to download image from
            debugger: Optional debugger instance
            
        Returns:
            Image bytes
        """
        print("Step 1️⃣: Downloading image...")
        file_bytes = await download_image(image_url)
        print(f"  ✓ Downloaded {len(file_bytes)} bytes")
        
        if debugger:
            debugger.save_image(file_bytes, "01_original", {
                "url": image_url,
                "size_bytes": len(file_bytes)
            })
        
        return file_bytes
