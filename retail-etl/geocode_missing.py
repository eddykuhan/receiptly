import json
import requests
from urllib.parse import quote
import time

stores_to_geocode = [
    ("Lotus's Ipoh Bercham", "Taman Tasek Indra, Ipoh, Perak, Malaysia"),
    ("Lotus's Klang", "Bandar Bukit Tinggi, Klang, Selangor, Malaysia"),
    ("Lotus's Mart Duyong", "Ayer Molek, Melaka, Malaysia"),
    ("Lotus's Mergong", "Alor Setar, Kedah, Malaysia"),
    ("Lotus's Mutiara Rini", "Taman Mutiara Rini, Skudai, Johor, Malaysia"),
    ("Lotus's Penang E-Gate", "Bandar Jelutong, Penang, Malaysia"),
    ("Lotus's Seremban Jaya", "Seremban, Negeri Sembilan, Malaysia"),
    ("Lotus's Sg Dua", "Sg Dua, Penang, Malaysia"),
]

def geocode_address(address):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={quote(address)}&format=json&countrycodes=my"
        response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon']), data[0].get('display_name', '')
    except Exception as e:
        print(f"Error: {e}")
    return None, None, None

print("Searching for coordinates...")
for name, address in stores_to_geocode:
    lat, lng, display = geocode_address(address)
    if lat:
        print(f"✓ {name}: {lat:.6f}, {lng:.6f}")
        print(f"  {display}")
    else:
        print(f"✗ {name}: Not found")
    time.sleep(0.5)  # Rate limit