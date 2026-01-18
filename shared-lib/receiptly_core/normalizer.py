"""
Text normalization utilities for product canonicalization.
"""
import re


# Multilingual translation dictionary (Malay/Indonesian -> English)
# This helps match products with different language names
TRANSLATION_MAP = {
   
    # =========================
    # Cooking oils & fats
    # =========================
    'minyak masak': 'cooking oil',
    'minyak goreng': 'cooking oil',
    'minyak sayur': 'vegetable oil',
    'minyak jagung': 'corn oil',
    'minyak kelapa': 'coconut oil',
    'minyak zaitun': 'olive oil',
    'minyak sawit': 'palm oil',
    'mentega': 'butter',
    'marjerin': 'margarine',

    # =========================
    # Rice & grains
    # =========================
    'beras': 'rice',
    'nasi': 'rice',
    'tepung': 'flour',
    'tepung gandum': 'wheat flour',
    'tepung roti': 'bread flour',
    'mi': 'noodles',
    'mee': 'noodles',
    'bihun': 'vermicelli',
    'bijiran': 'cereal',
    'jagung': 'corn',
    'barli': 'barley',

    # =========================
    # Sugar & sweeteners
    # =========================
    'gula': 'sugar',
    'gula pasir': 'granulated sugar',
    'gula merah': 'brown sugar',
    'madu': 'honey',

    # =========================
    # Dairy
    # =========================
    'susu': 'milk',
    'susu kotak': 'milk drink',
    'keju': 'cheese',
    'yogurt': 'yogurt',
    'krim': 'cream',

    # =========================
    # Meat & poultry
    # =========================
    'ayam': 'chicken',
    'ayam goreng': 'fried chicken',
    'ayam segar': 'fresh chicken',
    'ayam potong': 'cut chicken',
    'ayam beku': 'frozen chicken',
    'daging ayam': 'chicken meat',
    'daging ayam kisar': 'minced chicken',
    'daging lembu': 'beef',
    'daging lembu kisar': 'minced beef',
    'daging kambing': 'mutton',
    'daging babi': 'pork',
    'itik': 'duck',
    'puyuh': 'quail',
    'sosej': 'sausage',
    'sosej ayam': 'chicken sausage',
    'sosej daging': 'beef sausage',
    'burger': 'burger patty',

    # =========================
    # Eggs & alternatives
    # =========================
    'telur': 'egg',
    'telur ayam': 'chicken egg',
    'telur itik': 'duck egg',
    'telur gred a': 'egg grade a',
    'telur gred b': 'egg grade b',
    'telur gred c': 'egg grade c',
    'tahu': 'tofu',
    'tauhu': 'tofu',
    'tempe': 'tempeh',

    # =========================
    # Seafood
    # =========================
    'ikan': 'fish',
    'ikan kembung': 'mackerel',
    'ikan bilis': 'anchovy',
    'ikan selar': 'scad',
    'ikan tenggiri': 'spanish mackerel',
    'ikan merah': 'red snapper',
    'ikan siakap': 'barramundi',
    'ikan keli': 'catfish',
    'ikan patin': 'pangasius',
    'udang': 'prawn',
    'udang besar': 'large prawn',
    'udang kecil': 'small prawn',
    'sotong': 'squid',
    'ketam': 'crab',
    'kerang': 'cockle',
    'kupang': 'mussel',

    # =========================
    # Fruits
    # =========================
    'buah': 'fruit',
    'pisang': 'banana',
    'epal': 'apple',
    'oren': 'orange',
    'limau': 'lime',
    'limau nipis': 'lime',
    'limau kasturi': 'calamansi',
    'mangga': 'mango',
    'betik': 'papaya',
    'tembikai': 'watermelon',
    'anggur': 'grape',
    'nanas': 'pineapple',
    'strawberi': 'strawberry',
    'kiwi': 'kiwi',
    'pear': 'pear',

    # =========================
    # Vegetables
    # =========================
    'sayur': 'vegetable',
    'sayur sayuran': 'vegetable',
    'sawi': 'mustard greens',
    'sawi hijau': 'mustard greens',
    'kobis': 'cabbage',
    'kobis bulat': 'cabbage',
    'kobis bunga': 'cauliflower',
    'brokoli': 'broccoli',
    'bayam': 'spinach',
    'kangkung': 'water spinach',
    'lobak': 'radish',
    'lobak merah': 'carrot',
    'timun': 'cucumber',
    'tomato': 'tomato',
    'terung': 'eggplant',
    'bendi': 'okra',
    'kentang': 'potato',
    'bawang': 'onion',
    'bawang besar': 'onion',
    'bawang kecil': 'shallot',
    'bawang merah': 'red onion',
    'bawang putih': 'garlic',
    'halia': 'ginger',
    'kunyit': 'turmeric',
    'serai': 'lemongrass',

    # =========================
    # Bakery & breakfast
    # =========================
    'roti': 'bread',
    'roti putih': 'white bread',
    'roti gandum': 'whole wheat bread',
    'roti canai': 'flatbread',
    'roti bakar': 'toast',
    'mentega kacang': 'peanut butter',
    'jem': 'jam',
    'jem strawberi': 'strawberry jam',
    'bijirin sarapan': 'breakfast cereal',

    # =========================
    # Instant & frozen foods
    # =========================
    'mi segera': 'instant noodles',
    'mee segera': 'instant noodles',
    'kari': 'curry',
    'kari ayam': 'chicken curry',
    'pes kari': 'curry paste',
    'pes cili': 'chili paste',
    'beku': 'frozen',
    'sejuk': 'chilled',
    'ais krim': 'ice cream',
    'nugget ayam': 'chicken nugget',
    'kentang goreng': 'french fries',

    # =========================
    # Condiments & sauces
    # =========================
    'sos': 'sauce',
    'kicap': 'soy sauce',
    'cuka': 'vinegar',
    'garam': 'salt',
    'lada': 'pepper',
    'cili': 'chili',
    'sambal': 'chili paste',
    'kuah': 'gravy',

    # =========================
    # Snacks & sweets
    # =========================
    'coklat': 'chocolate',
    'biskut': 'biscuit',
    'kek': 'cake',
    'kerepek': 'chips',
    'gula gula': 'candy',

    # =========================
    # Canned & preserved
    # =========================
    'tin': 'can',
    'tin kecil': 'small can',
    'tin besar': 'large can',
    'sardin': 'sardine',
    'tuna': 'tuna',

    # =========================
    # Beverages
    # =========================
    'air': 'water',
    'teh': 'tea',
    'kopi': 'coffee',
    'jus': 'juice',
    'minuman': 'drink',
    'bir': 'beer',
    'asli': 'original',
    'segar': 'fresh',
    'dingin': 'cold',

    # =========================
    # Household & cleaning
    # =========================
    'sabun': 'soap',
    'pencuci': 'detergent',
    'pembersih': 'cleaner',
    'sampo': 'shampoo',
    'ubat gigi': 'toothpaste',
    'kertas tandas': 'toilet paper',
    'tisu': 'tissue',
    'tisu basah': 'wet wipes',
    'plastik': 'plastic',
    'plastik sampah': 'trash bag',

    # =========================
    # Packaging & descriptors
    # =========================
    'pek': 'pack',
    'paket': 'pack',
    'botol': 'bottle',
    'isi': 'contents',
    'campur': 'mixed',
    'daun': 'leaf',

    # =========================
    # Quality / attributes
    # =========================
    'organik': 'organic',
    'premium': 'premium',
    'murah': 'cheap',
    'mahal': 'expensive',
    'tanpa gula': 'sugar free',
    'rendah lemak': 'low fat',
    'penuh krim': 'full cream',

    # =========================
    # Units & sizes
    # =========================
    'besar': 'large',
    'kecil': 'small',
    'sederhana': 'medium',
    'kg': 'kg',
    'gm': 'g',
    'gram': 'g',
    'liter': 'l'
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
