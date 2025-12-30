"""
MYDIN scraper adapter for the unified ETL pipeline.

Refactored to use Mydin's GraphQL API instead of Selenium/Requests-HTML.
"""
import json
import time
from typing import List, Dict
import requests
from datetime import datetime
import logging

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class MydinScraper(BaseScraper):
    """MYDIN scraper using internal GraphQL API."""
    
    # Main categories from Mydin (Food, Groceries, etc.)
    # 1222: Groceries/Food? (Found Wonda Coffee here)
    # 1513: Groceries?
    # 2665: Food & Beverages (from analysis)
    # 2669: Home & Living
    # 2667: Mom & Baby
    TARGET_CATEGORIES = [1222, 1513, 2665, 2667, 2668, 2669]

    def __init__(self, store_url: str = "https://myapi.mydin.my/magento/products", max_pages: int = 10, pricing_zone_id: str = "MYDIN_NATIONAL", target_categories: List[int] = None):
        """
        Initialize MYDIN scraper.
        
        Args:
            store_url: The Base GraphQL API URL
            max_pages: Maximum number of pages to scrape PER CATEGORY
            pricing_zone_id: Pricing Zone ID
            target_categories: List of category IDs to scrape
        """
        super().__init__(
            pricing_zone_id=pricing_zone_id,
            store_name="MYDIN (National)", 
            store_address="Malaysia",
            latitude=None, 
            longitude=None
        )
        self.max_pages = max_pages
        self.base_api_url = store_url
        self.target_categories = target_categories or self.TARGET_CATEGORIES
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Origin": "https://mydin.my",
            "Referer": "https://mydin.my/",
            "Content-Type": "application/json"
        }

    def scrape(self) -> List[Dict]:
        """
        Scrape products from MYDIN APIs.
        """
        all_products = []
        
        for category_id in self.TARGET_CATEGORIES:
            logger.info(f"Scraping Category ID: {category_id}")
            category_products = self._scrape_category(category_id)
            all_products.extend(category_products)
            
        return all_products

    def _scrape_category(self, category_id: int) -> List[Dict]:
        """Scrape all pages for a single category."""
        category_items = []
        
        for page in range(1, self.max_pages + 1):
            logger.info(f"Fetching page {page} for category {category_id}...")
            
            items = self._fetch_graphql_products(category_id, page)
            
            if not items:
                logger.info(f"No more items found for category {category_id} at page {page}")
                break
                
            for item in items:
                transformed = self._transform_item(item)
                if transformed:
                    category_items.append(transformed)
            
            logger.info(f"Found {len(items)} items on page {page}")
            time.sleep(1) # Polite delay
            
        return category_items

    def _fetch_graphql_products(self, category_id: int, page: int, page_size: int = 48) -> List[Dict]:
        """Execute GraphQL query to fetch products."""
        query_body = [
            {
                "filter": {"category_id": {"eq": str(category_id)}},
                "pageSize": page_size,
                "currentPage": page,
                "sort": {"position": "ASC"}
            },
            {
                "products": "products-custom-query",
                "metadata": {
                    "fields": """
                        items {
                            id
                            sku
                            name
                            custom_productname
                            url_key
                            image { url label }
                            thumbnail { url label }
                            salable_quantity
                            price_range {
                                minimum_price {
                                    final_price { value currency }
                                }
                            }
                            categories { name }
                        }
                    """
                }
            },
            {}
        ]
        
        try:
            resp = requests.get(
                self.base_api_url, 
                params={'body': json.dumps(query_body)}, 
                headers=self.headers, 
                timeout=20
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if data and 'data' in data and data['data'] and 'products' in data['data'] and data['data']['products']:
                    return data['data']['products'].get('items', []) or []
            else:
                logger.error(f"Error fetching data: {resp.status_code} - {resp.text[:200]}")
                
        except Exception as e:
            logger.error(f"Exception during request: {e}")
            
        return []

    def _transform_item(self, product: Dict) -> Dict:
        """Transform raw GraphQL product to BaseScraper format."""
        
        # Name
        name = product.get('custom_productname') or product.get('name')
        if not name:
            return None
            
        # Price
        price = 0.0
        try:
            price_data = product.get('price_range', {}).get('minimum_price', {}).get('final_price', {})
            price = float(price_data.get('value', 0))
        except (ValueError, TypeError, AttributeError):
            pass
            
        if price <= 0:
            return None

        # Image
        image_url = ""
        img_obj = product.get('image') or product.get('thumbnail')
        if img_obj:
            image_url = img_obj.get('url', "")

        # Category
        cat_name = "Unknown"
        cats = product.get('categories', [])
        if cats:
            cat_name = cats[0].get('name', 'Unknown')

        # Availability
        salable_qty = product.get('salable_quantity')
        if salable_qty is None:
            salable_qty = 0
            
        return {
            'item_name': name,
            'unit_price': price,
            'category': cat_name,
            'brand': '',
            'sku': product.get('sku', ''),
            'product_url': f"https://mydin.my/{product.get('url_key')}.html",
            'image_url': image_url,
            'available': salable_qty > 0,
            'scraped_at': datetime.utcnow().isoformat(),
            'source': 'mydin_graphql'
        }

if __name__ == "__main__":
    # Test run
    scraper = MydinScraper(max_pages=1)
    # Temporarily limit categories for testing
    scraper.TARGET_CATEGORIES = [1222] 
    results = scraper.scrape()
    print(f"Scraped {len(results)} items")
    if results:
        print(f"Sample: {results[0]}")
