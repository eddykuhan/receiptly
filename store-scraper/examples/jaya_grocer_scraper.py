"""
Example: Specific scraper implementation for Jaya Grocer
This demonstrates how to customize the scraper for a specific website
"""

import requests
from bs4 import BeautifulSoup
from scraper import StoreScraper, StoreLocation
from typing import List
import re


class JayaGrocerDetailedScraper(StoreScraper):
    """
    Detailed scraper for Jaya Grocer with actual website structure
    
    Note: This is an example. You'll need to inspect the actual website
    and update the selectors accordingly.
    """
    
    def __init__(self):
        super().__init__("Jaya Grocer", "https://www.jaya.com.my")
    
    def scrape(self) -> List[StoreLocation]:
        """Scrape Jaya Grocer locations from their store locator page"""
        locations = []
        
        # Step 1: Get the store locator page
        stores_url = f"{self.base_url}/store-locator"
        
        try:
            print(f"Fetching {stores_url}...")
            response = self.session.get(stores_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Step 2: Find all store listings
            # Example selectors - adjust based on actual HTML
            store_elements = soup.select('.store-item, .location-card, [data-store]')
            
            print(f"Found {len(store_elements)} potential store elements")
            
            for idx, element in enumerate(store_elements, 1):
                try:
                    location = self._parse_store_element(element, stores_url)
                    if location:
                        locations.append(location)
                        print(f"  ✓ Parsed: {location.branch_name}")
                except Exception as e:
                    print(f"  ✗ Error parsing store {idx}: {e}")
                    continue
            
        except Exception as e:
            print(f"Error scraping {self.store_name}: {e}")
        
        return locations
    
    def _parse_store_element(self, element, source_url: str) -> StoreLocation:
        """Parse a single store element"""
        
        # Extract branch name
        branch_name = self._extract_text(element, 'h3, .store-name, .branch-name')
        
        # Extract full address
        address = self._extract_text(element, '.address, .store-address, p')
        
        # Extract phone
        phone = self._extract_phone_from_element(element)
        
        # Parse address components
        city, state, postal_code = self._parse_address(address)
        
        # Try to extract coordinates if available
        lat, lng = self._extract_coordinates(element)
        
        return StoreLocation(
            store_name=self.store_name,
            branch_name=branch_name or "Unknown Branch",
            address=address or "Unknown Address",
            city=city,
            state=state,
            postal_code=postal_code,
            phone=phone,
            latitude=lat,
            longitude=lng,
            source_url=source_url
        )
    
    def _extract_text(self, element, selector: str) -> str:
        """Extract text from element using CSS selector"""
        found = element.select_one(selector)
        return found.text.strip() if found else ""
    
    def _extract_phone_from_element(self, element) -> str:
        """Extract phone number from element"""
        # Look for phone in various formats
        phone_patterns = [
            r'\+?6?0?1[0-9]-?[0-9]{3,4}-?[0-9]{4}',  # Malaysian mobile
            r'\+?6?0?[2-9]-?[0-9]{3,4}-?[0-9]{4}',   # Malaysian landline
        ]
        
        text = element.get_text()
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None
    
    def _parse_address(self, address: str) -> tuple:
        """Parse address to extract city, state, and postal code"""
        city = "Unknown"
        state = "Unknown"
        postal_code = None
        
        if not address:
            return city, state, postal_code
        
        # Extract postal code (5 digits in Malaysia)
        postal_match = re.search(r'\b\d{5}\b', address)
        if postal_match:
            postal_code = postal_match.group(0)
        
        # Malaysian states
        states = {
            'selangor': 'Selangor',
            'kuala lumpur': 'Kuala Lumpur',
            'penang': 'Penang',
            'pulau pinang': 'Penang',
            'johor': 'Johor',
            'perak': 'Perak',
            'melaka': 'Melaka',
            'malacca': 'Melaka',
            'negeri sembilan': 'Negeri Sembilan',
            'pahang': 'Pahang',
            'kedah': 'Kedah',
            'kelantan': 'Kelantan',
            'terengganu': 'Terengganu',
            'sabah': 'Sabah',
            'sarawak': 'Sarawak',
            'perlis': 'Perlis',
            'putrajaya': 'Putrajaya',
            'labuan': 'Labuan'
        }
        
        address_lower = address.lower()
        for key, value in states.items():
            if key in address_lower:
                state = value
                break
        
        # Extract city (usually before state)
        # Common Malaysian cities
        cities = [
            'Georgetown', 'Butterworth', 'Bukit Mertajam',
            'Petaling Jaya', 'Subang Jaya', 'Shah Alam',
            'Johor Bahru', 'Ipoh', 'Kuching', 'Kota Kinabalu',
            'Melaka', 'Seremban', 'Kuantan', 'Kota Bharu',
            'Kuala Terengganu', 'Alor Setar', 'Kangar'
        ]
        
        for city_name in cities:
            if city_name.lower() in address_lower:
                city = city_name
                break
        
        return city, state, postal_code
    
    def _extract_coordinates(self, element) -> tuple:
        """Extract GPS coordinates if available in data attributes"""
        lat = element.get('data-lat') or element.get('data-latitude')
        lng = element.get('data-lng') or element.get('data-longitude')
        
        try:
            if lat and lng:
                return float(lat), float(lng)
        except ValueError:
            pass
        
        return None, None


if __name__ == "__main__":
    print("🔍 Jaya Grocer Store Scraper")
    print("=" * 50)
    
    scraper = JayaGrocerDetailedScraper()
    locations = scraper.scrape()
    
    print(f"\n✅ Found {len(locations)} locations")
    
    if locations:
        scraper.save_to_json(locations, 'data/jaya_grocer_locations.json')
        scraper.save_to_csv(locations, 'data/jaya_grocer_locations.csv')
        
        # Print summary
        print("\nSample locations:")
        for loc in locations[:3]:
            print(f"  • {loc.branch_name}")
            print(f"    {loc.address}")
            print(f"    {loc.city}, {loc.state} {loc.postal_code or ''}")
            print()
