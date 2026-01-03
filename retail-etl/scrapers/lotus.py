"""
Lotus scraper for the unified ETL pipeline.

Uses Lotus Malaysia's JSON API to scrape grocery products.
"""
import json
import time
from typing import List, Dict
import requests
from datetime import datetime
import logging
import os

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class LotusScraper(BaseScraper):
    """Lotus Malaysia scraper using their mobile BFF API."""
    
    BASE_URL = 'https://api-o2o.lotuss.com.my/lotuss-mobile-bff'
    
    def __init__(self, store_url: str = None, max_products: int = None, pricing_zone_id: str = "LOTUSS_NATIONAL"):
        """
        Initialize Lotus scraper.
        
        Args:
            store_url: Not used (kept for interface compatibility)
            max_products: Maximum products to scrape (None = all)
            pricing_zone_id: Pricing Zone ID
        """
        super().__init__(
            pricing_zone_id=pricing_zone_id,
            store_name="Lotus Malaysia",
            store_address="Malaysia",
            latitude=None,
            longitude=None
        )
        self.max_products = max_products
        self.headers = {
            'key': 'SeiRQmEDnaZXOlpfKhCjV4Bo2y6vAcW99QKmzifsgP2uCMN7wF3ahRXex84kH6qUVIWoY5Dp0GEljdAvS1JytOZcLbnBTr',
            'channel': 'web',
            'version': '2.3.8',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'referer': 'https://www.lotuss.com.my/',
            'origin': 'https://www.lotuss.com.my'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.all_categories = None  # Cache all categories from API

    def _fetch_all_categories(self) -> List[int]:
        """
        Load grocery category IDs from lotuss_grocery_categories.json.
        Falls back to API fetch if file not found.
        
        Returns:
            List of grocery category IDs to scrape
        """
        # Try to load from JSON file first
        categories_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            'lotuss_grocery_categories.json'
        )
        
        if os.path.exists(categories_file):
            try:
                logger.info(f"Loading grocery categories from {categories_file}")
                with open(categories_file, 'r') as f:
                    categories_data = json.load(f)
                
                # Extract just the categoryId values
                category_ids = [cat['categoryId'] for cat in categories_data if 'categoryId' in cat]
                
                logger.info(f"Loaded {len(category_ids)} grocery categories from file")
                logger.info(f"Departments: {set(cat.get('departmentName', 'Unknown') for cat in categories_data)}")
                
                return category_ids
                
            except Exception as e:
                logger.error(f"Error loading categories from file: {e}")
                logger.info("Falling back to API fetch...")
        else:
            logger.warning(f"Grocery categories file not found: {categories_file}")
            logger.info("Falling back to API fetch...")
        
        # Fallback: Fetch from API
        try:
            # Fetch the complete category tree
            url = f'{self.BASE_URL}/product/v1/categories/4'
            params = {'websiteCode': 'malaysia_hy'}
            
            logger.info("Fetching category tree from Lotus API...")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            category_tree = data.get('data', {})
            
            # Recursively extract all category IDs
            def extract_category_ids(node, ids_list=None):
                if ids_list is None:
                    ids_list = []
                
                # Add current category ID
                if 'id' in node:
                    ids_list.append(node['id'])
                
                # Recursively add children
                for child in node.get('children', []):
                    extract_category_ids(child, ids_list)
                
                return ids_list
            
            all_categories = extract_category_ids(category_tree)
            
            logger.info(f"Successfully discovered {len(all_categories)} categories from Lotus API")
            
            return all_categories
            
        except Exception as e:
            logger.error(f"Error fetching categories from API: {e}")
            logger.warning("Falling back to hardcoded category list")
            
            # Final fallback to known working categories
            return [61116, 61119, 61122, 61125, 61128, 61131, 61134, 6003, 6006, 6009, 6015, 6018,
                    6021, 6024, 6027, 6030, 6033, 6036, 6039, 6042, 6045, 6048, 6051, 6054, 6057]

    def scrape(self) -> List[Dict]:
        """
        Scrape all products from Lotus Malaysia (all categories).
        
        Returns:
            List of product dictionaries conforming to BaseScraper schema
        """
        # Discover all categories dynamically
        if not self.all_categories:
            self.all_categories = self._fetch_all_categories()
        
        if not self.all_categories:
            logger.error("No categories found, unable to scrape")
            return []
        
        all_products = []
        seen_skus = set()  # Track SKUs to avoid duplicates
        total_scraped = 0
        total_duplicates = 0
        
        logger.info(f"Starting Lotus scrape for {len(self.all_categories)} categories")
        
        for idx, category_id in enumerate(self.all_categories, 1):
            if self.max_products and total_scraped >= self.max_products:
                logger.info(f"Reached max products limit: {self.max_products}")
                break
            
            logger.info(f"Scraping category {idx}/{len(self.all_categories)} (ID: {category_id})")
            category_products = self._scrape_category(category_id)
            
            # Deduplicate by SKU
            new_products = 0
            for product in category_products:
                sku = product.get('sku', '')
                if sku and sku not in seen_skus:
                    seen_skus.add(sku)
                    all_products.append(product)
                    new_products += 1
                elif sku:
                    total_duplicates += 1
            
            total_scraped += new_products
            
            logger.info(f"Scraped {len(category_products)} products, {new_products} new (total unique: {total_scraped}, duplicates skipped: {total_duplicates})")
            time.sleep(0.5)  # Rate limiting between categories
        
        logger.info(f"Total unique products scraped: {len(all_products)} (skipped {total_duplicates} duplicates)")
        return all_products

    def _scrape_category(self, category_id: int) -> List[Dict]:
        """
        Scrape all products from a single category using pagination.
        
        Args:
            category_id: Lotus category ID
            
        Returns:
            List of transformed product dictionaries
        """
        products = []
        offset = 0
        limit = 99  # Max items per page
        
        while True:
            # Build query JSON
            query = {
                "offset": offset,
                "limit": limit,
                "filter": {
                    "categoryId": [str(category_id)]
                },
                "websiteCode": "malaysia_hy"
            }
            
            # Make API request
            url = f'{self.BASE_URL}/product/v2/products'
            params = {'q': json.dumps(query)}
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # Check for API errors
                if data.get('status', {}).get('code') != 200:
                    logger.error(f"API error for category {category_id}: {data.get('status', {}).get('message')}")
                    break
                
                # Extract products
                page_products = data.get('data', {}).get('products', [])
                
                if not page_products:
                    break
                
                # Transform and add products
                for product in page_products:
                    transformed = self._transform_product(product)
                    if transformed:
                        products.append(transformed)
                
                # Check if more pages exist
                total = data.get('meta', {}).get('total', 0)
                if offset + limit >= total:
                    break
                
                offset += limit
                time.sleep(0.5)  # Rate limiting between pages
                
            except requests.RequestException as e:
                logger.error(f"Request error for category {category_id}, offset {offset}: {e}")
                break
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Parse error for category {category_id}: {e}")
                break
        
        return products

    def _transform_product(self, product: Dict) -> Dict:
        """
        Transform Lotus API product to BaseScraper schema.
        
        Args:
            product: Raw product dict from Lotus API
            
        Returns:
            Transformed product dict or None if invalid
        """
        try:
            # Extract price information
            # Use priceRange.minimumPrice.finalPrice.value (actual selling price)
            # NOT finalPricePerUOW which is calculated per unit of weight
            price_range = product.get('priceRange', {}).get('minimumPrice', {})
            final_price = price_range.get('finalPrice', {}).get('value')
            regular_price = price_range.get('regularPrice', {}).get('value')
            
            if final_price is None:
                logger.warning(f"No price found for SKU {product.get('sku')}")
                return None
            
            # Extract category (use last breadcrumb or fallback)
            breadcrumb = product.get('breadcrumb', [])
            if breadcrumb:
                category = breadcrumb[-1]['name']
            else:
                links = product.get('links')
                if links and isinstance(links, dict):
                    cat_info = links.get('category')
                    if cat_info and isinstance(cat_info, dict):
                        category = cat_info.get('name', 'Unknown')
                    else:
                        category = 'Unknown'
                else:
                    category = 'Unknown'
            
            # Extract brand
            brand = ''
            links = product.get('links')
            if links and isinstance(links, dict):
                brand_info = links.get('brand')
                if brand_info and isinstance(brand_info, dict):
                    brand = brand_info.get('name', '')
            
            # Build transformed record
            record = {
                'item_name': product.get('name', '').strip(),
                'unit_price': float(final_price),
                'category': category,
                'brand': brand,
                'sku': product.get('sku', ''),
                'available': product.get('stockStatus') == 'IN_STOCK',
                'scraped_at': datetime.now().isoformat(),
                'source': 'lotus_api'
            }
            
            # Add optional metadata
            if regular_price and regular_price != final_price:
                record['original_price'] = float(regular_price)
            
            if product.get('promotions'):
                record['promotion'] = product['promotions'][0].get('offerText', '')
            
            return record
            
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error transforming product {product.get('sku', 'unknown')}: {e}")
            return None

    def run(self) -> List[Dict]:
        """
        Execute the scraper and return products with store metadata.
        
        Returns:
            List of products with store information added
        """
        products = self.scrape()
        
        # Add store metadata to each product
        for product in products:
            product['store_name'] = self.store_name
            product['pricing_zone_id'] = self.pricing_zone_id
        
        return products


def main():
    """Test the scraper."""
    scraper = LotusScraper(max_products=100)
    products = scraper.run()
    
    print(f"\nScraped {len(products)} products")
    
    # Show sample
    if products:
        print("\nSample product:")
        import pprint
        pprint.pprint(products[0])
        
        # Show category distribution
        categories = {}
        for p in products:
            cat = p.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\nCategory distribution:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
