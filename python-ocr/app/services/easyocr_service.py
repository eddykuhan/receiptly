"""
EasyOCR Service for extracting store location and address information from receipts.
"""
import easyocr
from PIL import Image
import io
import re
from typing import Dict, Any, Optional, List
import cv2
import numpy as np
from datetime import datetime


class EasyOCRService:
    """Service for extracting store location using EasyOCR."""
    
    def __init__(self, debug_mode: bool = False, languages: List[str] = None):
        """
        Initialize the EasyOCR service.
        
        Args:
            debug_mode: If True, saves preprocessed images for debugging
            languages: List of language codes (default: ['en'])
        """
        self.debug_mode = debug_mode
        self.languages = languages or ['en']
        
        # Initialize EasyOCR reader (lazy loading to save memory)
        self._reader = None
        
        # Common store location keywords to help identify location sections
        self.location_keywords = [
            'address', 'location', 'store', 'branch', 'outlet',
            'street', 'road', 'avenue', 'blvd', 'drive', 'lane',
            'city', 'state', 'zip', 'postal', 'phone', 'tel',
            'level', 'floor', 'unit', '#'
        ]
        
        # Common country patterns
        self.country_patterns = {
            'singapore': r'\bsingapore\b|\bs\s*\d{6}\b',
            'malaysia': r'\bmalaysia\b|\bkl\b|\bselangor\b',
            'usa': r'\b\d{5}(?:-\d{4})?\b',  # ZIP code
            'uk': r'\b[A-Z]{1,2}\d{1,2}\s*\d[A-Z]{2}\b'  # UK postcode
        }
    
    @property
    def reader(self):
        """Lazy load the EasyOCR reader."""
        if self._reader is None:
            print(f"Initializing EasyOCR reader with languages: {self.languages}")
            self._reader = easyocr.Reader(self.languages, gpu=False)
        return self._reader
    
    def extract_location_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Extract store location information from receipt image bytes.
        Tries multiple preprocessing strategies for best results.
        
        Args:
            image_bytes: Receipt image in bytes
            
        Returns:
            Dictionary containing extracted location information
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Try multiple preprocessing strategies
            strategies = [
                ('full_image', self._preprocess_full_image),  # Try full image first
                ('enhanced', self._preprocess_for_location_ocr),
                ('simple', self._preprocess_simple),
                ('high_contrast', self._preprocess_high_contrast)
            ]
            
            best_result = None
            best_score = 0
            
            for strategy_name, preprocess_func in strategies:
                try:
                    # Preprocess image
                    processed_image = preprocess_func(image)
                    
                    # Debug: Save preprocessed image
                    if self.debug_mode:
                        import os
                        debug_dir = 'debug_ocr'
                        os.makedirs(debug_dir, exist_ok=True)
                        debug_path = os.path.join(debug_dir, f'{strategy_name}_{id(image)}.png')
                        processed_image.save(debug_path)
                        print(f"[DEBUG] Saved {strategy_name} image to: {debug_path}")
                    
                    # Convert to numpy array for EasyOCR
                    img_array = np.array(processed_image)
                    
                    # Extract text using EasyOCR
                    results = self.reader.readtext(img_array)
                    
                    # Combine all detected text
                    full_text = '\n'.join([text for (bbox, text, conf) in results])
                    
                    if self.debug_mode:
                        print(f"[DEBUG] Strategy '{strategy_name}' extracted {len(results)} text regions")
                        print(f"[DEBUG] Sample text: {full_text[:200]}")
                    
                    # Extract location information
                    location_info = self._extract_location_info(full_text, results)
                    
                    # Score this result
                    score = location_info.get('confidence', 0.0)
                    # Bonus for finding store name
                    if location_info.get('store_name'):
                        score += 0.2
                    # Bonus for finding address
                    if location_info.get('address'):
                        score += 0.3
                    
                    if self.debug_mode:
                        print(f"[DEBUG] Strategy '{strategy_name}' score: {score:.2f}")
                        print(f"[DEBUG] Store name: {location_info.get('store_name', 'N/A')}")
                        print(f"[DEBUG] Address: {location_info.get('address', 'N/A')[:50] if location_info.get('address') else 'N/A'}")
                    
                    if score > best_score:
                        best_score = score
                        best_result = {
                            "success": True,
                            "location": location_info,
                            "raw_text": full_text[:500],
                            "confidence": location_info.get('confidence', 0.0),
                            "strategy_used": strategy_name
                        }
                        
                except Exception as e:
                    if self.debug_mode:
                        print(f"[DEBUG] Strategy '{strategy_name}' failed: {str(e)}")
                    continue
            
            if best_result:
                return best_result
            else:
                return {
                    "success": False,
                    "error": "All preprocessing strategies failed",
                    "location": None
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "location": None
            }
    
    
    def _preprocess_full_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess full image with minimal cropping.
        Good for receipts where address might be in middle section.
        
        Args:
            image: PIL Image
            
        Returns:
            Preprocessed PIL Image
        """
        # Convert PIL to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Use top 50% of image (more than location-only preprocessing)
        height = gray.shape[0]
        width = gray.shape[1]
        top_section = gray[:int(height * 0.25), :]
        
        # Resize if too small
        if width < 1200:
            scale_factor = 1200 / width
            new_width = int(width * scale_factor)
            new_height = int(top_section.shape[0] * scale_factor)
            top_section = cv2.resize(top_section, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Light denoising
        denoised = cv2.bilateralFilter(top_section, 5, 50, 50)
        
        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Convert back to PIL
        return Image.fromarray(enhanced)
    
    def _preprocess_for_location_ocr(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image specifically for location extraction.
        Focus on the top portion where store info is usually located.
        Uses multiple techniques to enhance text clarity.
        
        Args:
            image: PIL Image
            
        Returns:
            Preprocessed PIL Image
        """
        # Convert PIL to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Focus on top 25% of image (where store info usually is)
        height = gray.shape[0]
        width = gray.shape[1]
        top_section = gray[:int(height * 0.25), :]
        
        # Resize if too small (OCR works better with larger images)
        if width < 1000:
            scale_factor = 1000 / width
            new_width = int(width * scale_factor)
            new_height = int(top_section.shape[0] * scale_factor)
            top_section = cv2.resize(top_section, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Apply bilateral filter to reduce noise while keeping edges sharp
        denoised = cv2.bilateralFilter(top_section, 9, 75, 75)
        
        # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Apply adaptive thresholding for better text recognition
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
        
        # Morphological operations to clean up text
        kernel = np.ones((1, 1), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Optional: Invert if background is dark
        if np.mean(binary) < 127:
            binary = cv2.bitwise_not(binary)
        
        # Convert back to PIL
        return Image.fromarray(binary)
    
    def _preprocess_simple(self, image: Image.Image) -> Image.Image:
        """
        Simple preprocessing - just grayscale and resize.
        Sometimes works better for clear receipts.
        """
        img_array = np.array(image)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Focus on top 25%
        height = gray.shape[0]
        width = gray.shape[1]
        top_section = gray[:int(height * 0.25), :]
        
        # Resize if needed
        if width < 1500:
            scale_factor = 1500 / width
            new_width = int(width * scale_factor)
            new_height = int(top_section.shape[0] * scale_factor)
            top_section = cv2.resize(top_section, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        return Image.fromarray(top_section)
    
    def _preprocess_high_contrast(self, image: Image.Image) -> Image.Image:
        """
        High contrast preprocessing for faded receipts.
        """
        img_array = np.array(image)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Focus on top 25%
        height = gray.shape[0]
        width = gray.shape[1]
        top_section = gray[:int(height * 0.25), :]
        
        # Resize
        if width < 1500:
            scale_factor = 1500 / width
            new_width = int(width * scale_factor)
            new_height = int(top_section.shape[0] * scale_factor)
            top_section = cv2.resize(top_section, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Aggressive contrast enhancement
        # Normalize to full range
        normalized = cv2.normalize(top_section, None, 0, 255, cv2.NORM_MINMAX)
        
        # Apply Otsu's thresholding
        _, binary = cv2.threshold(normalized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Invert if needed
        if np.mean(binary) < 127:
            binary = cv2.bitwise_not(binary)
        
        return Image.fromarray(binary)
    
    def _extract_location_info(self, text: str, ocr_results: List) -> Dict[str, Any]:
        """
        Extract structured location information from OCR text.
        
        Args:
            text: Full OCR text
            ocr_results: List of (bbox, text, confidence) tuples from EasyOCR
            
        Returns:
            Dictionary with extracted location details
        """
        lines = text.split('\n')
        
        # Extract different location components
        store_name = self._extract_store_name(lines, ocr_results)
        address = self._extract_address(lines, ocr_results, store_name)  # Pass store_name to exclude it
        phone = self._extract_phone(lines)
        postal_code = self._extract_postal_code(text)
        country = self._detect_country(text)
        
        # Extract transaction date
        date_info = self.extract_date_from_text(text)
        
        # Calculate confidence based on how much info we found
        confidence = self._calculate_location_confidence(
            store_name, address, phone, postal_code, country
        )
        
        result = {
            "store_name": store_name,
            "address": address,
            "phone": phone,
            "postal_code": postal_code,
            "country": country,
            "confidence": confidence,
            "full_location_text": self._get_location_section(lines)
        }
        
        # Add date information if found
        if date_info:
            result["transaction_date"] = date_info
        
        return result
    
    def _extract_store_name(self, lines: List[str], ocr_results: List) -> Optional[str]:
        """
        Extract store name (usually first non-empty line with significant text).
        Filters out noise and common OCR errors.
        Uses confidence scores from EasyOCR to prioritize high-confidence text.
        """
        # Sort OCR results by Y-coordinate (top to bottom)
        sorted_results = sorted(ocr_results, key=lambda x: x[0][0][1])  # Sort by top-left Y
        
        # Get t top 10 results (likely header area)
        for bbox, text, conf in sorted_results[:10]:
            text = text.strip()
            
            # Skip empty or very short lines
            if len(text) < 3:
                continue
            
            # Skip if confidence is too low
            if conf < 0.5:
                continue
            
            # Skip lines that are purely numeric (likely not a store name)
            if text.replace(' ', '').replace('.', '').replace('-', '').isdigit():
                continue
            
            # Skip common noise patterns
            noise_patterns = ['|', '===', '---', '___', '***']
            if any(pattern in text for pattern in noise_patterns):
                continue
            
            # Skip if it looks like a date
            if any(word in text.lower() for word in ['date', 'time', 'am', 'pm']):
                continue
            
            # Check if line is gibberish
            if self._is_gibberish(text):
                continue
            
            # If line has mostly letters (good sign for store name)
            letter_count = sum(c.isalpha() for c in text)
            if letter_count >= 3:  # At least 3 letters
                # Final length check - store names shouldn't be extremely long
                if len(text) <= 100:  # Reasonable max length
                    return text
        
        # Fallback to line-based extraction
        for line in lines[:10]:
            line = line.strip()
            if len(line) >= 3 and not self._is_gibberish(line):
                letter_count = sum(c.isalpha() for c in line)
                if letter_count >= 3 and len(line) <= 100:
                    return line
        
        return None
    
    def _is_gibberish(self, text: str) -> bool:
        """
        Detect if text is likely gibberish/noise from bad OCR.
        
        Returns True if text appears to be gibberish.
        """
        if not text or len(text) < 3:
            return True
        
        # Check for excessive length
        if len(text) > 200:
            return True
        
        # Count character types
        letter_count = sum(c.isalpha() for c in text)
        special_count = sum(not c.isalnum() and not c.isspace() for c in text)
        total_chars = len(text)
        
        if total_chars == 0:
            return True
        
        letter_ratio = letter_count / total_chars
        special_ratio = special_count / total_chars
        
        # Gibberish indicators
        if letter_ratio < 0.3:
            return True
        
        if special_ratio > 0.4:
            return True
        
        # Check for valid words
        words = text.split()
        valid_words = [w for w in words if len(w) >= 3 and any(c.isalpha() for c in w)]
        if len(valid_words) == 0:
            return True
        
        return False
    
    def _extract_address(self, lines: List[str], ocr_results: List = None, store_name: str = None) -> Optional[str]:
        """
        Extract address lines containing street, building info, or location names.
        Uses fuzzy matching to catch OCR errors in location names.
        Excludes the store name from being included in the address.
        
        Args:
            lines: List of text lines
            ocr_results: OCR results with bounding boxes
            store_name: Detected store name to exclude from address
        """
        address_lines = []
        
        # Malaysian cities and areas (for fuzzy matching)
        malaysian_locations = [
            # Major cities
            'penang', 'pulau pinang', 'georgetown', 'butterworth',
            'kuala lumpur', 'kl', 'petaling jaya', 'pj',
            'selangor', 'shah alam', 'subang jaya',
            'johor', 'johor bahru', 'jb',
            'melaka', 'malacca',
            'ipoh', 'perak',
            'kuching', 'sarawak',
            'kota kinabalu', 'sabah',
            
            # Penang areas and malls
            'bukit mertajam', 'bayan lepas', 'bayan baru',
            'egate', 'e-gate', 'egenie', 'egnie',  # Common OCR errors for E-Gate
            'gurney', 'gurney plaza', 'gurney paragon',
            'queensbay', 'queensbay mall',
            'komtar', 'prangin mall',
            'sunway carnival',
            
            # KL/Selangor malls
            'mid valley', 'midvalley',
            'pavilion', 'suria klcc',
            'one utama', '1 utama',
            'sunway pyramid',
            'the curve', 'ikea',
            
            # Common branch identifiers
            'tesco', 'lotus', 'mydin', 'aeon',
            'giant', 'jaya grocer', 'village grocer'
        ]
        
        # If we have OCR results, use them to find location-related text
        if ocr_results:
            for bbox, text, conf in ocr_results:
                text_lower = text.lower().strip()
                
                # Skip very short text or gibberish
                if len(text) < 3 or self._is_gibberish(text):
                    continue
                
                # Skip if this text is the store name
                if store_name and text.strip().lower() == store_name.strip().lower():
                    print(f"  [ADDRESS] Skipping store name: '{text}'")
                    continue
                
                # Skip company-related text (not useful for location)
                company_keywords = [
                    'sdn', 'bhd', 'sdn bhd', 'sdn. bhd.',
                    'stores', 'store', 'supermarket', 'hypermarket',
                    'malaysia', 'singapore',
                    'reg', 'no', 'registration',
                    'formerly', 'former',
                    '(reg', '(formerly'
                ]
                if any(keyword in text_lower for keyword in company_keywords):
                    print(f"  [ADDRESS] Skipping company text: '{text}'")
                    continue
                
                # Skip registration numbers and codes
                if re.search(r'\d{6,}', text):  # Long numbers (registration, product codes)
                    continue
                
                # Check for exact or fuzzy match with Malaysian locations
                # Use stricter threshold (0.75) to avoid false positives
                for location in malaysian_locations:
                    # Fuzzy match: allow some character differences
                    if self._fuzzy_match(text_lower, location, threshold=0.75):
                        if len(text) <= 150:
                            address_lines.append(text)
                            print(f"  [ADDRESS] Found location: '{text}' (matched: {location}, conf: {conf:.2f})")
                            break
                
                # Check for address keywords
                if any(keyword in text_lower for keyword in [
                    'street', 'road', 'avenue', 'blvd', 'drive', 'lane',
                    'level', 'floor', 'unit', '#', 'bldg', 'building',
                    'mall', 'plaza', 'center', 'centre', 'jalan', 'jln',
                    'taman', 'persiaran', 'lorong'
                ]):
                    if len(text) <= 150 and text not in address_lines:
                        address_lines.append(text)
                        print(f"  [ADDRESS] Found keyword: '{text}' (conf: {conf:.2f})")
        
        # Fallback: use line-based extraction
        if not address_lines:
            for line in lines[:15]:
                line = line.strip()
                
                if not line or self._is_gibberish(line):
                    continue
                
                # Check for location names
                for location in malaysian_locations:
                    if self._fuzzy_match(line.lower(), location, threshold=0.6):
                        if len(line) <= 150:
                            address_lines.append(line)
                            break
                
                # Check if line contains address-like keywords
                if any(keyword in line.lower() for keyword in [
                    'street', 'road', 'avenue', 'blvd', 'drive', 'lane',
                    'level', 'floor', 'unit', '#', 'bldg', 'building',
                    'mall', 'plaza', 'center', 'centre', 'jalan', 'jln'
                ]):
                    if len(line) <= 150:
                        address_lines.append(line)
                
                # Check for numbered addresses
                elif re.search(r'\b\d+[-\s]+[A-Za-z]', line):
                    if len(line) <= 150:
                        address_lines.append(line)
        
        full_address = ' '.join(address_lines) if address_lines else None
        
        if full_address and len(full_address) > 300:
            full_address = full_address[:300]
        
        return full_address
    
    def _fuzzy_match(self, text: str, target: str, threshold: float = 0.7) -> bool:
        """
        Improved fuzzy matching using Levenshtein-like distance.
        Returns True if text is similar enough to target.
        Catches OCR errors like: EGNIE → EGATE, FENANG → PENANG
        """
        # Normalize: remove spaces, lowercase
        text = text.replace(' ', '').replace('-', '').lower()
        target = target.replace(' ', '').replace('-', '').lower()
        
        # Empty check
        if len(text) == 0 or len(target) == 0:
            return False
        
        # Exact match
        if text == target:
            return True
        
        # Substring match (one contains the other)
        if target in text or text in target:
            return True
        
        # For very short targets (like "kl", "pj"), require exact match
        if len(target) <= 2:
            return text == target
        
        # Calculate Levenshtein-like similarity
        # Count matching characters in order
        matches = 0
        text_idx = 0
        target_idx = 0
        
        while text_idx < len(text) and target_idx < len(target):
            if text[text_idx] == target[target_idx]:
                matches += 1
                text_idx += 1
                target_idx += 1
            else:
                # Try skipping one character in text (insertion error)
                if text_idx + 1 < len(text) and text[text_idx + 1] == target[target_idx]:
                    text_idx += 2
                    target_idx += 1
                    matches += 1
                # Try skipping one character in target (deletion error)
                elif target_idx + 1 < len(target) and text[text_idx] == target[target_idx + 1]:
                    text_idx += 1
                    target_idx += 2
                    matches += 1
                else:
                    # Substitution error - still count as partial match
                    text_idx += 1
                    target_idx += 1
        
        # Calculate similarity ratio
        max_len = max(len(text), len(target))
        similarity = matches / max_len
        
        # Also check character overlap (alternative metric)
        common_chars = sum(1 for c in text if c in target)
        char_overlap = common_chars / max_len
        
        # Use the better of the two metrics
        final_similarity = max(similarity, char_overlap)
        
        return final_similarity >= threshold
    
    def _extract_phone(self, lines: List[str]) -> Optional[str]:
        """Extract phone number with improved pattern matching."""
        phone_patterns = [
            r'(?:Tel|Phone|Ph|Contact)[\s:]*\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            r'0[1-9][-.\s]?\d{3,4}[-.\s]?\d{4}',
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\d{4}[-.\s]?\d{4}',
            r'\d{8,}',
        ]
        
        for line in lines[:20]:
            for pattern in phone_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    phone = match.group(0)
                    phone = re.sub(r'(?:Tel|Phone|Ph|Contact)[\s:]*', '', phone, flags=re.IGNORECASE)
                    phone = re.sub(r'[^\d+]', '', phone)
                    
                    if len(phone.replace('+', '')) >= 7:
                        return phone
        
        return None
    
    def _extract_postal_code(self, text: str) -> Optional[str]:
        """Extract postal/ZIP code."""
        labeled_patterns = [
            r'(?:postal|post\s*code|zip)[\s:]+([A-Z0-9\s-]{4,10})',
            r'\b([5-9]\d{4})\s*(?:kuala|lumpur|kl|malaysia)',
        ]
        
        for pattern in labeled_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _detect_country(self, text: str) -> Optional[str]:
        """Detect country from text patterns."""
        text_lower = text.lower()
        
        explicit_countries = [
            ('singapore', ['singapore', 'republic of singapore']),
            ('malaysia', ['malaysia', 'kuala lumpur', 'selangor', 'penang', 'johor']),
            ('thailand', ['thailand', 'bangkok']),
        ]
        
        for country, keywords in explicit_countries:
            if any(keyword in text_lower for keyword in keywords):
                return country.title()
        
        return None
    
    def _get_location_section(self, lines: List[str]) -> str:
        """Get the full location section."""
        location_lines = []
        
        for line in lines[:15]:
            line = line.strip()
            if line:
                location_lines.append(line)
            
            if any(keyword in line.lower() for keyword in ['date', 'time', 'cashier', 'terminal']):
                break
        
        return '\n'.join(location_lines)
    
    def _calculate_location_confidence(
        self,
        store_name: Optional[str],
        address: Optional[str],
        phone: Optional[str],
        postal_code: Optional[str],
        country: Optional[str]
    ) -> float:
        """Calculate confidence score based on extracted information."""
        confidence = 0.0
        
        if store_name:
            confidence += 0.4
        if address:
            confidence += 0.3
        if phone:
            confidence += 0.15
        if postal_code:
            confidence += 0.1
        if country:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def extract_date_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract transaction date from OCR text.
        (Simplified version - can be expanded based on tesseract_ocr.py implementation)
        """
        # Date patterns
        date_patterns = [
            (r'\b(\d{1,2})[/\-.:](\d{1,2})[/\-.:](\d{4})\b', 'DMY_or_MDY'),
            (r'\b(\d{4})[/\-.:](\d{1,2})[/\-.:](\d{1,2})\b', 'YMD'),
        ]
        
        for pattern, format_type in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if format_type == 'DMY_or_MDY':
                        day = int(groups[0])
                        month = int(groups[1])
                        year = int(groups[2])
                        
                        # Try creating date
                        try:
                            date_obj = datetime(year, month, day)
                            return {
                                'value': date_obj.strftime('%Y-%m-%d'),
                                'content': match.group(0),
                                'confidence': 0.8,
                                'format_detected': format_type
                            }
                        except ValueError:
                            # Try swapping day/month
                            try:
                                date_obj = datetime(year, day, month)
                                return {
                                    'value': date_obj.strftime('%Y-%m-%d'),
                                    'content': match.group(0),
                                    'confidence': 0.8,
                                    'format_detected': 'MDY'
                                }
                            except ValueError:
                                continue
                except Exception:
                    continue
        
        return None
