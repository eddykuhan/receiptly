"""
Quick Start: Get store locations using Google Places API

This is the recommended approach - much more reliable than web scraping.
"""

import os
import json
import requests
import time
from typing import List, Dict


def get_store_locations(store_name: str, api_key: str, location: str = "Malaysia", max_results: int = 100) -> List[Dict]:
    """
    Fetch store locations using Google Places API (New version) with pagination
    
    Args:
        store_name: Name of the store (e.g., "Jaya Grocer")
        api_key: Your Google Places API key
        location: Geographic area (default: "Malaysia")
        max_results: Maximum number of results to fetch (default: 100)
    
    Returns:
        List of store locations with address, coordinates, etc.
    """
    url = "https://places.googleapis.com/v1/places:searchText"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.nationalPhoneNumber,places.rating,places.userRatingCount,nextPageToken"
    }
    
    all_locations = []
    next_page_token = None
    page_count = 0
    
    while len(all_locations) < max_results:
        body = {
            "textQuery": f"{store_name} {location}",
            "maxResultCount": 20  # Max 20 per request
        }
        
        # Add page token for subsequent requests
        if next_page_token:
            body["pageToken"] = next_page_token
        
        try:
            response = requests.post(url, json=body, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            places = data.get('places', [])
            if not places:
                break
            
            # Process places
            for place in places:
                location_data = {
                    'store_name': store_name,
                    'branch_name': place.get('displayName', {}).get('text', ''),
                    'address': place.get('formattedAddress', ''),
                    'latitude': place.get('location', {}).get('latitude'),
                    'longitude': place.get('location', {}).get('longitude'),
                    'phone': place.get('nationalPhoneNumber', ''),
                    'rating': place.get('rating'),
                    'total_ratings': place.get('userRatingCount', 0)
                }
                all_locations.append(location_data)
            
            page_count += 1
            print(f"   📄 Page {page_count}: {len(places)} locations (total: {len(all_locations)})")
            
            # Check for next page
            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                print(f"   ℹ️  No more pages available")
                break
            
            # Google requires a short delay between paginated requests
            time.sleep(2)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching data: {e}")
            break
    
    return all_locations[:max_results]


def save_to_json(data: List[Dict], filename: str):
    """Save data to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(data)} locations to {filename}")


def main():
    """Main function"""
    print("🔍 Google Places Store Locator")
    print("=" * 60)
    
    # Get API key from environment variable
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    
    if not api_key:
        print("\n❌ GOOGLE_PLACES_API_KEY not set!")
        print("\n📝 To get started:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a project and enable 'Places API (New)'")
        print("3. Create credentials (API Key)")
        print("4. Set the environment variable:")
        print("   export GOOGLE_PLACES_API_KEY='your-api-key-here'")
        print("\n💡 Or edit this file and add your key directly (line 80)")
        return
    
    # List of stores to fetch
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
        "Guardian Malaysia"
    ]
    
    for store_name in stores:
        print(f"\n📍 Fetching {store_name} locations...")
        locations = get_store_locations(store_name, api_key, max_results=200)
        
        if locations:
            # Save to file
            filename = f"data/{store_name.lower().replace(' ', '_').replace('\'', '')}_locations.json"
            save_to_json(locations, filename)
            
            # Print sample
            print(f"\n   Sample locations:")
            for loc in locations[:3]:
                print(f"   • {loc['branch_name']}")
                print(f"     {loc['address'][:60]}...")
        else:
            print(f"   ⚠️  No locations found")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    # OPTION: Hardcode your API key here (not recommended for production)
    # os.environ['GOOGLE_PLACES_API_KEY'] = 'your-key-here'
    
    main()
