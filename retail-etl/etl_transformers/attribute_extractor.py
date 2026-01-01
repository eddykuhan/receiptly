"""
Attribute Extractor for Amazon-style canonicalization.

Extracts structured attributes (brand, size, variant, tokens) from product names
to enable precise matching and fast candidate generation.
"""
import re
from typing import Dict, Optional, Tuple, List


class AttributeExtractor:
    """Extract structured attributes from product names (Amazon-style)."""
    
    # Common brand patterns (Malaysia-specific)
    KNOWN_BRANDS = {
        'farm fresh', 'dutch lady', 'nestle', 'magnolia', 'f&n',
        'marigold', 'anmum', 'anchor', 'devondale', 'paul', 'meiji',
        'ayam brand', 'fernleaf', 'ideal', 'nespray', 'frisolac',
        'lactogen', 'dumex', 'similac', 'enfagrow', 'friso',
        'gardenia', 'massimo', 'sunshine', 'super ring', 'julies',
        'hup seng', 'khong guan', 'munchy', 'oriental', 'mamee',
        'milo', 'nescafe', 'ovaltine', 'vico', 'horlicks',
        'sunquick', 'ribena', 'tropicana', 'twister', 'minute maid',
        'maggi', 'knorr', 'ajinomoto', 'adabi', 'tumix',
        'cap udang', 'cap burung', 'cap ayam', 'cap ibu', 'baba'
    }
    
    # Size patterns (matches common units)
    SIZE_PATTERN = re.compile(
        r'(\d+(?:\.\d+)?)\s*(l|litre|liter|ml|milliliter|millilitre|'
        r'kg|kilogram|kilograms|g|gram|grams|oz|ounce|lb|pound|'
        r'pack|pkt|sachet)s?\b',
        re.IGNORECASE
    )
    
    # Pack count patterns
    PACK_PATTERN = re.compile(
        r'(\d+)\s*(?:pack|x|pk|pcs?|pieces?|units?|tins?|cans?|bottles?)',
        re.IGNORECASE
    )
    
    def extract_brand(self, text: str) -> Optional[str]:
        """
        Extract brand from product name.
        Uses known brands list + first 2-3 capitalized tokens as fallback.
        
        Args:
            text: Product name
            
        Returns:
            Brand name in title case, or None
        """
        text_lower = text.lower()
        
        # Check known brands (longest match first to handle multi-word brands)
        sorted_brands = sorted(self.KNOWN_BRANDS, key=len, reverse=True)
        for brand in sorted_brands:
            if brand in text_lower:
                return brand.title()
        
        # Fallback: first 2-3 tokens before common product type words
        tokens = text.split()
        product_types = {
            'milk', 'bread', 'rice', 'oil', 'coffee', 'tea', 'juice',
            'biscuit', 'cookie', 'noodle', 'pasta', 'sauce', 'powder',
            'cream', 'butter', 'cheese', 'yogurt', 'drink', 'water',
            'cereal', 'oat', 'flour', 'sugar', 'salt', 'pepper'
        }
        
        brand_tokens = []
        for i, token in enumerate(tokens):
            if token.lower() in product_types:
                break
            if i < 3:  # Max 3 tokens for brand
                brand_tokens.append(token)
        
        if brand_tokens:
            return ' '.join(brand_tokens).title()
        
        return None
    
    def extract_size(self, text: str) -> Tuple[Optional[str], Optional[float], Optional[str]]:
        """
        Extract size from product name and normalize to base units.
        
        Args:
            text: Product name
            
        Returns:
            Tuple of (original_size, normalized_size, unit)
            Example: ("2L", 2.0, "L"), ("500ml", 0.5, "L")
        """
        match = self.SIZE_PATTERN.search(text)
        if not match:
            return None, None, None
        
        value = float(match.group(1))
        unit = match.group(2).lower()
        
        # Normalize to base units
        if unit in ['ml', 'milliliter', 'millilitre']:
            normalized_value = value / 1000
            normalized_unit = 'L'
        elif unit in ['l', 'liter', 'litre']:
            normalized_value = value
            normalized_unit = 'L'
        elif unit in ['g', 'gram', 'grams']:
            normalized_value = value / 1000
            normalized_unit = 'kg'
        elif unit in ['kg', 'kilogram', 'kilograms']:
            normalized_value = value
            normalized_unit = 'kg'
        elif unit in ['oz', 'ounce']:
            normalized_value = value * 0.0283495  # oz to kg
            normalized_unit = 'kg'
        elif unit in ['lb', 'pound']:
            normalized_value = value * 0.453592  # lb to kg
            normalized_unit = 'kg'
        else:
            # Unknown unit, keep as-is
            normalized_value = value
            normalized_unit = unit.upper()
        
        # Format original size
        original_size = f"{value}{unit.upper()}"
        
        return original_size, normalized_value, normalized_unit
    
    def extract_pack_count(self, text: str) -> int:
        """
        Extract pack count from product name.
        
        Args:
            text: Product name
            
        Returns:
            Pack count (defaults to 1)
        """
        match = self.PACK_PATTERN.search(text)
        if match:
            return int(match.group(1))
        return 1
    
    def extract_variant(self, text: str, brand: Optional[str], size: Optional[str]) -> Optional[str]:
        """
        Extract variant description (what's left after removing brand + size).
        
        Args:
            text: Product name
            brand: Extracted brand
            size: Extracted size (original)
            
        Returns:
            Variant description in title case, or None
        """
        clean_text = text.lower()
        
        # Remove brand
        if brand:
            clean_text = re.sub(re.escape(brand.lower()), '', clean_text, count=1)
        
        # Remove size
        if size:
            clean_text = re.sub(re.escape(size.lower()), '', clean_text, count=1)
        
        # Remove pack count indicators
        clean_text = self.PACK_PATTERN.sub('', clean_text)
        
        # Clean up extra whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text.strip())
        
        if clean_text:
            return clean_text.title()
        
        return None
    
    def extract_key_tokens(self, text: str) -> List[str]:
        """
        Extract discriminative tokens for fast candidate generation.
        Filters stopwords and short tokens.
        
        Args:
            text: Product name
            
        Returns:
            List of key tokens (lowercase)
        """
        text_lower = text.lower()
        
        # Remove special characters, keep alphanumeric and spaces
        text_lower = re.sub(r'[^a-z0-9\s]', ' ', text_lower)
        
        # Remove common stopwords
        stopwords = {'the', 'and', 'with', 'or', 'of', 'a', 'an', 'for', 'in', 'on'}
        tokens = [
            t for t in text_lower.split() 
            if t not in stopwords and len(t) > 1
        ]
        
        return tokens
    
    def extract_all_attributes(self, item_name: str) -> Dict:
        """
        Extract all structured attributes from product name.
        This is the main entry point for attribute extraction.
        
        Args:
            item_name: Raw product name
            
        Returns:
            Dictionary containing all extracted attributes
        """
        brand = self.extract_brand(item_name)
        size_orig, size_norm, size_unit = self.extract_size(item_name)
        pack_count = self.extract_pack_count(item_name)
        variant = self.extract_variant(item_name, brand, size_orig)
        tokens = self.extract_key_tokens(item_name)
        
        return {
            'brand': brand,
            'size': size_orig,
            'size_normalized': size_norm,
            'size_unit': size_unit,
            'pack_count': pack_count,
            'variant': variant,
            'name_tokens': tokens
        }


# Example usage and testing
if __name__ == "__main__":
    extractor = AttributeExtractor()
    
    # Test cases
    test_items = [
        "Farm Fresh Pure Fresh Milk 2L",
        "Dutch Lady Full Cream Milk 1 Litre",
        "Nestle Omega Plus Milk 500ml X 3 Pack",
        "Gardenia White Bread 400g",
        "Milo Activ-Go 1kg",
        "Maggi Curry Flavour 5 Pack 79g",
    ]
    
    print("Testing Attribute Extraction:")
    print("=" * 80)
    
    for item in test_items:
        attrs = extractor.extract_all_attributes(item)
        print(f"\nInput: {item}")
        print(f"  Brand: {attrs['brand']}")
        print(f"  Size: {attrs['size']} (normalized: {attrs['size_normalized']} {attrs['size_unit']})")
        print(f"  Pack: {attrs['pack_count']}")
        print(f"  Variant: {attrs['variant']}")
        print(f"  Tokens: {attrs['name_tokens']}")
