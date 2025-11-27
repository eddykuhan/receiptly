"""
Store Location Web Scraper

This scraper extracts store locations from various retailer websites
and saves them in a structured format for use with the receipt OCR system.
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import time
from urllib.parse import urljoin, urlparse


@dataclass
class StoreLocation:
    """Data class for store location information"""
    store_name: str
    branch_name: str
    address: str
    city: str
    state: str
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source_url: str = ""


class StoreScraper:
    """Base class for store location scrapers"""
    
    def __init__(self, store_name: str, base_url: str):
        self.store_name = store_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def scrape(self) -> List[StoreLocation]:
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement scrape()")
    
    def save_to_json(self, locations: List[StoreLocation], filename: str):
        """Save locations to JSON file"""
        data = [asdict(loc) for loc in locations]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved {len(locations)} locations to {filename}")
    
    def save_to_csv(self, locations: List[StoreLocation], filename: str):
        """Save locations to CSV file"""
        if not locations:
            print("No locations to save")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=asdict(locations[0]).keys())
            writer.writeheader()
            writer.writerows([asdict(loc) for loc in locations])
        print(f"✓ Saved {len(locations)} locations to {filename}")


class JayaGrocerScraper(StoreScraper):
    """Scraper for Jaya Grocer store locations"""
    
    def __init__(self):
        super().__init__("Jaya Grocer", "https://www.jaya.com.my")
    
    def scrape(self) -> List[StoreLocation]:
        """Scrape Jaya Grocer locations"""
        locations = []
        
        # Example: Adjust the URL and selectors based on actual website structure
        stores_url = f"{self.base_url}/stores"
        
        try:
            response = self.session.get(stores_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Example selectors - adjust based on actual HTML structure
            store_cards = soup.find_all('div', class_='store-card')
            
            for card in store_cards:
                try:
                    location = StoreLocation(
                        store_name=self.store_name,
                        branch_name=card.find('h3').text.strip(),
                        address=card.find('p', class_='address').text.strip(),
                        city=self._extract_city(card),
                        state=self._extract_state(card),
                        postal_code=self._extract_postal_code(card),
                        phone=self._extract_phone(card),
                        source_url=stores_url
                    )
                    locations.append(location)
                except Exception as e:
                    print(f"Error parsing store card: {e}")
                    continue
            
        except Exception as e:
            print(f"Error scraping {self.store_name}: {e}")
        
        return locations
    
    def _extract_city(self, element) -> str:
        """Extract city from element"""
        # Implement based on website structure
        return "Unknown"
    
    def _extract_state(self, element) -> str:
        """Extract state from element"""
        # Implement based on website structure
        return "Unknown"
    
    def _extract_postal_code(self, element) -> Optional[str]:
        """Extract postal code from element"""
        # Implement based on website structure
        return None
    
    def _extract_phone(self, element) -> Optional[str]:
        """Extract phone number from element"""
        # Implement based on website structure
        return None


class MydinScraper(StoreScraper):
    """Scraper for Mydin store locations"""
    
    def __init__(self):
        super().__init__("Mydin", "https://www.mydin.com.my")
    
    def scrape(self) -> List[StoreLocation]:
        """Scrape Mydin locations"""
        locations = []
        
        # Implement Mydin-specific scraping logic
        print(f"Scraping {self.store_name} locations...")
        
        # TODO: Implement actual scraping based on Mydin website structure
        
        return locations


class LotussScraper(StoreScraper):
    """Scraper for Lotus's (formerly Tesco) store locations"""
    
    def __init__(self):
        super().__init__("Lotus's", "https://www.lotuss.com")
    
    def scrape(self) -> List[StoreLocation]:
        """Scrape Lotus's locations"""
        locations = []
        
        # Implement Lotus's-specific scraping logic
        print(f"Scraping {self.store_name} locations...")
        
        # TODO: Implement actual scraping based on Lotus's website structure
        
        return locations


class GooglePlacesScraper:
    """
    Alternative: Use Google Places API to get store locations
    More reliable than web scraping but requires API key
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://places.googleapis.com/v1/places:searchText"
    
    def search_stores(self, store_name: str, location: str = "Malaysia") -> List[StoreLocation]:
        """Search for stores using Google Places API"""
        locations = []
        
        # Text search endpoint
        search_url = f"{self.base_url}"
        body = {
            'textQuery': f"{store_name} {location}",
        }

        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.priceLevel"
        }
        
        try:
            response = requests.post(search_url, json=body, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            for place in data.get('results', []):
                location = StoreLocation(
                    store_name=store_name,
                    branch_name=place.get('name', ''),
                    address=place.get('formatted_address', ''),
                    city=self._extract_city_from_address(place.get('formatted_address', '')),
                    state=self._extract_state_from_address(place.get('formatted_address', '')),
                    latitude=place.get('geometry', {}).get('location', {}).get('lat'),
                    longitude=place.get('geometry', {}).get('location', {}).get('lng'),
                    source_url=f"Google Places: {place.get('place_id', '')}"
                )
                locations.append(location)
            
        except Exception as e:
            print(f"Error using Google Places API: {e}")
        
        return locations
    
    def _extract_city_from_address(self, address: str) -> str:
        """Extract city from formatted address"""
        # Simple extraction - can be improved
        parts = address.split(',')
        if len(parts) >= 2:
            return parts[-2].strip()
        return "Unknown"
    
    def _extract_state_from_address(self, address: str) -> str:
        """Extract state from formatted address"""
        # Simple extraction - can be improved
        malaysian_states = [
            'Selangor', 'Kuala Lumpur', 'Penang', 'Johor', 'Perak',
            'Melaka', 'Negeri Sembilan', 'Pahang', 'Kedah', 'Kelantan',
            'Terengganu', 'Sabah', 'Sarawak', 'Perlis', 'Putrajaya', 'Labuan'
        ]
        
        for state in malaysian_states:
            if state.lower() in address.lower():
                return state
        
        return "Unknown"


def main():
    """Main function to run scrapers"""
    print("🔍 Store Location Scraper")
    print("=" * 50)
    
    # Example: Scrape Jaya Grocer
    print("\n1. Scraping Jaya Grocer...")
    jaya_scraper = JayaGrocerScraper()
    jaya_locations = jaya_scraper.scrape()
    
    if jaya_locations:
        jaya_scraper.save_to_json(jaya_locations, 'data/jaya_grocer_locations.json')
        jaya_scraper.save_to_csv(jaya_locations, 'data/jaya_grocer_locations.csv')
    
    # Example: Scrape Mydin
    print("\n2. Scraping Mydin...")
    mydin_scraper = MydinScraper()
    mydin_locations = mydin_scraper.scrape()
    
    if mydin_locations:
        mydin_scraper.save_to_json(mydin_locations, 'data/mydin_locations.json')
    
    # Example: Scrape Lotus's
    print("\n3. Scraping Lotus's...")
    lotuss_scraper = LotussScraper()
    lotuss_locations = lotuss_scraper.scrape()
    
    if lotuss_locations:
        lotuss_scraper.save_to_json(lotuss_locations, 'data/lotuss_locations.json')
    
    # Alternative: Use Google Places API (requires API key)
    # google_api_key = "YOUR_API_KEY_HERE"
    # google_scraper = GooglePlacesScraper(google_api_key)
    # jaya_locations = google_scraper.search_stores("Jaya Grocer", "Malaysia")
    
    print("\n✅ Scraping complete!")


if __name__ == "__main__":
    main()
