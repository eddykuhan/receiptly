import json
import pandas as pd
import uuid
from datetime import datetime
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "receiptly")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DB_CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DATA_DIR = "data"

# File paths
JAYA_GROCER_PRODUCTS_FILE = os.path.join(DATA_DIR, "jaya_grocer_products_penang.json")
MYDIN_PRODUCTS_FILE = os.path.join(DATA_DIR, "mydin_scrapy_products.json")
JAYA_GROCER_LOCATIONS_FILE = os.path.join(DATA_DIR, "jaya_grocer_locations.json")
MYDIN_LOCATIONS_FILE = os.path.join(DATA_DIR, "mydin_locations.json")

# Filter Definition
GROCERY_CATEGORIES = {
    "Bakery", "Beverages", "Biscuits & Crackers", "Biscuits and Cookies", 
    "Blended & Cooking Oil", "Breadcrumbs & Stuffing", "Breakfast", 
    "Cake Ingredients & Deco", "Candies & Sweets", "Canned Seafood", "Cereal", 
    "Chicken", "chilled and frozen", "Chilled and Frozen", "Chilled Dips", 
    "Chilled Juice", "Chilled Pork", "Chocolates", "Coffee", "Condiments", 
    "Cooking Paste", "Dairy", "Dressing & Topping", "Dried Goods", "Drinks", 
    "Eggs", "Flour", "food essentials", "Food Essentials", "fresh Market", 
    "Fresh Market", "Frozen Meat", "Frozen Others", "Fruit & Herbal Tea", 
    "Grapes", "Herbs & Spices", "Honey", "Hot Cereal & Oat", 
    "Ice Cream, Sandwiches & Cones", "Instant Meals", "Instant Noodles", 
    "Instant Soup Mix", "Jam & Marmalade", "Japan Snacks", "Jellies & Puddings", 
    "Jelly Powder & Mix", "Lamb", "Leafy Vegetables", "Marinated", "Milk", 
    "Nuts and Seeds", "Olive Oil", "Onions and Garlic", "Organic Cereal", 
    "Organic Cereal and Oat", "Organic Herbs & Spices", "Organic Juice", 
    "Organic Noodles & Pasta", "Organic Oat, Soy and Milk", 
    "Organic Rice, Grains & Dried Goods", "Organic Rice, Grains and Dried Goods", 
    "Organic Sauces, Condiments & Oil", "Organics", "Other Chips", "Other Juice", 
    "Others (Pork)", "Pasta", "Pastes & Mixes", "Pastry and Puff", "Pepper", 
    "Pickles", "Pork and Non-Halal", "Potato and Corn Chips", 
    "Potato, Corn & Tortilla Chips", "Powder Mixes", "Preserved Vegetables", 
    "Pretzel & Popcorn", "Ready Meal", "Ready Meals", "Ready-to-Drink", "Rice", 
    "Salad Vegetables", "Salt & MSG", "Sauces & Specialty", "Seasoning", 
    "Sesame Oil", "Snacks", "Specialty Oil", "Stock, Gravy & Broth", "Tea Bags", 
    "Tofu, Noodles and Others", "Tomato & Vegetable Juice", "Tropical Fruits", 
    "UHT Milk", "Vermicelli", "Vinegar", "Yogurt"
}

# For Mydin, since we lack categories, we use keywords in item name
GROCERY_KEYWORDS = [
    "rice", "beras", "oil", "minyak", "sugar", "gula", "salt", "garam", 
    "flour", "tepung", "noodle", "mee", "mi", "bihun", "kway teow", 
    "coffee", "kopi", "tea", "teh", "milk", "susu", "creamer", "milo", 
    "chocolate", "coklat", "biscuit", "biskut", "cracker", "bread", "roti", 
    "sauce", "sos", "kicap", "paste", "pes", "spices", "rempah", "seasoning", 
    "perencah", "chicken", "ayam", "beef", "daging", "fish", "ikan", 
    "sardine", "sardin", "tuna", "vegetable", "sayur", "fruit", "buah", 
    "drink", "minuman", "water", "air", "juice", "jus", "cordial", "sirap", 
    "jam", "jem", "kaya", "butter", "mentega", "margarine", "cheese", "keju", 
    "yogurt", "egg", "telur", "cereal", "oat", "honey", "madu"
]

# Mapping for Mydin Category Inference
KEYWORD_CATEGORY_MAP = {
    "rice": "Rice", "beras": "Rice",
    "oil": "Blended & Cooking Oil", "minyak": "Blended & Cooking Oil",
    "sugar": "Sugar & Sweeteners", "gula": "Sugar & Sweeteners",
    "salt": "Salt & Seasoning", "garam": "Salt & Seasoning",
    "flour": "Flour", "tepung": "Flour",
    "noodle": "Noodles", "mee": "Noodles", "mi": "Noodles", "bihun": "Noodles", "kway teow": "Noodles",
    "coffee": "Coffee", "kopi": "Coffee",
    "tea": "Tea", "teh": "Tea",
    "milk": "Milk", "susu": "Milk",
    "creamer": "Dairy",
    "milo": "Beverages",
    "chocolate": "Chocolates", "coklat": "Chocolates",
    "biscuit": "Biscuits & Crackers", "biskut": "Biscuits & Crackers", "cracker": "Biscuits & Crackers",
    "bread": "Bakery", "roti": "Bakery",
    "sauce": "Sauces & Specialty", "sos": "Sauces & Specialty", "kicap": "Sauces & Specialty",
    "paste": "Cooking Paste", "pes": "Cooking Paste",
    "spices": "Herbs & Spices", "rempah": "Herbs & Spices",
    "seasoning": "Seasoning", "perencah": "Seasoning",
    "chicken": "Chicken", "ayam": "Chicken",
    "beef": "Frozen Meat", "daging": "Frozen Meat",
    "fish": "Seafood", "ikan": "Seafood", "sardine": "Seafood", "sardin": "Seafood", "tuna": "Seafood",
    "vegetable": "Vegetables", "sayur": "Vegetables",
    "fruit": "Fruits", "buah": "Fruits",
    "drink": "Drinks", "minuman": "Drinks",
    "water": "Drinks", "air": "Drinks",
    "juice": "Drinks", "jus": "Drinks",
    "cordial": "Drinks", "sirap": "Drinks",
    "jam": "Jam & Marmalade", "jem": "Jam & Marmalade", "kaya": "Jam & Marmalade",
    "butter": "Dairy", "mentega": "Dairy", "margarine": "Dairy",
    "cheese": "Dairy", "keju": "Dairy",
    "yogurt": "Yogurt",
    "egg": "Eggs", "telur": "Eggs",
    "cereal": "Cereal", "oat": "Cereal",
    "honey": "Honey", "madu": "Honey"
}

def get_db_engine():
    """Create SQLAlchemy engine."""
    return create_engine(DB_CONNECTION_STRING)

def load_json_file(filepath):
    """Load JSON data from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: File not found: {filepath}")
        return None

def get_penang_locations(locations_file, store_name_filter):
    """Filter locations for Penang region."""
    data = load_json_file(locations_file)
    if not data:
        return []
    
    penang_locations = []
    for loc in data:
        # Check if address or region indicates Penang
        # Common Penang indicators: "Pulau Pinang", "Penang", "George Town", "Butterworth", "Bukit Mertajam"
        address = loc.get('address', '').lower()
        region = loc.get('region_searched', '').lower()
        
        is_penang = (
            'pulau pinang' in address or 
            'penang' in address or 
            'george town' in address or 
            'bukit mertajam' in address or
            'seberang jaya' in address or
            'bayan lepas' in address or
            'simpang ampat' in address or
            region == 'penang'
        )
        
        # Also strictly ensure strict matching for store brand if needed, 
        # though files like mydin_locations.json are usually specific.
        # But jaya_grocer_locations.json might have others if generic scraper was used.
        # The file names suggests they contain locations for that brand.
        
        if is_penang:
            penang_locations.append(loc)
            
    print(f"Found {len(penang_locations)} Penang locations in {locations_file}")
    return penang_locations

def transform_to_gold_schema(df, location):
    """
    Transform product dataframe to match purchase_analytics_gold schema.
    Replicates products for a specific location.
    """
    # Create a copy to avoid modifying original
    gold_df = df.copy()
    
    # Generate UUIDs for new records
    gold_df['Id'] = [str(uuid.uuid4()) for _ in range(len(gold_df))]
    
    # Map fields
    # Generate UUID for ItemId since it's required (NOT NULL)
    gold_df['ItemId'] = [str(uuid.uuid4()) for _ in range(len(gold_df))]
    
    # ReceiptId/UserId might be nullable for external data. If not, this will fail next.
    gold_df['ReceiptId'] = None 
    gold_df['UserId'] = None
    
    # Core Product Data
    # Handle different column names from scrapers
    if 'item_name' in gold_df.columns:
        gold_df['ItemName'] = gold_df['item_name']
    elif 'name' in gold_df.columns:
        gold_df['ItemName'] = gold_df['name']

    # CLEANING STEP: Remove " - 1 UNIT" suffix
    # We use regex to replace case-insensitive " - 1 unit" at the end of string
    gold_df['ItemName'] = gold_df['ItemName'].str.replace(r'\s*-\s*1\s*UNIT$', '', case=False, regex=True)

        
    gold_df['CanonicalName'] = gold_df['ItemName'] # Ideally normalized later
    
    if 'unit_price' in gold_df.columns:
        gold_df['UnitPrice'] = pd.to_numeric(gold_df['unit_price'], errors='coerce').fillna(0)
    elif 'price' in gold_df.columns:
        gold_df['UnitPrice'] = pd.to_numeric(gold_df['price'], errors='coerce').fillna(0)
        
    gold_df['TotalPrice'] = gold_df['UnitPrice'] # Assuming quantity 1 unit logic for price comparison
    gold_df['Quantity'] = 1
    
    # Store Context from Location Object
    gold_df['StoreName'] = location.get('branch_name') or location.get('store_name')
    gold_df['StoreAddress'] = location.get('address')
    gold_df['StorePhoneNumber'] = location.get('phone')
    gold_df['Latitude'] = location.get('latitude')
    gold_df['Longitude'] = location.get('longitude')
    gold_df['LocationConfidence'] = 1.0 # High confidence as it is scraping
    
    # Category
    if 'category' in gold_df.columns:
        gold_df['Category'] = gold_df['category']
    else:
        gold_df['Category'] = None

    # Metadata
    gold_df['PurchaseDate'] = datetime.now() # Current timestamp for "market price as of now"
    gold_df['ReceiptType'] = 'Scraped'
    gold_df['Source'] = 'Scraper'  # Identify this as scraped data
    gold_df['TransactionId'] = None
    gold_df['PaymentMethod'] = None
    gold_df['ReceiptStatus'] = 'Verified'
    gold_df['IsCorrected'] = False
    gold_df['CorrectedAt'] = None
    gold_df['CreatedAt'] = datetime.now()
    
    # Select only columns present in target table
    target_columns = [
        'Id', 'ItemId', 'ReceiptId', 'UserId', 'ItemName', 'CanonicalName',
        'UnitPrice', 'TotalPrice', 'Quantity', 'PurchaseDate',
        'StoreName', 'StoreAddress', 'StorePhoneNumber', 
        'Latitude', 'Longitude', 'LocationConfidence', 'Category',
        'ReceiptType', 'TransactionId', 'PaymentMethod', 
        'ReceiptStatus', 'IsCorrected', 'CorrectedAt', 'CreatedAt',
        'Source'
    ]
    
    # Ensure all columns exist
    for col in target_columns:
        if col not in gold_df.columns:
            gold_df[col] = None
            
    return gold_df[target_columns]

def main():
    print("Starting data loading pipeline...")
    
    engine = get_db_engine()
    
    # 1. Load Jaya Grocer Data
    print("\n--- Processing Jaya Grocer ---")
    jg_products_data = load_json_file(JAYA_GROCER_PRODUCTS_FILE)
    if jg_products_data:
        # Handle structure: ensure we have a list of products
        jg_products = jg_products_data.get('products', []) if isinstance(jg_products_data, dict) else jg_products_data
        
        if jg_products:
            df_jg = pd.DataFrame(jg_products)
            
            # FILTERING JAYA GROCER
            original_count = len(df_jg)
            if 'category' in df_jg.columns:
                df_jg = df_jg[df_jg['category'].isin(GROCERY_CATEGORIES)]
            filtered_count = len(df_jg)
            print(f"Loaded {original_count} Jaya Grocer products. Filtered to {filtered_count} grocery items.")
            
            # Get locations
            jg_locations = get_penang_locations(JAYA_GROCER_LOCATIONS_FILE, 'Jaya Grocer')
            
            all_jg_gold = []
            for loc in jg_locations:
                print(f"Processing location: {loc.get('branch_name')}")
                df_gold = transform_to_gold_schema(df_jg, loc)
                all_jg_gold.append(df_gold)
            
            if all_jg_gold:
                final_jg_df = pd.concat(all_jg_gold)
                print(f"Inserting {len(final_jg_df)} records for Jaya Grocer...")
                final_jg_df.to_sql('purchase_analytics_gold', engine, if_exists='append', index=False)
                print("Done.")
        else:
            print("No Jaya Grocer products found.")
    else:
        print("Skipping Jaya Grocer (file not found/empty).")

    # 2. Load Mydin Data
    print("\n--- Processing Mydin ---")
    mydin_products_data = load_json_file(MYDIN_PRODUCTS_FILE)
    # Mydin scraper saves list directly usually
    if mydin_products_data:
        mydin_products = mydin_products_data
        
        if mydin_products:
            df_mydin = pd.DataFrame(mydin_products)
            
            # FILTERING MYDIN
            original_count = len(df_mydin)
            # Create a boolean mask for filtering
            def is_grocery(item_name):
                if not isinstance(item_name, str): return False
                name_lower = item_name.lower()
                return any(keyword in name_lower for keyword in GROCERY_KEYWORDS)
            
            # Assuming column is 'item_name' based on schema
            if 'item_name' in df_mydin.columns:
                 mask = df_mydin['item_name'].apply(is_grocery)
                 df_mydin = df_mydin[mask]
            
            # INFER CATEGORY FOR MYDIN
            def infer_category(item_name):
                if not isinstance(item_name, str): return None
                name_lower = item_name.lower()
                # Check keywords in mapping
                for keyword, category in KEYWORD_CATEGORY_MAP.items():
                    # Simple inclusion check. Could be improved with word boundary check.
                    if keyword in name_lower:
                        return category
                return "Uncategorized"

            if 'item_name' in df_mydin.columns:
                df_mydin['category'] = df_mydin['item_name'].apply(infer_category)
            
            filtered_count = len(df_mydin)
            print(f"Loaded {original_count} Mydin products. Filtered to {filtered_count} grocery items.")
            
            # Get locations
            mydin_locations = get_penang_locations(MYDIN_LOCATIONS_FILE, 'Mydin')
            
            all_mydin_gold = []
            for loc in mydin_locations:
                print(f"Processing location: {loc.get('branch_name')}")
                df_gold = transform_to_gold_schema(df_mydin, loc)
                all_mydin_gold.append(df_gold)
                
            if all_mydin_gold:
                final_mydin_df = pd.concat(all_mydin_gold)
                print(f"Inserting {len(final_mydin_df)} records for Mydin...")
                final_mydin_df.to_sql('purchase_analytics_gold', engine, if_exists='append', index=False)
                print("Done.")
        else:
            print("No Mydin products found.")
    else:
        print("Skipping Mydin (file not found/empty).")

    print("\nData loading complete!")

if __name__ == "__main__":
    main()
