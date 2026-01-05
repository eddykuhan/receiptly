"""
Category Normalization Service for Retail ETL Pipeline

Ensures consistent category naming across all data sources by:
- Normalizing case variations (beverages → Beverages)
- Handling spelling differences (Yogurt vs Yoghurt)
- Trimming whitespace
- Fixing UTF-8 encoding issues
- Applying title case to unknown categories

This prevents duplicate categories from entering the database.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CategoryNormalizer:
    """
    Normalizes product category names to ensure consistency across different retailers.
    
    Mirrors the C# CategoryNormalizationService implementation for consistency.
    """
    
    # Standard category mapping (case-insensitive keys)
    CATEGORY_ALIASES = {
        # Spelling variations (British vs American)
        "yogurt": "Yogurt",
        "yoghurt": "Yogurt",
        
        # Case variations (common patterns from different retailers)
        "beverages": "Beverages",
        "chilled and frozen": "Chilled and Frozen",
        "food essentials": "Food Essentials",
        "fresh market": "Fresh Market",
        "household products": "Household Products",
        "snacks": "Snacks",
        
        # Whitespace issues (trailing spaces from OCR)
        "uht milk": "UHT Milk",
        "adult milk": "Adult Milk",
        
        # Encoding issues (UTF-8 problems)
        "ros ÿwine": "Rosé Wine",
        "rosé wine": "Rosé Wine",
        
        # Common retailer variations
        "biscuits & crackers": "Biscuits & Crackers",
        "biscuits and cookies": "Biscuits & Cookies",
        "health & beauty": "Health & Beauty",
        "health and beauty": "Health & Beauty",
        "meat & poultry": "Meat & Poultry",
        "dairy & eggs": "Dairy & Eggs",
        
        # Uncategorized/Unknown variations
        "uncategorized": "Unknown",
        "others": "Unknown",
        "": "Unknown",
        
        # All products (generic category)
        "all products": "All Products",
        
        # Additional common variations
        "bread & pastry": "Bread & Pastry",
        "pasta & instant food": "Pasta & Instant Food",
        "instant noodles": "Instant Noodles",
        "canned fish & seafood": "Canned Fish & Seafood",
        "fruits, beans, nuts & seeds": "Fruits, Beans, Nuts & Seeds",
        "cooking paste": "Cooking Paste",
        "herbs & spices": "Herbs & Spices",
        "sauces & specialty": "Sauces & Specialty",
        "rice & agriculture": "Rice & Agriculture",
    }
    
    def normalize(self, category: Optional[str]) -> str:
        """
        Normalize a category name to its canonical form.
        
        Args:
            category: Raw category name from scraper/OCR
            
        Returns:
            Normalized category name in title case
        """
        if not category or not category.strip():
            return "Unknown"
        
        # Step 1: Trim whitespace and fix encoding issues
        normalized = category.strip()
        normalized = self._fix_encoding(normalized)
        
        # Step 2: Check against known aliases (case-insensitive)
        lower_key = normalized.lower()
        if lower_key in self.CATEGORY_ALIASES:
            canonical = self.CATEGORY_ALIASES[lower_key]
            if canonical != normalized:
                logger.debug(f"Normalized category '{category}' → '{canonical}'")
            return canonical
        
        # Step 3: Apply title case for unknown categories
        title_cased = self._to_title_case(normalized)
        
        if title_cased != normalized:
            logger.debug(f"Applied title case to category '{category}' → '{title_cased}'")
        
        return title_cased
    
    def _fix_encoding(self, text: str) -> str:
        """Fix common UTF-8 encoding issues."""
        # Common encoding issues
        replacements = {
            "???ÿ": "é",
            "â€™": "'",
            "â€œ": '"',
            "â€": '"',
        }
        
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        
        return text
    
    def _to_title_case(self, text: str) -> str:
        """
        Convert string to title case with special handling for acronyms.
        
        Preserves:
        - All-uppercase acronyms (UHT, MSG, etc.)
        - Mixed case words (iOS, JavaScript)
        - Ampersands
        """
        if not text:
            return text
        
        # Split by common separators
        words = []
        for word in text.replace('-', ' ').replace('/', ' ').replace('&', ' & ').split():
            # Skip ampersands
            if word == '&':
                words.append('&')
                continue
            
            # Preserve all-uppercase acronyms (length <= 4)
            if len(word) <= 4 and word.isupper():
                words.append(word)
            # Preserve words with mixed case (e.g., iOS, JavaScript)
            elif any(c.isupper() for c in word) and any(c.islower() for c in word):
                words.append(word)
            # Apply title case to lowercase words
            else:
                words.append(word.capitalize())
        
        result = ' '.join(words)
        
        # Clean up multiple spaces
        result = ' '.join(result.split())
        
        return result
    
    def normalize_batch(self, categories: list) -> list:
        """
        Normalize a batch of categories.
        
        Args:
            categories: List of raw category names
            
        Returns:
            List of normalized category names
        """
        return [self.normalize(cat) for cat in categories]


# Singleton instance
_normalizer = CategoryNormalizer()


def normalize_category(category: Optional[str]) -> str:
    """
    Convenience function to normalize a single category.
    
    Args:
        category: Raw category name
        
    Returns:
        Normalized category name
    """
    return _normalizer.normalize(category)


def normalize_categories(categories: list) -> list:
    """
    Convenience function to normalize multiple categories.
    
    Args:
        categories: List of raw category names
        
    Returns:
        List of normalized category names
    """
    return _normalizer.normalize_batch(categories)
