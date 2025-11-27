"""
Quick Start: Get store locations using Google Places API

This is the recommended approach - much more reliable than web scraping.
"""

import os
import json
import requests
from typing import List, Dict


def get_store_locations(store_name: str, api_key: str, location: str = "Malaysia") -> List[Dict]:
    """
    Fetch store locations using Google Places API (New version)
    
    Args:
        store_name: Name of the store (e.g., "Jaya Grocer")
        api_key: Your Google Places API key
        location: Geographic area (default: "Malaysia")
    
    Returns:
        List of store locations with address, coordinates, etc.
    """
    url = "https://places.googleapis.com/v1/places:searchText"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.nationalPhoneNumber,places.rating,places.userRatingCount"
    }
    
    body = {
        "textQuery": f"{store_name} {location}",
        "maxResultCount": 20  # Max 20 per request
    }
    
    try:
        response = requests.post(url, json=body, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        locations = []
        for place in data.get('places', []):
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
            locations.append(location_data)
        
        return locations
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        return []


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
        "Village Grocer Malaysia"
    ]
    
    for store_name in stores:
        print(f"\n📍 Fetching {store_name} locations...")
        locations = get_store_locations(store_name, api_key)
        
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
