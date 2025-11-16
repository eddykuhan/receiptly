"""
Debug utilities for saving images at various processing stages.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import io
from PIL import Image


class ImageDebugger:
    """Utility class for saving debug images during processing."""
    
    def __init__(self, enabled: bool = False, output_dir: str = "debug_ocr"):
        """
        Initialize the image debugger.
        
        Args:
            enabled: Whether debug mode is enabled
            output_dir: Directory to save debug images
        """
        self.enabled = enabled
        self.output_dir = Path(output_dir)
        self.session_id = None
        
        if self.enabled:
            self._setup_output_dir()
    
    def _setup_output_dir(self):
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Debug output directory: {self.output_dir.absolute()}")
    
    def start_session(self, session_id: Optional[str] = None):
        """
        Start a new debug session.
        
        Args:
            session_id: Optional session identifier. If not provided, uses timestamp.
        """
        if not self.enabled:
            return
        
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        self.session_id = session_id
        session_dir = self.output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🔍 Debug session started: {session_id}")
        print(f"   Output: {session_dir.absolute()}")
        
        return session_id
    
    def save_image(self, image_bytes: bytes, stage: str, metadata: dict = None):
        """
        Save an image at a specific processing stage.
        
        Args:
            image_bytes: Image data as bytes
            stage: Stage identifier (e.g., "01_original", "02_cropped")
            metadata: Optional metadata dictionary
        """
        if not self.enabled or not self.session_id:
            return
        
        if metadata is None:
            metadata = {}
        
        try:
            # Create session directory
            session_dir = self.output_dir / self.session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            filename = f"{stage}.jpg"
            filepath = session_dir / filename
            
            # Save image
            image = Image.open(io.BytesIO(image_bytes))
            image.save(filepath, "JPEG", quality=95)
            
            # Save metadata as JSON
            meta_filename = f"{stage}_metadata.json"
            meta_filepath = session_dir / meta_filename
            
            full_metadata = {
                "stage": stage,
                "timestamp": datetime.now().isoformat(),
                "size_bytes": len(image_bytes),
                "dimensions": f"{image.size[0]}x{image.size[1]}",
                "format": image.format,
                "mode": image.mode,
                **metadata
            }
            
            with open(meta_filepath, 'w') as f:
                json.dump(full_metadata, f, indent=2)
            
            print(f"   💾 Saved: {stage} ({len(image_bytes)} bytes, {image.size[0]}x{image.size[1]})")
            
        except Exception as e:
            print(f"   ⚠️  Failed to save debug image at stage '{stage}': {str(e)}")
            import traceback
            traceback.print_exc()
    
    def save_text(self, text: str, stage: str, metadata: dict = None):
        """
        Save text output at a specific processing stage.
        
        Args:
            text: Text content
            stage: Stage identifier
            metadata: Optional metadata dictionary
        """
        if not self.enabled or not self.session_id:
            return
        
        if metadata is None:
            metadata = {}
        
        try:
            session_dir = self.output_dir / self.session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{stage}.txt"
            filepath = session_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # Save metadata
            meta_filename = f"{stage}_metadata.json"
            meta_filepath = session_dir / meta_filename
            
            full_metadata = {
                "stage": stage,
                "timestamp": datetime.now().isoformat(),
                "length_chars": len(text),
                **metadata
            }
            
            with open(meta_filepath, 'w') as f:
                json.dump(full_metadata, f, indent=2)
            
            print(f"   💾 Saved: {stage} ({len(text)} chars)")
            
        except Exception as e:
            print(f"   ⚠️  Failed to save debug text at stage '{stage}': {str(e)}")
            import traceback
            traceback.print_exc()
    
    def save_json(self, data: dict, stage: str, metadata: dict = None):
        """
        Save JSON data at a specific processing stage.
        
        Args:
            data: Dictionary to save as JSON
            stage: Stage identifier
            metadata: Optional metadata dictionary
        """
        if not self.enabled or not self.session_id:
            return
        
        if metadata is None:
            metadata = {}
        
        try:
            session_dir = self.output_dir / self.session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{stage}.json"
            filepath = session_dir / filename
            
            full_data = {
                'stage': stage,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata,
                'data': data
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(full_data, f, indent=2, ensure_ascii=False)
            
            print(f"   💾 Saved: {stage} (JSON)")
            
        except Exception as e:
            print(f"   ⚠️  Failed to save debug JSON at stage '{stage}': {str(e)}")
            import traceback
            traceback.print_exc()
    
    def end_session(self):
        """End the current debug session."""
        if not self.enabled:
            return
        
        if self.session_id:
            print(f"✅ Debug session completed: {self.session_id}")
            print(f"   Files saved to: {(self.output_dir / self.session_id).absolute()}")
            self.session_id = None


# Global debugger instance
_debugger: Optional[ImageDebugger] = None


def get_debugger(enabled: bool = False) -> ImageDebugger:
    """
    Get or create the global debugger instance.
    
    Args:
        enabled: Whether debug mode should be enabled
        
    Returns:
        ImageDebugger instance
    """
    global _debugger
    
    if _debugger is None:
        _debugger = ImageDebugger(enabled=enabled)
    
    return _debugger


def enable_debug():
    """Enable debug mode."""
    global _debugger
    _debugger = ImageDebugger(enabled=True)
    print("🔍 Debug mode ENABLED")


def disable_debug():
    """Disable debug mode."""
    global _debugger
    if _debugger:
        _debugger.enabled = False
    print("🔍 Debug mode DISABLED")


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled."""
    return _debugger is not None and _debugger.enabled
