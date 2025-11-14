"""
Tesseract OCR Service for extracting store location and address information from receipts.
"""
import pytesseract
from PIL import Image
import io
import re
from typing import Dict, Any, Optional, List
import cv2
import numpy as np


class TesseractOCRService:
    """Service for extracting store location using Tesseract OCR."""
    
    def __init__(self, debug_mode: bool = False):
        """
        Initialize the Tesseract OCR service.
        
        Args:
            debug_mode: If True, saves preprocessed images for debugging
        """
        self.debug_mode = debug_mode
        
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
                    
                    # Extract text using Tesseract with optimized config
                    custom_config = r'--oem 3 --psm 6'
                    full_text = pytesseract.image_to_string(processed_image, config=custom_config)
                    
                    # Also try with different PSM mode
                    custom_config_alt = r'--oem 3 --psm 3'
                    full_text_alt = pytesseract.image_to_string(processed_image, config=custom_config_alt)
                    
                    # Use the longer result (usually more accurate)
                    if len(full_text_alt) > len(full_text):
                        full_text = full_text_alt
                    
                    # Get detailed OCR data
                    ocr_data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT, config=custom_config)
                    
                    # Extract location information
                    location_info = self._extract_location_info(full_text, ocr_data)
                    
                    # Score this result
                    score = location_info.get('confidence', 0.0)
                    # Bonus for finding store name
                    if location_info.get('store_name'):
                        score += 0.2
                    
                    if self.debug_mode:
                        print(f"[DEBUG] Strategy '{strategy_name}' score: {score:.2f}")
                        print(f"[DEBUG] Store name: {location_info.get('store_name', 'N/A')}")
                    
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
        
        # Resize if too small (Tesseract works better with larger images)
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
    
    def _extract_location_info(self, text: str, ocr_data: Dict) -> Dict[str, Any]:
        """
        Extract structured location information from OCR text.
        
        Args:
            text: Full OCR text
            ocr_data: Detailed OCR data with bounding boxes
            
        Returns:
            Dictionary with extracted location details
        """
        lines = text.split('\n')
        
        # Extract different location components
        store_name = self._extract_store_name(lines)
        address = self._extract_address(lines)
        phone = self._extract_phone(lines)
        postal_code = self._extract_postal_code(text)
        country = self._detect_country(text)
        
        # Calculate confidence based on how much info we found
        confidence = self._calculate_location_confidence(
            store_name, address, phone, postal_code, country
        )
        
        return {
            "store_name": store_name,
            "address": address,
            "phone": phone,
            "postal_code": postal_code,
            "country": country,
            "confidence": confidence,
            "full_location_text": self._get_location_section(lines)
        }
    
    def _extract_store_name(self, lines: List[str]) -> Optional[str]:
        """
        Extract store name (usually first non-empty line with significant text).
        Filters out noise and common OCR errors.
        """
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            
            # Skip empty or very short lines
            if len(line) < 3:
                continue
            
            # Skip lines that are purely numeric (likely not a store name)
            if line.replace(' ', '').replace('.', '').replace('-', '').isdigit():
                continue
            
            # Skip common noise patterns
            noise_patterns = ['|', '===', '---', '___', '***']
            if any(pattern in line for pattern in noise_patterns):
                continue
            
            # Skip if it looks like a date
            if any(word in line.lower() for word in ['date', 'time', 'am', 'pm']):
                continue
            
            # Clean up common OCR errors
            cleaned_line = self._clean_ocr_text(line)
            
            # If line has mostly letters (good sign for store name)
            letter_count = sum(c.isalpha() for c in cleaned_line)
            if letter_count >= 3:  # At least 3 letters
                return cleaned_line
        
        return None
    
    def _clean_ocr_text(self, text: str) -> str:
        """Clean up common OCR errors and noise."""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Common OCR substitutions
        replacements = {
            '|': 'I',  # Vertical bar often misread as I
            '0': 'O',  # Zero vs O in text context
            '1': 'I',  # One vs I in text context  
        }
        
        # Only apply replacements if the text looks like it needs it
        # (has mix of letters and these characters)
        if any(c.isalpha() for c in text):
            for old, new in replacements.items():
                # Only replace if surrounded by letters
                import re
                text = re.sub(f'(?<=[A-Z]){re.escape(old)}(?=[A-Z])', new, text)
        
        return text
    
    def _extract_address(self, lines: List[str]) -> Optional[str]:
        """
        Extract address lines containing street, building info.
        Cleans OCR errors in addresses.
        """
        address_lines = []
        
        for line in lines[:15]:  # Check first 15 lines
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Clean common OCR errors in addresses
            line = self._clean_address_ocr(line)
            
            # Check if line contains address-like keywords
            if any(keyword in line.lower() for keyword in [
                'street', 'road', 'avenue', 'blvd', 'drive', 'lane',
                'level', 'floor', 'unit', '#', 'bldg', 'building',
                'mall', 'plaza', 'center', 'centre', 'jalan', 'jln'
            ]):
                address_lines.append(line)
            
            # Check for numbered addresses (e.g., "123 Main St")
            elif re.search(r'\b\d+[-\s]+[A-Za-z]', line):
                address_lines.append(line)
        
        return ' '.join(address_lines) if address_lines else None
    
    def _clean_address_ocr(self, text: str) -> str:
        """Clean OCR errors specific to addresses."""
        # Common OCR errors in postal codes and numbers
        text = re.sub(r'\$(\d)', r'5\1', text)  # $ at start of number = 5
        text = re.sub(r'(\d)\$', r'\g<1>5', text)  # $ at end of number = 5
        text = re.sub(r'\$', '5', text)  # Standalone $ = 5
        
        # Fix common letter/number confusion in addresses
        # But only in numeric contexts
        text = re.sub(r'(?<=\d)[Oo](?=\d)', '0', text)  # O between digits = 0
        text = re.sub(r'(?<=\d)[Oo](?=\s|$)', '0', text)  # O after digits = 0
        
        return text
    
    def _extract_phone(self, lines: List[str]) -> Optional[str]:
        """
        Extract phone number with improved pattern matching.
        Preserves country codes for better country detection.
        """
        phone_patterns = [
            # International with country code
            r'(?:Tel|Phone|Ph|Contact)[:\s]*\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # +XX format
            
            # Malaysia format (03-XXXXXXX or 03XXXXXXX)
            r'0[1-9][-.\s]?\d{3,4}[-.\s]?\d{4}',
            
            # General patterns
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (XXX) XXX-XXXX
            r'\d{4}[-.\s]?\d{4}',  # XXXX-XXXX
            r'\d{8,}',  # 8+ consecutive digits
        ]
        
        for line in lines[:20]:
            # Clean OCR errors in phone numbers
            line = re.sub(r'[Oo]', '0', line)  # O -> 0
            line = re.sub(r'\?', '7', line)  # ? often misread as 7
            
            for pattern in phone_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    phone = match.group(0)
                    
                    # Remove label if present
                    phone = re.sub(r'(?:Tel|Phone|Ph|Contact)[:\s]*', '', phone, flags=re.IGNORECASE)
                    
                    # Clean but preserve + for country code
                    phone = re.sub(r'[^\d+]', '', phone)
                    
                    # Validate minimum length
                    if len(phone.replace('+', '')) >= 7:
                        return phone
                        
        return None
    
    def _extract_postal_code(self, text: str) -> Optional[str]:
        """
        Extract postal/ZIP code.
        Excludes invoice numbers, dates, and other non-postal patterns.
        """
        # First check for explicit postal code labels
        labeled_patterns = [
            r'(?:postal|post\s*code|zip)[:\s]+([A-Z0-9\s-]{4,10})',  # "Postal Code: 12345"
            r'\b([5-9]\d{4})\s*(?:kuala|lumpur|kl|malaysia)',  # Malaysia postal before city
        ]
        
        for pattern in labeled_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                postal = match.group(1).strip()
                # Clean up OCR errors in postal codes
                postal = re.sub(r'[$]', '5', postal)  # $ often misread as 5
                postal = re.sub(r'[Oo]', '0', postal)  # O misread as 0
                return postal
        
        # Extract postal from address context (Malaysia: 5-digit before city name)
        # Look for pattern: "59200 KUALA LUMPUR" or "$9200 KUALA LUMPUR"
        address_postal = re.search(
            r'[$5-9]?\d{4,5}\s+(?:kuala\s+lumpur|kl|selangor|penang|johor|ipoh|melaka)',
            text,
            re.IGNORECASE
        )
        if address_postal:
            postal = address_postal.group(0).split()[0]  # Get just the number part
            # Clean OCR errors
            postal = re.sub(r'[$]', '5', postal)
            postal = re.sub(r'[Oo]', '0', postal)
            # Validate it's a valid Malaysia postal code (50000-99999)
            if postal.isdigit() and 50000 <= int(postal) <= 99999:
                return postal
        
        # Country-specific patterns (with context validation)
        patterns = {
            'singapore': r'\bS\s*\d{6}\b',  # Singapore postal code with S prefix
            'malaysia': r'\b[5-9]\d{4}\b',  # Malaysia postal code (50000-99999)
            'usa': r'\b\d{5}(?:-\d{4})?\b',  # US ZIP
            'uk': r'\b[A-Z]{1,2}\d{1,2}\s*\d[A-Z]{2}\b',  # UK postcode
            'canada': r'\b[A-Z]\d[A-Z]\s*\d[A-Z]\d\b',  # Canada
        }
        
        # Exclusion patterns - things that look like postal codes but aren't
        exclusions = [
            r'invoice|receipt|trans|bill|no[:\s.]*\d',  # Near invoice/transaction numbers
            r'vat\d+',  # VAT numbers
            r'\d{2}[/-]\d{2}[/-]\d{2}',  # Dates
            r'[\($]\d+[-)]',  # Numbers in parentheses or with $ (company reg numbers)
            r'sdn\s+bhd',  # Company registration context
        ]
        
        for country, pattern in patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                candidate = match.group(0).strip()
                
                # Check surrounding context for exclusions (30 chars before and after)
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].lower()
                
                # Skip if in excluded context
                if any(re.search(excl, context) for excl in exclusions):
                    continue
                
                # Clean OCR errors
                candidate = re.sub(r'[$]', '5', candidate)
                candidate = re.sub(r'[Oo]', '0', candidate)
                
                return candidate
        
        return None
    
    def _detect_country(self, text: str) -> Optional[str]:
        """
        Detect country from text patterns and context.
        Uses multiple signals to avoid false positives.
        """
        text_lower = text.lower()
        
        # Priority 1: Explicit country mentions
        explicit_countries = [
            ('singapore', ['singapore', 'republic of singapore']),
            ('malaysia', ['malaysia', 'kuala lumpur', 'selangor', 'penang', 'johor']),
            ('thailand', ['thailand', 'bangkok']),
            ('indonesia', ['indonesia', 'jakarta']),
            ('philippines', ['philippines', 'manila']),
            ('australia', ['australia', 'sydney', 'melbourne']),
            ('canada', ['canada', 'toronto', 'vancouver']),
            ('uk', ['united kingdom', 'england', 'scotland', 'wales', 'london']),
            ('usa', ['united states', 'america']),
        ]
        
        for country, keywords in explicit_countries:
            if any(keyword in text_lower for keyword in keywords):
                return country.title()
        
        # Priority 2: Phone number patterns (more reliable than postal codes)
        phone_country_patterns = {
            'singapore': r'\+65|^65[-\s]',  # +65 or starts with 65
            'malaysia': r'\+60|^60[-\s]|03[-\s]\d{4}',  # +60 or 03 area code (KL)
            'thailand': r'\+66|^66[-\s]',
            'indonesia': r'\+62|^62[-\s]',
            'philippines': r'\+63|^63[-\s]',
            'usa': r'\+1[-\s]\d{3}',
            'canada': r'\+1[-\s]\d{3}',
            'uk': r'\+44',
            'australia': r'\+61',
        }
        
        for country, pattern in phone_country_patterns.items():
            if re.search(pattern, text):
                return country.title()
        
        # Priority 3: Postal code patterns (only if no phone number found)
        # Malaysia postal codes are 5 digits starting with 5-9
        if re.search(r'\b[5-9]\d{4}\b.*(?:kuala|lumpur|malaysia)', text_lower):
            return 'Malaysia'
        
        # Singapore postal codes often have 6 digits or S prefix
        if re.search(r'\bS\s*\d{6}\b', text_lower):
            return 'Singapore'
        
        # UK postcodes have specific format
        if re.search(r'\b[A-Z]{1,2}\d{1,2}\s*\d[A-Z]{2}\b', text):
            return 'Uk'
        
        # Canadian postcodes
        if re.search(r'\b[A-Z]\d[A-Z]\s*\d[A-Z]\d\b', text):
            return 'Canada'
        
        # US ZIP codes (least specific, check last)
        # Only if explicitly near "USA" or state names
        if re.search(r'\b\d{5}(?:-\d{4})?\b', text):
            us_context = ['usa', 'united states', 'ca', 'ny', 'tx', 'fl']
            if any(state in text_lower for state in us_context):
                return 'Usa'
        
        return None
    
    def _get_location_section(self, lines: List[str]) -> str:
        """Get the full location section (usually top portion of receipt)."""
        location_lines = []
        
        for i, line in enumerate(lines[:15]):  # First 15 lines
            line = line.strip()
            if line:
                location_lines.append(line)
            
            # Stop if we hit a date or transaction line
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
        """
        Calculate confidence score for extracted location.
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0
        
        if store_name:
            score += 0.25
        if address:
            score += 0.30
        if phone:
            score += 0.20
        if postal_code:
            score += 0.15
        if country:
            score += 0.10
        
        return round(score, 2)
