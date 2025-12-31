"""
Fetch ALL 99 Speedmart locations (3,043+ stores) with complete location data.

Strategy:
1. Fetch complete store list from WordPress REST API (3,043 stores)
2. For stores missing coordinates, use Google Places API to find locations
3. Combine data for comprehensive coverage with accurate coordinates
"""

import os
import json
import requests
import time
import re
import html
from typing import List, Dict, Set, Optional, Any, Tuple
import argparse


# WordPress API constants
API_ROOT = "https://99speedmart.com.my/wp-json/wp/v2/stores"
PER_PAGE = 100


def extract_place_id(url: Optional[str]) -> Optional[str]:
    """Extract place_id from Google Maps URL"""
    if not url:
        return None
    m = re.search(r'place_id:([A-Za-z0-9_-]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'/place/([A-Za-z0-9_-]{10,})', url)
    if m:
        return m.group(1)
    return None


def extract_lat_lng(url: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """Extract coordinates from Google Maps URL"""
    if not url:
        return None, None

    # Handle Google Maps short URLs by following redirects
    if url.startswith('https://maps.app.goo.gl/') or url.startswith('https://goo.gl/maps/'):
        try:
            resp = requests.head(url, allow_redirects=True, timeout=10)
            url = resp.url
        except Exception:
            pass

    # Pattern 1: @lat,lng
    m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            pass

    # Pattern 2: /search/lat,+lng (short URL redirect format)
    m2 = re.search(r'/search/(-?\d+\.\d+),\s*\+?(-?\d+\.\d+)', url)
    if m2:
        try:
            return float(m2.group(1)), float(m2.group(2))
        except ValueError:
            pass

    # Pattern 3: !3d[lat]!4d[lng] (Google Maps deep link parameters)
    m3_lat = re.search(r'!3d(-?\d+\.\d+)', url)
    m3_lng = re.search(r'!4d(-?\d+\.\d+)', url)
    if m3_lat and m3_lng:
        try:
            return float(m3_lat.group(1)), float(m3_lng.group(1))
        except ValueError:
            pass

    return None, None


def clean_branch_name(title: Optional[Any], store_id: Optional[int]) -> str:
    """Clean and format branch name"""
    if isinstance(title, dict):
        title = title.get("rendered")
    if not title:
        return f"Store {store_id or 'Unknown'}"

    t = html.unescape(str(title))
    # Remove Store ID prefix (e.g. "3821 - ")
    t = re.sub(r'^\d+\s*[\u2013\u2014-]\s*', '', t)
    # Remove other noise
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def fetch_wordpress_stores(cache_file: str = "data/wordpress_stores_cache.json", force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Fetch all stores from WordPress REST API, with local caching"""
    import os
    import json

    # Check if cache exists and we're not forcing refresh
    if not force_refresh and os.path.exists(cache_file):
        print(f"📁 Loading stores from cache: {cache_file}")
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            print(f"✅ Loaded {len(cached_data)} stores from cache")
            return cached_data
        except Exception as e:
            print(f"⚠️  Cache file corrupted, fetching from API: {e}")

    # Ensure cache directory exists
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)

    print("📡 Fetching stores from WordPress API...")
    session = requests.Session()
    all_stores = []
    page = 1

    while True:
        params = {"per_page": PER_PAGE, "page": page}
        try:
            resp = session.get(API_ROOT, params=params, timeout=30)
            if resp.status_code in (404, 400): 
                break
            resp.raise_for_status()
            data = resp.json()

            if not data:
                break

            print(f"   Page {page}: {len(data)} stores")
            all_stores.extend(data)
            page += 1
            time.sleep(0.1)  # Be gentle with the API

        except Exception as e:
            print(f"   ❌ Error fetching page {page}: {e}")
            break

    print(f"✅ Fetched {len(all_stores)} stores from WordPress API")

    # Save to cache
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(all_stores, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved raw data to cache: {cache_file}")
    except Exception as e:
        print(f"⚠️  Failed to save cache: {e}")

    return all_stores


def search_store_location_google_places(store_name: str, branch_name: str, address: str, api_key: str) -> Optional[Dict]:
    """Search for a specific store location using Google Places API by branch name"""
    if not api_key or not branch_name:
        return None

    url = "https://places.googleapis.com/v1/places:searchText"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.nationalPhoneNumber,places.rating,places.userRatingCount,places.id"
    }

    # Search primarily by branch name for more accurate results
    # Format: "99 Speedmart [Branch Name]"
    text_query = f"{store_name} {branch_name}"
    print(f"   🔍 Searching Google Places: {text_query[:60]}...")

    body = {
        "textQuery": text_query,
        "maxResultCount": 3  # Get top 3 matches for better accuracy
    }

    try:
        response = requests.post(url, json=body, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        places = data.get('places', [])
        if not places:
            return None

        # Return the first (most relevant) result
        place = places[0]
        return {
            'latitude': place.get('location', {}).get('latitude'),
            'longitude': place.get('location', {}).get('longitude'),
            'address': place.get('formattedAddress', ''),
            'phone': place.get('nationalPhoneNumber', ''),
            'rating': place.get('rating'),
            'total_ratings': place.get('userRatingCount', 0),
            'place_id': place.get('id'),
            'source': 'google_places'
        }

    except Exception as e:
        print(f"   ❌ Google Places error: {str(e)}")
        return None


def transform_store_data(raw_store: Dict[str, Any], google_api_key: Optional[str] = None) -> Dict[str, Any]:
    """Transform raw store data and enrich with Google Places if needed"""
    acf = raw_store.get("acf") or {}
    maps_url = acf.get("maps")

    # Basic data from WordPress API
    lat, lng = extract_lat_lng(maps_url)
    branch = clean_branch_name(raw_store.get("title"), raw_store.get("id"))
    address = acf.get("store_address") or ""
    place_id = extract_place_id(maps_url)

    store_data = {
        "store_name": "99 Speedmart",
        "branch_name": f"99 Speedmart {branch}",
        "address": address,
        "latitude": lat,
        "longitude": lng,
        "phone": acf.get("phone") or acf.get("phone_number") or acf.get("store_phone") or acf.get("telephone"),
        "rating": None,
        "total_ratings": None,
        "place_id": place_id,
        "state": raw_store.get("state_name"),
        "area": raw_store.get("area_name"),
        "id": raw_store.get("id"),
        "source": "wordpress_api"
    }

    # If we don't have coordinates, try Google Places API
    if (lat is None or lng is None) and google_api_key:
        print(f"📍 Missing coordinates for: {store_data['branch_name'][:50]}...")
        print(f"   🔍 Searching Google Places by branch name...")
        google_data = search_store_location_google_places(
            store_data["store_name"],
            branch,
            address,
            google_api_key
        )

        if google_data:
            # Update with Google Places data
            store_data.update({
                'latitude': google_data['latitude'],
                'longitude': google_data['longitude'],
                'address': google_data['address'] or store_data['address'],
                'phone': google_data['phone'] or store_data['phone'],
                'rating': google_data['rating'],
                'total_ratings': google_data['total_ratings'],
                'place_id': google_data['place_id'] or store_data['place_id'],
                'source': 'wordpress_api + google_places'
            })
            print("   ✅ Found location via Google Places")
        else:
            print("   ⚠️  No location found via Google Places")
    return store_data


def main():
    print("🏪 99 Speedmart Complete Location Fetcher")
    print("=" * 70)
    print("Target: Fetch ALL 3,043+ stores with complete location data")
    print("Strategy: WordPress API + Google Places API enrichment")
    print("=" * 70)

    parser = argparse.ArgumentParser(description="Fetch all 99 Speedmart locations")
    parser.add_argument("--output", "-o", default="data/99_speedmart_complete.json",
                        help="Output JSON path")
    parser.add_argument("--use-google-places", action="store_true",
                        help="Use Google Places API to fill missing coordinates")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of stores to process (for testing)")
    parser.add_argument("--offset", type=int, default=0,
                        help="Skip first N stores (for testing stores without coordinates)")
    parser.add_argument("--refresh-cache", action="store_true",
                        help="Force refresh WordPress data from API instead of using cache")
    args = parser.parse_args()

    # Get Google Places API key if needed
    google_api_key = None
    if args.use_google_places:
        google_api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        if not google_api_key:
            print("\n❌ GOOGLE_PLACES_API_KEY not set!")
            print("   export GOOGLE_PLACES_API_KEY='your-api-key-here'")
            print("   Or run without --use-google-places flag")
            return

    # Step 1: Fetch all stores from WordPress API
    raw_stores = fetch_wordpress_stores(force_refresh=args.refresh_cache)

    if not raw_stores:
        print("❌ No stores fetched from WordPress API")
        return

    # Step 2: Transform and enrich each store
    print("\n🔄 Processing and enriching store data...")
    processed_stores = []

    # Apply offset and limit if specified (for testing)
    stores_to_process = raw_stores[args.offset:] if args.offset else raw_stores
    stores_to_process = stores_to_process[:args.limit] if args.limit else stores_to_process

    for i, raw_store in enumerate(stores_to_process, 1):
        if i % 100 == 0:
            print(f"   Processed {i}/{len(raw_stores)} stores...")

        store_data = transform_store_data(raw_store, google_api_key)
        processed_stores.append(store_data)

        # Rate limiting for Google Places API
        if google_api_key:
            time.sleep(0.1)

    # Step 3: Analyze results
    print("\n" + "=" * 70)
    print("📊 RESULTS SUMMARY")
    print("=" * 70)

    total_stores = len(processed_stores)
    with_coords = sum(1 for s in processed_stores if s.get('latitude') is not None and s.get('longitude') is not None)
    with_address = sum(1 for s in processed_stores if s.get('address'))
    wordpress_only = sum(1 for s in processed_stores if s.get('source') == 'wordpress_api')
    enriched = sum(1 for s in processed_stores if 'google_places' in str(s.get('source', '')))

    print(f"Total stores processed:     {total_stores}")
    print(f"Stores with coordinates:    {with_coords} ({with_coords/total_stores*100:.1f}%)")
    print(f"Stores with addresses:      {with_address} ({with_address/total_stores*100:.1f}%)")
    print(f"WordPress API only:         {wordpress_only}")
    print(f"Enriched with Google:       {enriched}")

    # Step 4: Save results
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = args.output if os.path.isabs(args.output) else os.path.join(script_dir, args.output)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(processed_stores, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Data saved to: {out_path}")

    # Step 5: Show usage instructions
    print("\n💡 To use in receipt processing:")
    print(f"   cp {args.output} ../retail-etl/data/99_speedmart_locations.json")

    if with_coords < total_stores * 0.5:  # Less than 50% coverage
        print("\n⚠️  WARNING: Low coordinate coverage!")
        print("   Consider using --use-google-places flag for better coverage")
        print("   Make sure GOOGLE_PLACES_API_KEY is set")


if __name__ == "__main__":
    main()
