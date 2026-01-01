#!/usr/bin/env python3
"""
Scrape Lotus's Malaysia store locations from corporate API.
Includes geocoding to get coordinates for each store.
"""
import requests
import json
import time
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# Google Maps Geocoding API (optional - set your API key)
GOOGLE_MAPS_API_KEY = ""  # Add your API key here if available

def get_csrf_token() -> str:
    """Extract CSRF token from the store locator page."""
    print("Fetching CSRF token...")
    url = "https://corp.lotuss.com.my/stores/store-locator"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Token is in the POST request, we need to extract it from the page
    # Looking at the network request, the token might be in a meta tag or script
    # For now, we'll try to get it from the nocache endpoint
    session = requests.Session()
    session.get(url)
    
    # Make the nocache request to get a fresh token
    nocache_response = session.post("https://corp.lotuss.com.my/!/nocache")
    
    # Try to extract token from cookies or response
    # The token appears to be in XSRF-TOKEN cookie
    token = session.cookies.get('XSRF-TOKEN')
    if token:
        # Decode URL-encoded cookie
        import urllib.parse
        token = urllib.parse.unquote(token)
        # Extract the value from the JSON structure
        try:
            token_data = json.loads(token)
            return token_data.get('value', token)
        except:
            pass
    
    print("Warning: Could not extract CSRF token, trying without it...")
    return ""

def fetch_stores_page(page: int = 1, limit: int = 100, session: requests.Session = None) -> Dict:
    """Fetch a single page of stores from the API."""
    url = f"https://corp.lotuss.com.my/entries/stores"
    
    if not session:
        session = requests.Session()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Referer': 'https://corp.lotuss.com.my/stores/store-locator',
        'Origin': 'https://corp.lotuss.com.my',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin'
    }
    
    params = {
        'sort': 'title|asc',
        'limit': limit,
        'page': page
    }
    
    # Get CSRF token from cookie
    token = session.cookies.get('XSRF-TOKEN', '')
    if token:
        # Decode the cookie value
        import urllib.parse
        token = urllib.parse.unquote(token)
        try:
            token_data = json.loads(token)
            token = token_data.get('value', '')
        except:
            pass
    
    try:
        data = {'_token': token}
        response = session.post(url, params=params, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
        return {}

def geocode_address(address: str) -> Optional[Dict[str, float]]:
    """
    Geocode an address to get latitude and longitude.
    Uses Google Maps Geocoding API if key is available, otherwise returns None.
    """
    if not GOOGLE_MAPS_API_KEY:
        return None
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'address': address,
        'key': GOOGLE_MAPS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if data['status'] == 'OK' and len(data['results']) > 0:
            location = data['results'][0]['geometry']['location']
            return {
                'latitude': location['lat'],
                'longitude': location['lng']
            }
    except Exception as e:
        print(f"Geocoding error for '{address}': {e}")
    
    return None

def transform_store_data(store: Dict, region: str = "Malaysia") -> Dict:
    """Transform API store data to match the existing JSON structure."""
    # Extract phone (use first contact if multiple)
    phone = store.get('contact', [''])[0] if store.get('contact') else ''
    
    # Get coordinates if geocoding is enabled
    coords = None
    if GOOGLE_MAPS_API_KEY:
        print(f"  Geocoding: {store['title']}...")
        coords = geocode_address(store['address'])
        time.sleep(0.1)  # Rate limiting
    
    transformed = {
        'store_name': "Lotus's Malaysia",
        'branch_name': store['title'],
        'address': store['address'],
        'latitude': coords['latitude'] if coords else None,
        'longitude': coords['longitude'] if coords else None,
        'phone': phone,
        'rating': None,  # Not available in API
        'total_ratings': None,  # Not available in API
        'region_searched': store['state']['label'] if store.get('state') else region,
        'state_code': store.get('state_code'),
        'facilities': [f['title'] for f in store.get('facilities', [])]
    }
    
    return transformed

def scrape_all_stores() -> List[Dict]:
    """Scrape all Lotus's stores from the API."""
    all_stores = []
    
    # Create session and load cookies
    session = requests.Session()
    
    # Visit the page to get cookies
    print("Loading store locator page to get session cookies...")
    session.get("https://corp.lotuss.com.my/stores/store-locator")
    
    # Make nocache request to refresh token
    session.post("https://corp.lotuss.com.my/!/nocache")
    
    # Fetch first page to get total pages
    print("Fetching page 1...")
    first_page = fetch_stores_page(page=1, limit=100, session=session)
    
    if not first_page or 'data' not in first_page:
        print("Error: Could not fetch store data")
        return []
    
    # Process first page
    total_pages = first_page.get('last_page', 1)
    total_stores = first_page.get('total', 0)
    
    print(f"Found {total_stores} stores across {total_pages} pages")
    
    for store in first_page['data']:
        print(f"Processing: {store['title']}")
        transformed = transform_store_data(store)
        all_stores.append(transformed)
    
    # Fetch remaining pages
    for page in range(2, total_pages + 1):
        print(f"\nFetching page {page}/{total_pages}...")
        page_data = fetch_stores_page(page=page, limit=100, session=session)
        
        if page_data and 'data' in page_data:
            for store in page_data['data']:
                print(f"Processing: {store['title']}")
                transformed = transform_store_data(store)
                all_stores.append(transformed)
        
        time.sleep(0.5)  # Rate limiting between pages
    
    return all_stores

def main():
    """Main function to scrape and save store data."""
    print("=" * 60)
    print("Lotus's Malaysia Store Scraper")
    print("=" * 60)
    
    if not GOOGLE_MAPS_API_KEY:
        print("\nWarning: No Google Maps API key set.")
        print("Coordinates will be set to None.")
        print("To add coordinates, set GOOGLE_MAPS_API_KEY in the script.\n")
    
    # Scrape stores
    stores = scrape_all_stores()
    
    if not stores:
        print("\nError: No stores scraped")
        return
    
    print(f"\n✓ Successfully scraped {len(stores)} stores")
    
    # Save to JSON file
    output_file = "data/lotuss_malaysia_locations_new.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(stores, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved to: {output_file}")
    
    # Show summary
    print("\nSummary by State:")
    states = {}
    for store in stores:
        region = store.get('region_searched', 'Unknown')
        states[region] = states.get(region, 0) + 1
    
    for state, count in sorted(states.items()):
        print(f"  {state}: {count} stores")
    
    print("\nNote: To replace the existing file, run:")
    print(f"  mv {output_file} data/lotuss_malaysia_locations.json")

if __name__ == "__main__":
    main()
