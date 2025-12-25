"""
Store Location Service - Fuzzy matching for store addresses using Google Places data

This service matches OCR-extracted store names against a database of verified
Google Places locations to improve address accuracy and provide geocoding.
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from thefuzz import fuzz
import logging

logger = logging.getLogger(__name__)


class StoreLocationService:
    """
    Service for matching store names to verified Google Places locations.
    
    Features:
    - Fuzzy matching of store names
    - Phone number matching
    - Partial address matching (city, postal code)
    - Confidence scoring
    - Support for multiple store chains
    """
    
    def __init__(self, data_directory: Optional[str] = None):
        """
        Initialize the service and load location data.
        
        Args:
            data_directory: Path to directory containing store location JSON files.
                          If None, will look for 'store-scraper/data' relative to project root.
        """
        if data_directory is None:
            # Try multiple locations for store data
            # 1. Docker container location (production)
            docker_path = Path("/app/store-scraper-data")
            # 2. Local development location - use absolute path resolution
            current_file = Path(__file__).resolve()  # Resolve to absolute path
            local_path = current_file.parent.parent.parent.parent / "store-scraper" / "data"
            
            # Debug logging
            logger.info(f"🔍 __file__ location: {current_file}")
            logger.info(f"🔍 Calculated local_path: {local_path}")
            logger.info(f"🔍 local_path.exists(): {local_path.exists()}")
            logger.info(f"🔍 docker_path.exists(): {docker_path.exists()}")
            
            if docker_path.exists():
                data_directory = docker_path
                logger.info(f"✅ Using Docker container store data: {docker_path}")
            elif local_path.exists():
                data_directory = local_path
                logger.info(f"✅ Using local development store data: {local_path}")
            else:
                # Fallback - will trigger warning in _load_all_locations
                logger.warning(f"⚠️ Store location data not found!")
                logger.warning(f"⚠️ Docker path checked: {docker_path}")
                logger.warning(f"⚠️ Local path checked: {local_path}")
                logger.warning(f"⚠️ Google Places matching will be disabled - OCR-only mode")
                data_directory = docker_path  # Use docker path as fallback (will be empty)
        
        self.data_directory = Path(data_directory)
        self.locations: List[Dict] = []
        self.store_index: Dict[str, List[Dict]] = {}  # Index by store name for faster lookup
        
        self._load_all_locations()
        logger.info(f"Loaded {len(self.locations)} store locations from {len(self.store_index)} different stores")
    
    def _load_all_locations(self) -> None:
        """Load all location JSON files from the data directory."""
        if not self.data_directory.exists():
            logger.warning(f"Data directory not found: {self.data_directory}")
            return
        
        json_files = list(self.data_directory.glob("*_locations.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    locations = json.load(f)
                    
                    if isinstance(locations, list):
                        self.locations.extend(locations)
                        
                        # Build index by store name
                        for location in locations:
                            store_name = location.get('store_name', '').lower()
                            if store_name not in self.store_index:
                                self.store_index[store_name] = []
                            self.store_index[store_name].append(location)
                        
                        logger.info(f"Loaded {len(locations)} locations from {json_file.name}")
                    else:
                        logger.warning(f"Invalid format in {json_file.name}: expected list")
                        
            except Exception as e:
                logger.error(f"Error loading {json_file.name}: {e}")
    
    def find_best_match(
        self,
        store_name: str,
        partial_address: Optional[str] = None,
        phone: Optional[str] = None,
        postal_code: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> Optional[Dict]:
        """
        Find the best matching store location using fuzzy matching.
        
        Args:
            store_name: Store name extracted from OCR
            partial_address: Partial address from OCR (may contain city, area)
            phone: Phone number from OCR
            postal_code: Postal code from OCR
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
        
        Returns:
            Dictionary with matched location data and confidence score, or None if no match found.
            {
                'store_name': 'Jaya Grocer',
                'branch_name': 'Jaya Grocer @ Gurney Paragon',
                'address': 'Full Google Places address',
                'latitude': 5.4356179,
                'longitude': 100.31110749999999,
                'phone': '04-291 9883',
                'rating': 4.5,
                'total_ratings': 1340,
                'confidence': 0.95,
                'match_reason': 'Exact store name + phone match'
            }
        """
        if not store_name or not self.locations:
            return None
        
        # Clean input
        store_name_clean = store_name.strip()
        
        # Find all potential matches
        candidates = self._find_candidates(store_name_clean)
        
        if not candidates:
            print(f"  ⚠️ StoreLocationService: No candidates found for '{store_name_clean}'")
            logger.info(f"No candidates found for store: {store_name_clean}")
            return None
        
        print(f"  🔍 StoreLocationService: Found {len(candidates)} candidates for '{store_name_clean}'")
        
        # Score each candidate
        scored_matches = []
        for candidate in candidates:
            confidence, reason = self._calculate_match_confidence(
                ocr_store_name=store_name_clean,
                db_store_name=candidate.get('store_name', ''),
                db_branch_name=candidate.get('branch_name', ''),
                ocr_phone=phone,
                db_phone=candidate.get('phone', ''),
                ocr_address=partial_address,
                db_address=candidate.get('address', ''),
                ocr_postal_code=postal_code
            )
            
            if confidence >= min_confidence:
                scored_matches.append({
                    **candidate,
                    'confidence': confidence,
                    'match_reason': reason
                })
        
        if not scored_matches:
            print(f"  ⚠️ StoreLocationService: No matches >= {min_confidence} threshold for '{store_name_clean}'")
            print(f"     Candidates scored but all below threshold:")
            for candidate in candidates[:3]:  # Show top 3 for debugging
                print(f"     - {candidate.get('branch_name')} (confidence would be calculated)")
            logger.info(f"No matches above confidence threshold {min_confidence} for: {store_name_clean}")
            return None
        
        # Sort by confidence (descending) and return best match
        scored_matches.sort(key=lambda x: x['confidence'], reverse=True)
        best_match = scored_matches[0]
        
        print(f"  ✅ StoreLocationService: Best match for '{store_name_clean}': {best_match['branch_name']} (confidence: {best_match['confidence']:.2f})")
        logger.info(
            f"Best match for '{store_name_clean}': {best_match['branch_name']} "
            f"(confidence: {best_match['confidence']:.2f}, reason: {best_match['match_reason']})"
        )
        
        return best_match
    
    def _find_candidates(self, store_name: str) -> List[Dict]:
        """
        Find potential candidate locations based on store name.
        
        Uses fuzzy matching to find stores even with OCR errors.
        """
        candidates = []
        store_name_lower = store_name.lower()
        
        # Strategy 1: Exact match in index
        if store_name_lower in self.store_index:
            candidates.extend(self.store_index[store_name_lower])
            logger.debug(f"Found {len(candidates)} exact matches for '{store_name}'")
            return candidates
        
        # Strategy 2: Fuzzy match against all store names
        for indexed_store_name, locations in self.store_index.items():
            ratio = fuzz.ratio(store_name_lower, indexed_store_name)
            
            # If fuzzy match is strong enough (>60%), consider these candidates
            if ratio >= 60:
                candidates.extend(locations)
                logger.debug(f"Fuzzy match: '{store_name}' → '{indexed_store_name}' (ratio: {ratio})")
        
        # Strategy 3: Partial match (e.g., "Jaya" matches "Jaya Grocer")
        if not candidates:
            for indexed_store_name, locations in self.store_index.items():
                if store_name_lower in indexed_store_name or indexed_store_name in store_name_lower:
                    candidates.extend(locations)
                    logger.debug(f"Partial match: '{store_name}' ↔ '{indexed_store_name}'")
        
        return candidates
    
    def _calculate_match_confidence(
        self,
        ocr_store_name: str,
        db_store_name: str,
        db_branch_name: str,
        ocr_phone: Optional[str],
        db_phone: str,
        ocr_address: Optional[str],
        db_address: str,
        ocr_postal_code: Optional[str]
    ) -> Tuple[float, str]:
        """
        Calculate confidence score for a potential match.
        
        Returns:
            (confidence_score, match_reason)
        """
        # Extract branch numbers/codes from OCR text and database
        ocr_branch_number = self._extract_branch_number(ocr_store_name)
        if ocr_address:
            ocr_branch_number = ocr_branch_number or self._extract_branch_number(ocr_address)
        
        db_branch_number = self._extract_branch_number(db_branch_name)
        
        # Check for branch number exact match
        branch_number_match = False
        if ocr_branch_number and db_branch_number:
            branch_number_match = ocr_branch_number == db_branch_number
        
        # Extract location keywords from OCR address
        ocr_location_keywords = self._extract_location_keywords(ocr_address) if ocr_address else set()
        db_location_keywords = self._extract_location_keywords(db_branch_name + " " + db_address)
        
        # Check for location keyword matches
        location_keyword_match = bool(ocr_location_keywords & db_location_keywords)
        matched_keywords = ocr_location_keywords & db_location_keywords
        
        # Calculate specificity of matched keywords (prefer multi-word matches)
        # e.g., "sunway carnival" (2 words) is more specific than "sunway" (1 word)
        match_specificity = 0
        if matched_keywords:
            match_specificity = max(len(kw.split()) for kw in matched_keywords)
        
        # Debug logging for location matching
        if ocr_location_keywords:
            logger.debug(f"OCR location keywords: {ocr_location_keywords}")
        if matched_keywords:
            logger.debug(f"Matched keywords: {matched_keywords} (specificity: {match_specificity})")
        
        # 1. Store name similarity (primary signal)
        name_ratio = fuzz.ratio(ocr_store_name.lower(), db_store_name.lower())
        
        # Also check against branch name (sometimes OCR captures full branch name)
        branch_ratio = fuzz.ratio(ocr_store_name.lower(), db_branch_name.lower())
        best_name_ratio = max(name_ratio, branch_ratio)
        
        # 2. Phone number match (strong signal)
        phone_match = False
        if ocr_phone and db_phone:
            phone_match = self._phone_numbers_match(ocr_phone, db_phone)
        
        # 3. Postal code match (strong signal)
        postal_match = False
        if ocr_postal_code and db_address:
            postal_match = ocr_postal_code in db_address
        
        # 4. Address partial match (city, area names)
        address_match = False
        city_match = None
        if ocr_address and db_address:
            address_match, city_match = self._addresses_match(ocr_address, db_address)
        
        # ========== PRIORITY MATCHING ==========
        
        # Highest priority: Branch number + name match
        if branch_number_match and best_name_ratio >= 80:
            return (0.98, f"Branch number match ({ocr_branch_number}) + name match")
        
        # Very high: Multi-word location match (e.g., "sunway carnival" not just "sunway")
        # Even with weaker name match, strong location match is highly reliable
        if match_specificity >= 2 and best_name_ratio >= 60:
            keywords_str = ", ".join(list(matched_keywords)[:3])
            return (0.95, f"Name + specific location match ({keywords_str})")
        
        # Very high: Multiple single-word location keywords with good name match
        if best_name_ratio >= 80 and location_keyword_match and len(matched_keywords) >= 2:
            keywords_str = ", ".join(list(matched_keywords)[:3])
            return (0.93, f"Name + location match ({keywords_str})")
        
        # High: Exact name + phone
        if best_name_ratio >= 90 and phone_match:
            return (0.95, "Exact name + phone match")
        
        # High: Name + postal
        if best_name_ratio >= 90 and postal_match:
            return (0.92, "Exact name + postal code match")
        
        # High: Name + single location keyword (could be ambiguous)
        if best_name_ratio >= 85 and location_keyword_match and match_specificity == 1:
            keywords_str = ", ".join(list(matched_keywords)[:2])
            # Lower confidence for single-word generic matches
            return (0.85, f"Name + location keyword ({keywords_str})")
        
        # Good: Name + city
        if best_name_ratio >= 90 and address_match:
            return (0.90, f"Exact name + city match ({city_match})")
        
        # Good: Strong name + additional signal
        if best_name_ratio >= 85 and (phone_match or postal_match):
            return (0.88, f"Strong name match ({best_name_ratio}%) + additional signal")
        
        # Moderate: Just name match (risky for chains with many branches)
        if best_name_ratio >= 90:
            return (0.80, f"Exact name match ({best_name_ratio}%) - no location confirmation")
        
        # Lower: Name + weak signals
        if best_name_ratio >= 80 and address_match:
            return (0.80, f"Strong name match ({best_name_ratio}%) + city match ({city_match})")
        
        elif best_name_ratio >= 80:
            return (0.70, f"Strong name match ({best_name_ratio}%) - no location confirmation")
        
        elif best_name_ratio >= 70:
            return (0.60, f"Moderate name match ({best_name_ratio}%)")
        
        else:
            return (0.50, f"Weak name match ({best_name_ratio}%)")
    
    def _phone_numbers_match(self, phone1: str, phone2: str) -> bool:
        """
        Check if two phone numbers match.
        
        Normalizes phone numbers by removing spaces, dashes, and country codes,
        then compares the last 7-8 digits.
        """
        # Extract digits only
        digits1 = ''.join(filter(str.isdigit, phone1))
        digits2 = ''.join(filter(str.isdigit, phone2))
        
        if not digits1 or not digits2:
            return False
        
        # Compare last 7 digits (local number without area code)
        # Malaysian numbers are typically 9-10 digits
        min_length = min(len(digits1), len(digits2))
        compare_length = min(7, min_length)
        
        return digits1[-compare_length:] == digits2[-compare_length:]
    
    def _addresses_match(self, ocr_address: str, db_address: str) -> Tuple[bool, Optional[str]]:
        """
        Check if addresses partially match (city, area, postal code).
        
        Returns:
            (match_found, matched_city_name)
        """
        ocr_lower = ocr_address.lower()
        db_lower = db_address.lower()
        
        # Malaysian cities and areas to look for
        malaysian_locations = [
            'kuala lumpur', 'kl', 'penang', 'pulau pinang', 'pg', 'george town',
            'johor bahru', 'johor', 'ipoh', 'perak', 'shah alam', 'selangor',
            'petaling jaya', 'pj', 'klang', 'melaka', 'malacca',
            'kuching', 'sarawak', 'kota kinabalu', 'sabah',
            'seremban', 'negeri sembilan', 'alor setar', 'kedah',
            'kuantan', 'pahang', 'kota bharu', 'kelantan',
            'bukit mertajam', 'seberang jaya', 'butterworth',
            'cyberjaya', 'putrajaya', 'subang jaya', 'damansara',
            'bangsar', 'cheras', 'ampang', 'puchong'
        ]
        
        # Check for city/area matches
        for location in malaysian_locations:
            if location in ocr_lower and location in db_lower:
                return (True, location.title())
        
        # Check for postal code match (5 digits in Malaysia)
        postal_pattern = r'\b\d{5}\b'
        ocr_postal = re.findall(postal_pattern, ocr_address)
        db_postal = re.findall(postal_pattern, db_address)
        
        if ocr_postal and db_postal:
            if any(p in db_postal for p in ocr_postal):
                return (True, f"Postal code {ocr_postal[0]}")
        
        return (False, None)
    
    def _extract_branch_number(self, text: str) -> Optional[str]:
        """
        Extract branch number/code from text.
        
        Examples:
            "99 Speed Mart 2868-PG" -> "2868"
            "7-Eleven Store #1234" -> "1234"
            "Jaya Grocer @ Gurney Paragon" -> None
        
        Returns:
            Branch number as string, or None if not found
        """
        if not text:
            return None
        
        import re
        
        # Pattern 1: 4-digit store numbers (common in 99 Speedmart, 7-Eleven)
        # e.g., "2868-PG", "2868 PG", "Store 2868"
        match = re.search(r'\b(\d{4})\b', text)
        if match:
            return match.group(1)
        
        # Pattern 2: 3-digit store numbers
        match = re.search(r'\b(\d{3})\b', text)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_location_keywords(self, text: str) -> Set[str]:
        """
        Extract significant location keywords from text.
        
        Focuses on:
        - Mall/shopping center names
        - Business park names
        - Specific area/neighborhood names
        - Landmark names
        
        Returns:
            Set of normalized location keywords
        """
        if not text:
            return set()
        
        text_lower = text.lower()
        keywords = set()
        
        # Malaysian malls and landmarks
        known_locations = [
            # Business parks
            'gravitas', 'gravitas business park',
            'elite business park', 'elite pavilion',
            'menara', 'plaza', 'tower',
            'business park', 'commercial centre', 'commercial center',
            
            # Major malls
            'sunway carnival', 'sunway carnival mall',  # Penang location
            'sunway pyramid', 'sunway pyramid mall',    # Petaling Jaya location
            'sunway putra', 'sunway putra mall',
            'sunway velocity', 'sunway velocity mall',
            'sunway geo', 'sunway giza',
            'dataran sunway',
            'mid valley', 'midvalley',
            'pavilion', 'klcc', 'suria klcc',
            'one utama', '1 utama', 'the curve',
            'gurney', 'gurney plaza', 'gurney paragon',
            'queensbay', 'queensbay mall',
            'komtar', 'prangin mall',
            'ikea', 'aeon mall', 'ioi mall',
            
            # Specific areas/neighborhoods
            'bukit bintang', 'bangsar', 'damansara',
            'mont kiara', 'hartamas', 'ampang',
            'cheras', 'setapak', 'wangsa maju',
            'kepong', 'puchong', 'subang',
            'usj', 'ss2', 'ss15',
            'kl', 'kuala lumpur',  # KL abbreviations
            
            # Penang areas
            'egate', 'e-gate', 'butterworth',
            'bayan lepas', 'bayan baru',
            'tanjung tokong', 'pulau tikus',
            'jelutong', 'georgetown', 'george town',
            'bukit mertajam', 'seberang jaya',
            'the sun', 'the zen', 'skyline city',
            'prangin mall', 'krystal point', 'arena curve',
            'sunway wellesley', 'golden triangle',
            'pg', 'penang', 'pulau pinang',  # Penang abbreviations and names
            
            # Other cities
            'ipoh', 'johor bahru', 'jb',
            'melaka', 'malacca', 'seremban',
            'kuantan', 'kota kinabalu', 'kuching'
        ]
        
        for location in known_locations:
            if location in text_lower:
                # Normalize the keyword (remove spaces, hyphens for matching)
                normalized = location.replace(' ', '').replace('-', '').replace("'", '')
                keywords.add(normalized)
                # Also add the original for better matching
                keywords.add(location)
        
        # Additionally extract any capitalized words (likely proper nouns/landmarks)
        # e.g., "Gravitas", "Queensbay", "KLCC"
        import re
        proper_nouns = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
        for noun in proper_nouns:
            if len(noun) > 3:  # Skip short words like "The", "At"
                keywords.add(noun.lower())
        
        # Remove overly generic keywords that don't help disambiguation
        # (Applied at the end to catch all sources of generic keywords)
        generic_keywords = {'malaysia', 'malaysian', 'my', 'asia', 'wilayah', 'federal', 'territory'}
        keywords = keywords - generic_keywords
        
        return keywords
    
    def get_all_stores(self) -> List[str]:
        """Get list of all unique store names in the database."""
        return list(self.store_index.keys())
    
    def get_locations_for_store(self, store_name: str) -> List[Dict]:
        """Get all locations for a specific store."""
        return self.store_index.get(store_name.lower(), [])
    
    def get_stats(self) -> Dict:
        """Get statistics about the location database."""
        return {
            'total_locations': len(self.locations),
            'total_stores': len(self.store_index),
            'stores': {
                store: len(locations) 
                for store, locations in self.store_index.items()
            }
        }
