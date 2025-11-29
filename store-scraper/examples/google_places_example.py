"""
Google Places API Integration Example

This script shows how to use Google Places API to get accurate store locations
with GPS coordinates. This is more reliable than web scraping.
"""

import os
import json
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class StoreLocation:
    """Store location data structure"""
    store_name: str
    branch_name: str
    address: str
    city: str
    state: str
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: str = ""
    rating: Optional[float] = None
    total_ratings: Optional[int] = None


class GooglePlacesAPI:
    """Google Places API client for store location data"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/place"
    
    def search_stores(
        self, 
        store_name: str, 
        location: str = "Malaysia",
        max_results: int = 60
    ) -> List[StoreLocation]:
        """
        Search for store locations using Google Places API
        
        Args:
            store_name: Name of the store chain (e.g., "Jaya Grocer")
            location: Geographic area to search (default: "Malaysia")
            max_results: Maximum number of results to return
            
        Returns:
            List of StoreLocation objects
        """
        locations = []
        next_page_token = None
        
        while len(locations) < max_results:
            # Text search endpoint
            search_url = f"{self.base_url}/textsearch/json"
            params = {
                'query': f"{store_name} {location}",
                'key': self.api_key
            }
            
            if next_page_token:
                params['pagetoken'] = next_page_token
            
            try:
                response = requests.get(search_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data.get('status') != 'OK':
                    print(f"API Error: {data.get('status')} - {data.get('error_message', '')}")
                    break
                
                # Process results
                for place in data.get('results', []):
                    location = self._parse_place(place, store_name)
                    locations.append(location)
                    print(f"  ✓ {location.branch_name} - {location.city}")
                
                # Check for more pages
                next_page_token = data.get('next_page_token')
                if not next_page_token or len(locations) >= max_results:
                    break
                
                # Google requires a short delay before using next_page_token
                import time
                time.sleep(2)
                
            except Exception as e:
                print(f"Error searching places: {e}")
                break
        
        return locations[:max_results]
    
    def get_place_details(self, place_id: str) -> Dict:
        """Get detailed information about a specific place"""
        details_url = f"{self.base_url}/details/json"
        params = {
            'place_id': place_id,
            'fields': 'name,formatted_address,formatted_phone_number,geometry,rating,user_ratings_total',
            'key': self.api_key
        }
        
        try:
            response = requests.get(details_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK':
                return data.get('result', {})
        except Exception as e:
            print(f"Error getting place details: {e}")
        
        return {}
    
    def _parse_place(self, place: Dict, store_name: str) -> StoreLocation:
        """Parse Google Places API result into StoreLocation"""
        address = place.get('formatted_address', '')
        geometry = place.get('geometry', {})
        location_data = geometry.get('location', {})
        
        # Parse address components
        city, state, postal_code = self._parse_address_components(
            place.get('address_components', [])
        )
        
        return StoreLocation(
            store_name=store_name,
            branch_name=place.get('name', ''),
            address=address,
            city=city,
            state=state,
            postal_code=postal_code,
            latitude=location_data.get('lat'),
            longitude=location_data.get('lng'),
            place_id=place.get('place_id', ''),
            rating=place.get('rating'),
            total_ratings=place.get('user_ratings_total')
        )
    
    def _parse_address_components(self, components: List[Dict]) -> tuple:
        """Parse address components from Google Places API"""
        city = "Unknown"
        state = "Unknown"
        postal_code = None
        
        for component in components:
            types = component.get('types', [])
            
            if 'locality' in types:
                city = component.get('long_name', city)
            elif 'administrative_area_level_1' in types:
                state = component.get('long_name', state)
            elif 'postal_code' in types:
                postal_code = component.get('long_name')
        
        return city, state, postal_code


def save_to_json(locations: List[StoreLocation], filename: str):
    """Save locations to JSON file"""
    data = [asdict(loc) for loc in locations]
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved {len(locations)} locations to {filename}")


def main():
    """Main function to fetch store locations using Google Places API"""
    
    # Get API key from environment variable or hardcode it
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    
    if not api_key:
        print("❌ Error: GOOGLE_PLACES_API_KEY environment variable not set")
        print("\nTo use this script:")
        print("1. Get an API key from https://console.cloud.google.com/")
        print("2. Enable the Places API")
        print("3. Set the environment variable:")
        print("   export GOOGLE_PLACES_API_KEY='your-api-key-here'")
        print("\nOr hardcode it in this script (not recommended for production)")
        return
    
    api = GooglePlacesAPI(api_key)
    
    # List of stores to scrape
    stores = [
        "Jaya Grocer",
        "Mydin",
        "Lotus's",
        "AEON",
        "Village Grocer"
    ]
    
    print("🔍 Fetching Store Locations from Google Places API")
    print("=" * 60)
    
    for store_name in stores:
        print(f"\n📍 Searching for {store_name} locations...")
        locations = api.search_stores(store_name, "Malaysia", max_results=50)
        
        if locations:
            filename = f"data/{store_name.lower().replace(' ', '_')}_locations.json"
            save_to_json(locations, filename)
            
            # Print summary
            print(f"\nSummary for {store_name}:")
            print(f"  Total locations: {len(locations)}")
            
            # Count by state
            states = {}
            for loc in locations:
                states[loc.state] = states.get(loc.state, 0) + 1
            
            print("  Distribution by state:")
            for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True):
                print(f"    {state}: {count}")
        else:
            print(f"  ⚠️  No locations found for {store_name}")
    
    print("\n✅ All done!")


if __name__ == "__main__":
    main()
