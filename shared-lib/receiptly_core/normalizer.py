"""
Text normalization utilities for product canonicalization.
"""
import re


# Multilingual translation dictionary (Malay/Indonesian -> English)
# This helps match products with different language names
TRANSLATION_MAP = {
    # Cooking oils & fats
    'minyak masak': 'cooking oil',
    'minyak goreng': 'cooking oil',
    'minyak sayur': 'vegetable oil',
    'minyak jagung': 'corn oil',
    'minyak kelapa': 'coconut oil',
    'minyak zaitun': 'olive oil',
    'minyak sawit': 'palm oil',
    'mentega': 'butter',
    'marjerin': 'margarine',
    
    # Rice & grains
    'beras': 'rice',
    'nasi': 'rice',
    'tepung': 'flour',
    'tepung gandum': 'wheat flour',
    'tepung roti': 'bread flour',
    'mi': 'noodles',
    'mee': 'noodles',
    'bihun': 'vermicelli',
    
    # Sugar & sweeteners
    'gula': 'sugar',
    'gula pasir': 'granulated sugar',
    'gula merah': 'brown sugar',
    'madu': 'honey',
    
    # Dairy
    'susu': 'milk',
    'keju': 'cheese',
    'yogurt': 'yogurt',
    'krim': 'cream',
    
    # Meat & Poultry
    'ayam goreng': 'fried chicken',
    'daging ayam': 'chicken meat',
    'ayam': 'chicken',
    'daging lembu': 'beef',
    'daging kambing': 'mutton',
    'daging babi': 'pork',
    'itik': 'duck',
    'puyuh': 'quail',
    'telur ayam': 'chicken egg',
    'telur itik': 'duck egg',
    'telur': 'egg',
    'ikan': 'fish',
    'udang': 'prawn',
    'sotong': 'squid',
    'ketam': 'crab',
    
    # Beverages
    'air': 'water',
    'teh': 'tea',
    'kopi': 'coffee',
    'jus': 'juice',
    'minuman': 'drink',
    'susu kotak': 'milk drink',
    'bir': 'beer',
    
    # Condiments & sauces
    'sos': 'sauce',
    'kicap': 'soy sauce',
    'cuka': 'vinegar',
    'garam': 'salt',
    'lada': 'pepper',
    'cili': 'chili',
    'sambal': 'chili paste',
    'kuah': 'gravy',
    
    # Snacks & sweets
    'coklat': 'chocolate',
    'biskut': 'biscuit',
    'kek': 'cake',
    'roti': 'bread',
    'kerepek': 'chips',
    'gula gula': 'candy',
    
    # Canned & preserved
    'tin': 'can',
    'sardin': 'sardine',
    'tuna': 'tuna',
    
    # Cleaning products
    'sabun': 'soap',
    'pencuci': 'detergent',
    'pembersih': 'cleaner',
    'sampo': 'shampoo',
    'ubat gigi': 'toothpaste',
    
    # Units & sizes
    'besar': 'large',
    'kecil': 'small',
    'sederhana': 'medium',
    'kg': 'kg',
    'gm': 'g',
    'gram': 'g',
    'liter': 'l',
}


def translate_to_english(text: str) -> str:
    """
    Translate common Malay/Indonesian product terms to English.
    
    Args:
        text: Product text (already lowercased)
        
    Returns:
        Text with translations applied
    """
    # Sort by length (longest first) to avoid partial replacements
    # e.g., "minyak masak" should be translated before "minyak"
    sorted_terms = sorted(TRANSLATION_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    
    for malay_term, english_term in sorted_terms:
        # Use word boundaries to avoid partial word replacements
        pattern = r'\b' + re.escape(malay_term) + r'\b'
        text = re.sub(pattern, english_term, text)
    
    return text


def normalize_text(text: str) -> str:
    """
    Normalize product text for matching with multilingual support.
    
    Args:
        text: Raw product text
        
    Returns:
        Normalized text (lowercase, translated, alphanumeric + spaces, cleaned)
    """
    text = text.lower()
    
    # Apply translations before other normalization
    text = translate_to_english(text)
    
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s1\sunit$', '', text)  # Remove "1 unit" suffix
    text = re.sub(r'\s+', ' ', text.strip())
    return text
