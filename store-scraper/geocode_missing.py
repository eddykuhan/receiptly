import json
import requests
from urllib.parse import quote

# Stores that need geocoding
missing_coords = {
    "Lotus's Ipoh Bercham": "No. 2, Laluan Tasek Timur 6, Taman Tasek Indra, Off Jalan Kg Bercham, 34100 Ipoh, Perak",
    "Lotus's Klang": "No. 3, Jln Batu Nilam 6/KS6, Bandar Bukit Tinggi, 41200 Klang, Selangor",
    "Lotus's Mart Duyong": "Jalan Taman Iks Duyong, Taman Desa Duyong, 75460 Ayer Molek, Melaka",
    "Lotus's Mergong": "No. 1, Lebuhraya Sultanah Bahiyah, 05150 Alor Setar, Kedah",
    "Lotus's Mutiara Rini": "No.1, Jalan Persiaran Jasa 1, Taman Mutiara Rini, 81380 Skudai, Johor Bahru",
    "Lotus's Penang E-Gate": "No.1, Lebuh Tengku Kudin 1, Bandar Jelutong, 11700 Pulau Pinang",
}

def geocode_address(address):
    """Use Nominatim (OpenStreetMap) for free geocoding"""
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={quote(address)}&format=json&countrycodes=my"
        response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"Error geocoding: {e}")
    return None, None

# Load existing data
with open('data/lotuss_malaysia_locations.json', 'r') as f:
    stores = json.load(f)

updated = 0
print("Geocoding missing coordinates...")
for store in stores:
    name = store['branch_name']
    if name in missing_coords and (store['latitude'] is None or store['longitude'] is None):
        address = store['address']
        print(f"  Geocoding: {name}")
        lat, lng = geocode_address(address)
        if lat and lng:
            store['latitude'] = lat
            store['longitude'] = lng
            print(f"    ✓ Found: {lat:.6f}, {lng:.6f}")
            updated += 1
        else:
            print(f"    ✗ Not found")

# Save updated data
with open('data/lotuss_malaysia_locations.json', 'w') as f:
    json.dump(stores, f, indent=2, ensure_ascii=False)

print(f"\nUpdated {updated} stores")
