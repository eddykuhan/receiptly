
import json
import os
import psycopg2
from psycopg2.extras import execute_values
from config.settings import DB_CONFIG

# Paths to data files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JG_FILE = os.path.join(BASE_DIR, 'store-scraper', 'data', 'jaya_grocer_locations.json')
MYDIN_FILE = os.path.join(BASE_DIR, 'store-scraper', 'data', 'mydin_locations.json')
LOTUSS_FILE = os.path.join(BASE_DIR, 'store-scraper', 'data', 'lotuss_malaysia_locations.json')
AEON_FILE = os.path.join(BASE_DIR, 'store-scraper', 'data', 'aeon_official_stores.json')
VILLAGE_GROCER_FILE = os.path.join(BASE_DIR, 'store-scraper', 'data', 'village_grocer_actual_locations.json')

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def load_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def determine_jg_zone(address):
    address_lower = address.lower()
    
    if 'pulau pinang' in address_lower or 'penang' in address_lower:
        return 'JG_PENANG'
    if 'cyberjaya' in address_lower:
        return 'JG_CYBERJAYA'
    if 'kuala lumpur' in address_lower:
        return 'JG_KL'
    if 'selangor' in address_lower:
        return 'JG_KL' # Default Klang Valley to KL zone
    if 'johor' in address_lower:
        return 'JG_JOHOR'
    if 'perak' in address_lower:
        return 'JG_IPOH'
    if 'negeri sembilan' in address_lower:
        return 'JG_SEREMBAN'
        
    return 'JG_KL' # Fallback

def determine_village_grocer_zone(region_searched):
    """Determine Village Grocer pricing zone based on region searched."""
    region_lower = region_searched.lower() if region_searched else ''
    
    # # Location-specific zones for major hubs
    # if region_lower in ['mont kiara', 'kl']:
    #     return 'VILLAGE_GROCER_MONT_KIARA_MY'  # Flagship Mont Kiara location
    
    # Default to main catalog pricing zone for other locations
    # Physical stores use same pricing as main online catalog
    return 'VILLAGE_GROCER_MY'

def seed_stores():
    print("Connecting to database...")
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1. Truncate table
        print("Truncating stores table...")
        cur.execute("TRUNCATE TABLE stores RESTART IDENTITY CASCADE;")
        
        stores_data = []
        
        # 2. Process Jaya Grocer
        if os.path.exists(JG_FILE):
            print(f"Processing Jaya Grocer data from {JG_FILE}...")
            jg_locations = load_json(JG_FILE)
            for loc in jg_locations:
                stores_data.append((
                    loc.get('branch_name', loc.get('store_name')), # Name
                    'Jaya Grocer',   # RetailChain
                    determine_jg_zone(loc.get('address', '')), # PricingZoneId
                    loc.get('address'), # Address
                    loc.get('latitude'), # Latitude
                    loc.get('longitude') # Longitude
                ))
        else:
            print(f"Warning: File not found: {JG_FILE}")

        # 3. Process Mydin
        if os.path.exists(MYDIN_FILE):
             print(f"Processing Mydin data from {MYDIN_FILE}...")
             mydin_locations = load_json(MYDIN_FILE)
             for loc in mydin_locations:
                 stores_data.append((
                    loc.get('branch_name', loc.get('store_name')), # Name
                    'Mydin',   # RetailChain
                    'MYDIN_NATIONAL', # PricingZoneId (National Pricing)
                    loc.get('address'), # Address
                    loc.get('latitude'), # Latitude
                    loc.get('longitude') # Longitude
                 ))
        else:
            print(f"Warning: File not found: {MYDIN_FILE}")

        # 4. Process Lotus's
        if os.path.exists(LOTUSS_FILE):
             print(f"Processing Lotus's data from {LOTUSS_FILE}...")
             lotuss_locations = load_json(LOTUSS_FILE)
             for loc in lotuss_locations:
                 stores_data.append((
                    loc.get('branch_name', loc.get('store_name')), # Name
                    "Lotus's",   # RetailChain
                    'LOTUSS_NATIONAL', # PricingZoneId (National Pricing)
                    loc.get('address'), # Address
                    loc.get('latitude'), # Latitude
                    loc.get('longitude') # Longitude
                 ))
        else:
            print(f"Warning: File not found: {LOTUSS_FILE}")

        # 5. Process AEON
        if os.path.exists(AEON_FILE):
             print(f"Processing AEON data from {AEON_FILE}...")
             aeon_locations = load_json(AEON_FILE)
             for loc in aeon_locations:
                 stores_data.append((
                    loc.get('branch_name', loc.get('store_name')), # Name
                    "AEON",   # RetailChain
                    'AEON_NATIONAL', # PricingZoneId (National Pricing)
                    loc.get('address'), # Address
                    loc.get('latitude'), # Latitude
                    loc.get('longitude') # Longitude
                 ))
        else:
            print(f"Warning: File not found: {AEON_FILE}")

        # 6. Process Village Grocer
        if os.path.exists(VILLAGE_GROCER_FILE):
             print(f"Processing Village Grocer data from {VILLAGE_GROCER_FILE}...")
             vg_locations = load_json(VILLAGE_GROCER_FILE)
             for loc in vg_locations:
                 stores_data.append((
                    loc.get('branch_name', loc.get('store_name')), # Name
                    'Village Grocer',   # RetailChain
                    determine_village_grocer_zone(loc.get('region_searched', '')), # PricingZoneId
                    loc.get('address'), # Address
                    loc.get('latitude'), # Latitude
                    loc.get('longitude') # Longitude
                 ))
        else:
            print(f"Warning: File not found: {VILLAGE_GROCER_FILE}")
            
        # 7. Bulk Insert
        if stores_data:
            print(f"Inserting {len(stores_data)} stores...")
            insert_query = """
                INSERT INTO stores ("Id", "Name", "RetailChain", "PricingZoneId", "Address", "Latitude", "Longitude")
                VALUES %s
            """
            
            # Add UUID to each record
            import uuid
            final_data = []
            for record in stores_data:
                final_data.append((
                    str(uuid.uuid4()), # Generated UUID
                    *record
                ))
                
            execute_values(cur, insert_query, final_data)
            conn.commit()
            print("Seeding complete!")
        else:
            print("No data to insert.")

    except Exception as e:
        print(f"Error seeding stores: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    seed_stores()
