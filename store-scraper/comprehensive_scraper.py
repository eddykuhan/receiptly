"""
Comprehensive Store Location Scraper

Fetches store locations by iterating through all Malaysian states and major cities
to overcome Google Places API result limits (max 60 per query).
"""

import os
import json
import requests
import time
from typing import List, Dict, Set


def get_places_by_region(store_name: str, region: str, api_key: str) -> List[Dict]:
    """Fetch locations for a specific region"""
    url = "https://places.googleapis.com/v1/places:searchText"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.nationalPhoneNumber,places.rating,places.userRatingCount,nextPageToken"
    }
    
    all_locations = []
    next_page_token = None
    
    # Max 3 pages (60 results) per region is usually enough for a specific city/state
    # If a state has >60 stores, we rely on city-level searches to fill gaps
    for _ in range(3):
        body = {
            "textQuery": f"{store_name} {region}",
            "maxResultCount": 20
        }
        
        if next_page_token:
            body["pageToken"] = next_page_token
        
        try:
            response = requests.post(url, json=body, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            places = data.get('places', [])
            if not places:
                break
                
            for place in places:
                # Create a unique ID based on coordinates to avoid duplicates
                lat = place.get('location', {}).get('latitude')
                lng = place.get('location', {}).get('longitude')
                
                location_data = {
                    'store_name': store_name,
                    'branch_name': place.get('displayName', {}).get('text', ''),
                    'address': place.get('formattedAddress', ''),
                    'latitude': lat,
                    'longitude': lng,
                    'phone': place.get('nationalPhoneNumber', ''),
                    'rating': place.get('rating'),
                    'total_ratings': place.get('userRatingCount', 0),
                    'region_searched': region
                }
                all_locations.append(location_data)
            
            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                break
                
            time.sleep(2)  # Delay for pagination
            
        except Exception as e:
            print(f"    ❌ Error fetching {region}: {e}")
            break
            
    return all_locations


def get_all_store_locations(store_name: str, api_key: str) -> List[Dict]:
    """Fetch locations iterating through all regions"""
    
    # List of regions to search to ensure full coverage
    regions = [
        # States
        "Kuala Lumpur", "Selangor", "Penang", "Johor", "Perak", 
        "Melaka", "Negeri Sembilan", "Pahang", "Kedah", "Kelantan", 
        "Terengganu", "Sabah", "Sarawak", "Perlis", "Putrajaya", "Labuan",
        
        # Major Cities (to catch density limits)
        "Petaling Jaya", "Shah Alam", "Subang Jaya", "Klang", "Puchong",
        "Johor Bahru", "Ipoh", "George Town", "Kota Kinabalu", "Kuching",
        "Seremban", "Kuantan", "Alor Setar", "Kota Bharu", "Miri",
        "Sandakan", "Sibu", "Batu Pahat", "Sungai Petani", "Taiping"
    ]
    
    all_unique_locations = {}  # Key by coordinate string to deduplicate
    
    print(f"\n🔍 Comprehensive search for: {store_name}")
    print(f"   Searching {len(regions)} regions...")
    
    total_found = 0
    
    for i, region in enumerate(regions, 1):
        locations = get_places_by_region(store_name, region, api_key)
        
        new_count = 0
        for loc in locations:
            # Create unique key from coordinates (rounded to 4 decimals ~11m precision)
            if loc['latitude'] and loc['longitude']:
                key = f"{round(loc['latitude'], 4)},{round(loc['longitude'], 4)}"
                if key not in all_unique_locations:
                    all_unique_locations[key] = loc
                    new_count += 1
        
        total_found = len(all_unique_locations)
        print(f"   [{i}/{len(regions)}] {region}... {len(locations)} found, {new_count} new (total: {total_found})")
        
        # Small delay to be nice to API
        time.sleep(1)
        
    return list(all_unique_locations.values())


def save_to_json(data: List[Dict], filename: str):
    """Save data to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(data)} locations to {filename}")


def main():
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("❌ GOOGLE_PLACES_API_KEY not set")
        return
        
    # Stores that need comprehensive scraping (high density)
    stores = [
        "Jaya Grocer",
        "Mydin",
        "Lotus's Malaysia",
        "AEON Malaysia",
        "Village Grocer Malaysia",
        "99 Speedmart",
        "Giant Hypermarket",
       "7-Eleven Malaysia",
        "FamilyMart Malaysia",
        "KK Super Mart",
        "Watsons Malaysia",
        "Guardian Malaysia",
        "Mr DIY",
        "Econsave"
    ]
    
    print("🏪 Comprehensive Store Location Scraper")
    print("=" * 70)
    
    for store_name in stores:
        locations = get_all_store_locations(store_name, api_key)
        
        if locations:
            clean_name = store_name.lower().replace(' ', '_').replace("'", "")
            filename = f"data/{clean_name}_locations.json"
            save_to_json(locations, filename)
        else:
            print(f"⚠️ No locations found for {store_name}")

if __name__ == "__main__":
    main()
