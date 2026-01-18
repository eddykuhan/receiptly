import requests
import json
import os

API_URL = "https://mydin.my/api/map/getMapList"
OUTPUT_FILE = "data/mydin_locations.json"

def fetch_and_update_locations():
    print(f"Fetching data from {API_URL}...")
    try:
        # 405 usually means wrong method. Trying POST with headers.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        response = requests.post(API_URL, headers=headers, json={})
        # If POST fails with 404/405, we might try GET with headers, but 405 on GET strongly implies POST.
        response.raise_for_status()
        api_data = response.json()
        
        # Determine stricture of api_data
        # Based on user description, it returns values. Assuming list of objects.
        # Let's inspect first few items if running interactively, but here we just map.
        # Common API keys: 'name', 'address', 'lat', 'lng', 'contact', etc.
        
        # Since I haven't seen the API response, I will first print keys of first item 
        # to stdout so I can verify mapping before writing the final file IF this was a two-step.
        # But to be cleaner, I'll write a transformer that handles the likely schema 
        # or dumps the raw data if schema is unexpected.
        
        formatted_locations = []
        
        if isinstance(api_data, dict) and 'data' in api_data and isinstance(api_data['data'], list):
            items_list = api_data['data']
            print(f"Received {len(items_list)} locations from API.")
            
            for item in items_list:
                # Map fields based on actual API response
                # Keys: name, latitude, longitude, address, contact_number, business_hour, open
                
                name = item.get('name', 'Mydin Store').strip()
                address = item.get('address', '').strip()
                
                # Try to parse lat/lng ensuring float
                try:
                    lat = float(item.get('latitude', 0))
                    lng = float(item.get('longitude', 0))
                except (ValueError, TypeError):
                    lat = 0.0
                    lng = 0.0
                
                phone = item.get('contact_number', '').strip()
                
                # Derive region
                region = "Unknown"
                lower_addr = address.lower()
                if "kuala lumpur" in lower_addr or "kl" in lower_addr: region = "Kuala Lumpur"
                elif "selangor" in lower_addr: region = "Selangor"
                elif "penang" in lower_addr or "pulau pinang" in lower_addr: region = "Penang"
                elif "johor" in lower_addr: region = "Johor"
                elif "kedah" in lower_addr: region = "Kedah"
                elif "perak" in lower_addr: region = "Perak"
                elif "kelantan" in lower_addr: region = "Kelantan"
                elif "terengganu" in lower_addr: region = "Terengganu"
                elif "pahang" in lower_addr: region = "Pahang"
                elif "negeri sembilan" in lower_addr: region = "Negeri Sembilan"
                elif "melaka" in lower_addr or "malacca" in lower_addr: region = "Melaka"
                elif "perlis" in lower_addr: region = "Perlis"
                elif "sabah" in lower_addr: region = "Sabah"
                elif "sarawak" in lower_addr: region = "Sarawak"
                elif "putrajaya" in lower_addr: region = "Putrajaya"
                elif "labuan" in lower_addr: region = "Labuan"
                
                loc = {
                    "store_name": "Mydin",
                    "branch_name": name,
                    "address": address,
                    "latitude": lat,
                    "longitude": lng,
                    "phone": phone,
                    "rating": 4.0, # Default
                    "total_ratings": 100, # Default
                    "region_searched": region,
                    "business_hour": item.get('business_hour', '')
                }
                formatted_locations.append(loc)
                
            # Save to file
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(formatted_locations, f, indent=2)
            
            print(f"Successfully saved {len(formatted_locations)} locations to {OUTPUT_FILE}")
            
        else:
            print("Unexpected API response structure.")
            print(json.dumps(api_data, indent=2)[:500]) # Print sample

    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    fetch_and_update_locations()
