"""
Fetch 99 Speedmart locations for Penang and Kuala Lumpur

Focused extraction with detailed sub-region searches to maximize coverage.
Google Places API returns max ~60 results per query, so we search multiple specific areas.
"""

import os
import json
import requests
import time
from typing import List, Dict, Set


def get_store_locations_by_region(store_name: str, api_key: str, region: str, max_results: int = 60) -> List[Dict]:
    """
    Fetch store locations for a specific region using Google Places API with pagination
    
    Args:
        store_name: Name of the store (e.g., "99 Speedmart")
        api_key: Your Google Places API key
        region: Specific region/state in Malaysia
        max_results: Maximum results per region (default: 60)
    
    Returns:
        List of store locations
    """
    url = "https://places.googleapis.com/v1/places:searchText"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.nationalPhoneNumber,places.rating,places.userRatingCount,places.id,nextPageToken"
    }
    
    all_locations = []
    seen_ids = set()  # Prevent duplicates
    next_page_token = None
    page_count = 0
    
    # Paginate through results
    while len(all_locations) < max_results:
        body = {
            "textQuery": f"{store_name} {region}",
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
            
            for place in places:
                place_id = place.get('id', '')
                
                # Skip duplicates
                if place_id in seen_ids:
                    continue
                seen_ids.add(place_id)
                
                location_data = {
                    'store_name': store_name,
                    'branch_name': place.get('displayName', {}).get('text', ''),
                    'address': place.get('formattedAddress', ''),
                    'latitude': place.get('location', {}).get('latitude'),
                    'longitude': place.get('location', {}).get('longitude'),
                    'phone': place.get('nationalPhoneNumber', ''),
                    'rating': place.get('rating'),
                    'total_ratings': place.get('userRatingCount', 0),
                    'place_id': place_id
                }
                all_locations.append(location_data)
            
            page_count += 1
            
            # Check for next page
            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                break
            
            # Rate limiting between pages
            time.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ Error fetching {region} (page {page_count + 1}): {str(e)}")
            break
    
    print(f"   {region:20s}: {len(all_locations):3d} locations ({page_count} pages)")
    
    # Rate limiting between regions
    time.sleep(0.3)
    
    return all_locations


def deduplicate_locations(locations: List[Dict]) -> List[Dict]:
    """Remove duplicate locations based on place_id and address"""
    seen = set()
    unique_locations = []
    
    for loc in locations:
        # Create a unique key from place_id or address
        key = loc.get('place_id') or loc.get('address', '')
        
        if key and key not in seen:
            seen.add(key)
            unique_locations.append(loc)
    
    return unique_locations


def main():
    print("🔍 99 Speedmart Location Fetcher - Penang & Kuala Lumpur")
    print("=" * 70)
    
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    
    if not api_key:
        print("\n❌ GOOGLE_PLACES_API_KEY not set!")
        print("   export GOOGLE_PLACES_API_KEY='your-api-key-here'")
        return
    
    store_name = "99 Speedmart"
    
    # Focused search on Penang and Kuala Lumpur with sub-regions
    # Multiple specific areas help overcome the ~60 result limit per query
    regions = [
        # === PENANG ===
        "Penang Malaysia",
        "George Town Penang",
        "Butterworth Penang",
        "Bukit Mertajam Penang",
        "Bayan Lepas Penang",
        "Jelutong Penang",
        "Pulau Tikus Penang",
        "Tanjung Tokong Penang",
        "Bayan Baru Penang",
        "Prai Penang",
        "Perai Penang",
        "Seberang Perai Penang",
        "Nibong Tebal Penang",
        "Kepala Batas Penang",
        "Tasek Gelugor Penang",
        "Permatang Pauh Penang",
        "Bukit Jambul Penang",
        "Sungai Ara Penang",
        "Relau Penang",
        "Balik Pulau Penang",
        
        # === KUALA LUMPUR ===
        "Kuala Lumpur Malaysia",
        "Bukit Bintang Kuala Lumpur",
        "Chow Kit Kuala Lumpur",
        "KLCC Kuala Lumpur",
        "Bangsar Kuala Lumpur",
        "Mont Kiara Kuala Lumpur",
        "Kepong Kuala Lumpur",
        "Setapak Kuala Lumpur",
        "Wangsa Maju Kuala Lumpur",
        "Segambut Kuala Lumpur",
        "Sentul Kuala Lumpur",
        "Titiwangsa Kuala Lumpur",
        "Brickfields Kuala Lumpur",
        "Sri Petaling Kuala Lumpur",
        "Bukit Jalil Kuala Lumpur",
        "Seputeh Kuala Lumpur",
        "Lembah Pantai Kuala Lumpur",
        "Damansara Kuala Lumpur",
        "Desa Petaling Kuala Lumpur",
        "Cheras Kuala Lumpur",
    ]
    
    print(f"\n📍 Fetching {store_name} from {len(regions)} regions...")
    print("-" * 70)
    
    all_locations = []
    
    for region in regions:
        locations = get_store_locations_by_region(store_name, api_key, region)
        all_locations.extend(locations)
    
    print("\n" + "=" * 70)
    print(f"📊 Results before deduplication: {len(all_locations)} locations")
    
    # Remove duplicates
    unique_locations = deduplicate_locations(all_locations)
    print(f"📊 Results after deduplication:  {len(unique_locations)} locations")
    
    if unique_locations:
        # Separate locations by region
        penang_locations = [loc for loc in unique_locations if 'Penang' in loc.get('address', '') or 'Pulau Pinang' in loc.get('address', '')]
        kl_locations = [loc for loc in unique_locations if 'Kuala Lumpur' in loc.get('address', '')]
        
        # Save combined file
        filename = "data/99_speedmart_penang_kl.json"
        os.makedirs('data', exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(unique_locations, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Saved to: {filename}")
        
        # Detailed statistics
        print("\n📊 Results by region:")
        print(f"   Penang:         {len(penang_locations):3d} locations")
        print(f"   Kuala Lumpur:   {len(kl_locations):3d} locations")
        print(f"   Other:          {len(unique_locations) - len(penang_locations) - len(kl_locations):3d} locations")
        
        # Save separate files for each region
        if penang_locations:
            with open('data/99_speedmart_penang.json', 'w', encoding='utf-8') as f:
                json.dump(penang_locations, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Penang locations saved to: data/99_speedmart_penang.json")
        
        if kl_locations:
            with open('data/99_speedmart_kuala_lumpur.json', 'w', encoding='utf-8') as f:
                json.dump(kl_locations, f, ensure_ascii=False, indent=2)
            print(f"💾 KL locations saved to: data/99_speedmart_kuala_lumpur.json")
        
        print(f"\n💡 To use in OCR service:")
        print(f"   cp {filename} data/99_speedmart_locations.json")
    else:
        print("\n⚠️  No locations found")


if __name__ == "__main__":
    main()
