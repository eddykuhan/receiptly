"""
Store name extraction fallback service.
Used when Azure and Tesseract both fail to detect the merchant name.
"""

import re
from typing import Optional, Dict, Any, List
from PIL import Image
import pytesseract
import io
from thefuzz import fuzz, process


class StoreNameExtractor:
    """
    Fallback service to extract store name from receipt when primary methods fail.
    Uses full-image OCR with heuristics to identify the likely store name.
    """
    
    # Common retail chains and patterns (expandable)
    # Dictionary mapping Canonical Name -> List of variations/keywords to match
    KNOWN_CHAINS = {
        # Supermarkets / Hypermarkets
        'Aeon': ['aeon', 'aeon co', 'aeon retail'],
        'Aeon Big': ['aeon big'],
        'Lotus\'s': ['lotus', 'tesco', 'lotus store', 'lotuss'],
        'Giant': ['giant', 'giant hypermarket', 'giant superstore'],
        'Jaya Grocer': ['jaya grocer', 'trendcell'],
        'Village Grocer': ['village grocer'],
        'Mydin': ['mydin', 'mydin mohamed holdings', 'mydin hypermarket'],
        'Econsave': ['econsave', 'econsave cash & carry'],
        'Hero Market': ['hero market', 'hero supermarket'],
        'Cold Storage': ['cold storage'],
        'Mercato': ['mercato'],
        'B.I.G': ['b.i.g', 'ben\'s independent grocer'],
        'NSK': ['nsk', 'nsk trade city', 'nsk grocer'],
        'Checkers': ['checkers', 'checkers hypermarket'],
        'The Store': ['the store'],
        'Pacific': ['pacific', 'pacific hypermarket'],
        'Billion': ['billion', 'billion shopping centre'],
        
        # Convenience Stores
        '7-Eleven': ['7-eleven', '7 eleven', '7-11', 'seven eleven'],
        'FamilyMart': ['familymart', 'family mart'],
        'MyNews': ['mynews', 'my news'],
        'KK Super Mart': ['kk super mart', 'kk mart', 'kk supermart'],
        '99 Speedmart': ['99 speedmart', '99 speed mart', '99speedmart'],
        'CU': ['cu', 'cu convenience store'],
        'Potboy': ['potboy', 'potboy mart'],
        
        # Pharmacies / Health & Beauty
        'Watsons': ['watsons', 'watson\'s', 'watsons personal care'],
        'Guardian': ['guardian', 'guardian health and beauty'],
        'Caring': ['caring', 'caring pharmacy'],
        'Big Pharmacy': ['big pharmacy'],
        'Alpro': ['alpro', 'alpro pharmacy'],
        'Health Lane': ['health lane', 'health lane family pharmacy'],
        'AA Pharmacy': ['aa pharmacy'],
        'Sephora': ['sephora'],
        'Sasa': ['sasa'],
        
        # F&B
        'McDonald\'s': ['mcdonald', 'mcdonald\'s', 'gerbang alaf restaurants'],
        'KFC': ['kfc', 'kentucky fried chicken', 'qsr stores'],
        'Pizza Hut': ['pizza hut'],
        'Domino\'s': ['domino', 'domino\'s pizza'],
        'Burger King': ['burger king', 'cosmo restaurants'],
        'Subway': ['subway'],
        'Starbucks': ['starbucks', 'berjaya starbucks'],
        'Coffee Bean': ['coffee bean', 'the coffee bean & tea leaf'],
        'Tealive': ['tealive', 'loob holding'],
        'Chatime': ['chatime'],
        'Gong Cha': ['gong cha'],
        'OldTown': ['oldtown', 'oldtown white coffee'],
        'PappaRich': ['papparich'],
        'Secret Recipe': ['secret recipe'],
        'Nando\'s': ['nando', 'nando\'s', 'nando\'s chickenland'],
        'Texas Chicken': ['texas chicken'],
        'Marrybrown': ['marrybrown'],
        'A&W': ['a&w'],
        'Sushi King': ['sushi king'],
        'Sakae Sushi': ['sakae sushi'],
        
        # Retail / Department Stores
        'Parkson': ['parkson'],
        'Isetan': ['isetan'],
        'Sogo': ['sogo'],
        'Harvey Norman': ['harvey norman'],
        'Senheng': ['senheng', 'senheng electric'],
        'SenQ': ['senq', 'senq digital station'],
        'MR DIY': ['mr diy', 'mr. diy', 'mrdiy'],
        'Daiso': ['daiso'],
        'Uniqlo': ['uniqlo'],
        'H&M': ['h&m', 'hennes & mauritz'],
        'Padini': ['padini', 'padini concept store'],
        'Brands Outlet': ['brands outlet'],
        'Decathlon': ['decathlon'],
        'IKEA': ['ikea', 'ikano'],
        'Popular': ['popular', 'popular book'],
        
        # Petrol Stations
        'Petronas': ['petronas', 'petronas dagangan'],
        'Shell': ['shell', 'shell malaysia'],
        'Petron': ['petron'],
        'Caltex': ['caltex'],
        'BHPetrol': ['bhpetrol', 'boustead petroleum']
    }
    
    def __init__(self):
        """Initialize the store name extractor."""
        pass
    
    def extract_from_full_image(self, image_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Extract store name from full receipt image using OCR and heuristics.
        
        Args:
            image_bytes: Receipt image as bytes
            
        Returns:
            Dictionary with:
            - store_name: Extracted store name or None
            - confidence: Confidence score (0.0-1.0)
            - method: Extraction method used
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Extract all text from image
            ocr_text = pytesseract.image_to_string(image)
            
            if not ocr_text or len(ocr_text.strip()) < 5:
                return None
            
            lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
            
            if not lines:
                return None
            
            # Try multiple extraction strategies
            result = (
                self._extract_by_known_chain(lines) or
                self._extract_by_position(lines) or
                self._extract_by_capitalization(lines) or
                self._extract_by_pattern(lines)
            )
            
            return result
            
        except Exception as e:
            print(f"Error in fallback store name extraction: {str(e)}")
            return None
    
    def find_best_match(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Find the best matching known chain for a single string.
        
        Args:
            text: Text to match against known chains
            
        Returns:
            Dictionary with match details or None
        """
        if not text:
            return None
            
        text_lower = text.lower()
        best_match = None
        best_score = 0
        
        for canonical_name, variations in self.KNOWN_CHAINS.items():
            for variation in variations:
                # Exact match check (fast path)
                if variation in text_lower:
                    return {
                        'store_name': canonical_name,
                        'confidence': 0.95,
                        'method': 'exact'
                    }
                
                # Fuzzy match logic
                score = 0
                if len(variation) <= 4:
                    # Short names: strict matching
                    score = fuzz.ratio(variation, text_lower)
                    if score < 90:
                        # Word boundary check
                        if f" {variation} " in f" {text_lower} ":
                            score = 100
                        else:
                            score = 0
                else:
                    # Long names: flexible matching
                    score = fuzz.token_set_ratio(variation, text_lower)
                
                if score > 80 and score > best_score:
                    best_score = score
                    best_match = {
                        'store_name': canonical_name,
                        'confidence': score / 100.0,
                        'method': 'fuzzy'
                    }
        
        return best_match

    def _extract_by_known_chain(self, lines: list) -> Optional[Dict[str, Any]]:
        """
        Check if any line matches a known retail chain using fuzzy matching.
        
        Args:
            lines: List of text lines from OCR
            
        Returns:
            Store name match or None
        """
        best_match = None
        best_score = 0
        
        # Check first 10 lines for known chains
        for i, line in enumerate(lines[:10]):
            match = self.find_best_match(line)
            
            if match:
                # If exact match, return immediately
                if match['method'] == 'exact':
                    match['line_index'] = i
                    match['method'] = 'known_chain_exact'
                    return match
                
                # Keep track of best fuzzy match
                if match['confidence'] > best_score:
                    best_score = match['confidence']
                    best_match = match
                    best_match['line_index'] = i
                    best_match['method'] = 'known_chain_fuzzy'
        
        return best_match
    
    def _extract_by_position(self, lines: list) -> Optional[Dict[str, Any]]:
        """
        Extract store name from the first few lines (most common position).
        Uses validation to ensure it's a valid store name.
        
        Args:
            lines: List of text lines from OCR
            
        Returns:
            Store name from top of receipt or None
        """
        # Check first 5 lines
        for i, line in enumerate(lines[:5]):
            # Skip very short lines
            if len(line) < 3:
                continue
            
            # Skip lines that look like addresses or phone numbers
            if self._looks_like_address(line) or self._looks_like_phone(line):
                continue
            
            # Skip lines with too many numbers
            digit_ratio = sum(c.isdigit() for c in line) / len(line)
            if digit_ratio > 0.5:
                continue
            
            # Clean the line
            cleaned = self._clean_store_name(line)
            
            # Validate cleaned name
            if self._is_valid_store_name(cleaned):
                return {
                    'store_name': cleaned,
                    'confidence': 0.6,  # Medium confidence
                    'method': 'position',
                    'line_index': i
                }
        
        return None
    
    def _extract_by_capitalization(self, lines: list) -> Optional[Dict[str, Any]]:
        """
        Look for lines with all caps or title case (common for store names).
        
        Args:
            lines: List of text lines from OCR
            
        Returns:
            Store name based on capitalization pattern or None
        """
        # Check first 8 lines
        for i, line in enumerate(lines[:8]):
            # Skip very short lines
            if len(line) < 3:
                continue
            
            # Check if mostly uppercase letters
            alpha_chars = [c for c in line if c.isalpha()]
            if alpha_chars:
                uppercase_ratio = sum(c.isupper() for c in alpha_chars) / len(alpha_chars)
                
                # Line is mostly uppercase
                if uppercase_ratio > 0.7:
                    cleaned = self._clean_store_name(line)
                    
                    if self._is_valid_store_name(cleaned):
                        return {
                            'store_name': cleaned,
                            'confidence': 0.5,
                            'method': 'capitalization',
                            'line_index': i
                        }
        
        return None
    
    def _extract_by_pattern(self, lines: list) -> Optional[Dict[str, Any]]:
        """
        Use regex patterns to identify store-like names.
        
        Args:
            lines: List of text lines from OCR
            
        Returns:
            Store name based on patterns or None
        """
        # Patterns that often indicate store names
        patterns = [
            r'^[A-Z][A-Za-z\s&\'-]+(?:INC|LLC|CO|CORP)?\.?$',  # Company names
            r'^[A-Z\s&\'-]{3,}$',  # All caps words
        ]
        
        for i, line in enumerate(lines[:8]):
            for pattern in patterns:
                if re.match(pattern, line.strip()):
                    cleaned = self._clean_store_name(line)
                    
                    if self._is_valid_store_name(cleaned):
                        return {
                            'store_name': cleaned,
                            'confidence': 0.4,
                            'method': 'pattern',
                            'line_index': i
                        }
        
        return None
    
    def _clean_store_name(self, text: str) -> str:
        """
        Clean up extracted store name by removing common artifacts.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned store name
        """
        # Remove common suffixes
        text = re.sub(r'\s+(INC|LLC|CO|CORP|LTD)\.?$', '', text, flags=re.IGNORECASE)
        
        # Remove excessive special characters
        text = re.sub(r'[^\w\s&\'-]', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Capitalize properly (Title Case)
        text = text.title()
        
        # Truncate to max length
        if len(text) > 100:
            text = text[:100].strip()
        
        return text.strip()
    
    def _is_valid_store_name(self, text: str) -> bool:
        """
        Validate if extracted text is a reasonable store name.
        
        Args:
            text: Cleaned text to validate
            
        Returns:
            True if valid store name, False otherwise
        """
        if not text or len(text) < 3 or len(text) > 100:
            return False
        
        # Must have at least 30% letters
        letter_ratio = sum(c.isalpha() for c in text) / len(text)
        if letter_ratio < 0.3:
            return False
        
        # Must have at least one word with 2+ letters
        words = text.split()
        valid_words = [w for w in words if sum(c.isalpha() for c in w) >= 2]
        if len(valid_words) == 0:
            return False
        
        # Should not be all numbers
        if text.replace(' ', '').isdigit():
            return False
        
        return True
    
    def _looks_like_address(self, text: str) -> bool:
        """Check if text looks like an address."""
        # Check for common address patterns
        address_patterns = [
            r'\d+\s+[A-Za-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)',
            r'^\d+\s+[A-Za-z\s]+,',  # Number + street name + comma
        ]
        
        for pattern in address_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _looks_like_phone(self, text: str) -> bool:
        """Check if text looks like a phone number."""
        # Remove common phone formatting
        cleaned = re.sub(r'[\s\-\(\)]', '', text)
        
        # Check if mostly digits
        if len(cleaned) >= 10 and sum(c.isdigit() for c in cleaned) >= 10:
            return True
        
        return False
