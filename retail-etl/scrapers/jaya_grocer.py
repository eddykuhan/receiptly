"""
Jaya Grocer scraper adapter for the unified ETL pipeline.

Wraps the existing Jaya Grocer scraper logic to conform to BaseScraper interface.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'store-scraper'))

from jaya_grocer_scraper import JayaGrocerScraper as OriginalScraper
from scrapers.base_scraper import BaseScraper
from etl_transformers.category_normalizer import normalize_category
from typing import List, Dict


class JayaGrocerScraper(BaseScraper):
    """Jaya Grocer scraper conforming to BaseScraper interface."""
    
    def __init__(self, store_url: str = "https://jggp.jayagrocer.com", pricing_zone_id: str = "JG_PENANG"):
        """
        Initialize Jaya Grocer scraper.
        
        Args:
            store_url: Base URL for the Jaya Grocer store
            pricing_zone_id: Pricing Zone ID (e.g. "JG_PENANG")
        """
        # Initialize base scraper with store metadata
        super().__init__(
            pricing_zone_id=pricing_zone_id,
            store_name="Jaya Grocer (Penang)", # Generic zone name
            store_address="Gurney Paragon Mall, Penang", # Representative address
            latitude=None, 
            longitude=None
        )
        
        # Initialize the original scraper
        self.original_scraper = OriginalScraper(store_url)
    
    def scrape(self) -> List[Dict]:
        """
        Scrape products from Jaya Grocer.
        
        Returns:
            List of product dictionaries conforming to BaseScraper schema
        """
        # Use the original scraper to get products
        products = self.original_scraper.scrape_all_products(delay=1.5)
        
        # Transform to match BaseScraper schema
        transformed = []
        for product in products:
            # Clean item name - remove "- 1 UNIT" suffix
            item_name = product['item_name']
            item_name = item_name.replace(' - 1 UNIT', '').replace(' - 1 unit', '')
            
            record = {
                'item_name': item_name,
                'unit_price': product['unit_price'],
                'category': normalize_category(product.get('category', 'Unknown')),
                'brand': product.get('brand', ''),
                'sku': product.get('sku', ''),
                'available': product.get('available', True),
                'scraped_at': product.get('scraped_at'),
                'source': 'jaya_grocer_shopify_api'
            }
            transformed.append(record)
        
        return transformed


def main():
    """Test the scraper."""
    scraper = JayaGrocerScraper()
    products = scraper.run()
    print(f"\nScraped {len(products)} products")
    
    # Show sample
    if products:
        print("\nSample product:")
        print(products[0])


if __name__ == "__main__":
    main()
