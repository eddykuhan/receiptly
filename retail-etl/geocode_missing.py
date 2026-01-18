import json
import requests
from urllib.parse import quote
import time

stores_to_geocode = [
    ("AEON MaxValu Prime Evo Bangi", "Kompleks Evo, Jalan Pusat Bandar 2, 43650 Bandar Baru Bangi, Malaysia")
]

def geocode_address(address):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={quote(address)}&format=json&countrycodes=my"
        response = requests.get(url, timeout=5, headers={'User-Agent': 'Receiptly-Geocoding/1.0 (https://github.com/kuhan/receiptly)'})
        response.raise_for_status()  # Check for HTTP errors
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon']), data[0].get('display_name', '')
    except requests.RequestException as e:
        print(f"Request error: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Response content: {response.text[:500]}")  # Show first 500 chars of response
    except (KeyError, IndexError, ValueError) as e:
        print(f"Data parsing error: {e}")
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