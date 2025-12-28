import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import re


class JayaGrocerScraper:
    """
    Web scraper for Jaya Grocer Gurney Paragon using Shopify's JSON API.
    Extracts product information including names, prices, categories, and SKUs.
    """
    
    def __init__(self, store_url: str = "https://jggp.jayagrocer.com"):
        self.store_url = store_url
        self.store_name = "Jaya Grocer Gurney Paragon"
        self.store_address = "Gurney Paragon Mall, Penang"
        self.latitude = 5.4381
        self.longitude = 100.3102
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
    def normalize_name(self, name: str) -> str:
        """
        Normalize product name for canonical matching.
        Removes extra spaces, converts to title case.
        """
        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name.strip())
        return name
    
    def fetch_products_page(self, page: int = 1, limit: int = 250) -> Optional[List[Dict]]:
        """
        Fetch a single page of products from Shopify JSON API.
        
        Args:
            page: Page number (1-indexed)
            limit: Number of products per page (max 250)
            
        Returns:
            List of product dictionaries or None if error
        """
        url = f"{self.store_url}/products.json"
        params = {
            'page': page,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('products', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            return None
    
    def extract_product_data(self, product: Dict) -> List[Dict]:
        """
        Extract relevant data from a product and its variants.
        Returns a list of records (one per variant) compatible with gold layer schema.
        
        Args:
            product: Product dictionary from Shopify API
            
        Returns:
            List of product records
        """
        records = []
        scraped_at = datetime.utcnow()
        
        # Extract common product info
        product_title = product.get('title', '')
        product_type = product.get('product_type', '')
        vendor = product.get('vendor', '')
        handle = product.get('handle', '')
        product_url = f"{self.store_url}/products/{handle}"
        tags = product.get('tags', [])
        
        # Process each variant (different sizes, options)
        variants = product.get('variants', [])
        
        for variant in variants:
            # Extract variant-specific data
            price = variant.get('price', '0')
            sku = variant.get('sku', '')
            variant_title = variant.get('title', '')
            available = variant.get('available', False)
            
            # Combine product title with variant title if not "Default Title"
            full_name = product_title
            if variant_title and variant_title != "Default Title":
                full_name = f"{product_title} - {variant_title}"
            
            record = {
                # Item details
                'item_name': full_name,
                'canonical_name': self.normalize_name(full_name),
                'unit_price': float(price),
                
                # Store context
                'store_name': self.store_name,
                'store_address': self.store_address,
                'latitude': self.latitude,
                'longitude': self.longitude,
                
                # Product metadata
                'category': product_type,
                'brand': vendor,
                'sku': sku,
                'product_url': product_url,
                'tags': tags if isinstance(tags, list) else [],
                'available': available,
                
                # Scraping metadata
                'scraped_at': scraped_at.isoformat(),
                'source': 'jaya_grocer_shopify_api'
            }
            
            records.append(record)
        
        return records
    
    def scrape_all_products(self, delay: float = 1.5) -> List[Dict]:
        """
        Scrape all products from the store by paginating through the API.
        
        Args:
            delay: Delay in seconds between page requests (rate limiting)
            
        Returns:
            List of all product records
        """
        all_records = []
        page = 1
        
        print(f"Starting scrape of {self.store_name}...")
        
        while True:
            print(f"Fetching page {page}...")
            products = self.fetch_products_page(page=page, limit=250)
            
            if products is None:
                print(f"Error fetching page {page}, stopping.")
                break
            
            if not products:
                print(f"No more products found. Completed at page {page-1}.")
                break
            
            # Extract data from each product
            for product in products:
                records = self.extract_product_data(product)
                all_records.extend(records)
            
            print(f"  Extracted {len(products)} products ({len(all_records)} total records)")
            
            # Rate limiting
            if products:  # Only delay if we got results
                time.sleep(delay)
            
            page += 1
        
        print(f"\nScraping complete! Total records: {len(all_records)}")
        return all_records
    
    def save_to_json(self, records: List[Dict], filename: str = "data/jaya_grocer_products.json"):
        """
        Save scraped records to JSON file.
        
        Args:
            records: List of product records
            filename: Output filename
        """
        output = {
            'store_name': self.store_name,
            'store_address': self.store_address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'total_products': len(records),
            'scraped_at': datetime.utcnow().isoformat(),
            'products': records
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"Data saved to {filename}")


def main():
    """Main execution function."""
    scraper = JayaGrocerScraper()
    
    # Scrape all products
    products = scraper.scrape_all_products(delay=1.5)
    
    # Save to JSON
    scraper.save_to_json(products)
    
    # Print summary statistics
    if products:
        print("\n=== Summary Statistics ===")
        print(f"Total products: {len(products)}")
        
        # Count by category
        categories = {}
        for p in products:
            cat = p.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"\nProducts by category:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {cat}: {count}")
        
        # Price statistics
        prices = [p['unit_price'] for p in products if p['unit_price'] > 0]
        if prices:
            print(f"\nPrice range: RM {min(prices):.2f} - RM {max(prices):.2f}")
            print(f"Average price: RM {sum(prices)/len(prices):.2f}")


if __name__ == "__main__":
    main()
