"""
AEON myAEON2go scraper for the unified ETL pipeline.

Uses AEON's web-slug-configs API to scrape grocery products via Playwright.
"""
import json
import time
from typing import List, Dict, Optional
from datetime import datetime
import logging
from playwright.sync_api import sync_playwright, Page, Browser

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class AeonScraper(BaseScraper):
    """AEON myAEON2go scraper using their web API."""
    
    BASE_URL = 'https://myaeon2go.com/api'
    
    # Known category IDs from investigation
    CATEGORIES = {
        'featured_items': 1066,
        'pick_of_the_week': 1559,
        'fresh_foods': 928,
        'ready_to_eat': 940,
        'electrical_appliances': 1598,
    }
    
    def __init__(self, store_url: str = None, max_products: int = None, pricing_zone_id: str = "AEON_NATIONAL"):
        """
        Initialize AEON scraper.
        
        Args:
            store_url: Not used (kept for interface compatibility)
            max_products: Maximum products to scrape (None = all)
            pricing_zone_id: Pricing Zone ID
        """
        super().__init__(
            pricing_zone_id=pricing_zone_id,
            store_name="AEON myAEON2go",
            store_address="Malaysia",
            latitude=None,
            longitude=None
        )
        self.max_products = max_products
        self.discovered_categories = []
        self.playwright = None
        self.browser = None
        self.page = None

    def _discover_all_categories(self) -> List[int]:
        """
        Discover all available category IDs by trying different approaches.
        
        For now, uses known categories. Future enhancement: scrape category tree.
        
        Returns:
            List of category IDs to scrape
        """
        # Return known categories
        categories = list(self.CATEGORIES.values())
        logger.info(f"Using {len(categories)} known AEON categories")
        return categories

    def _init_browser(self):
        """Initialize Playwright browser."""
        if not self.playwright:
            logger.info("Initializing Playwright browser...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            
            # Create context with extra headers
            context = self.browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                extra_http_headers={
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Referer': 'https://myaeon2go.com/',
                    'Origin': 'https://myaeon2go.com',
                }
            )
            
            self.page = context.new_page()
            
            # Navigate to homepage to establish session
            logger.info("Loading AEON homepage to establish session...")
            self.page.goto('https://myaeon2go.com/', wait_until='networkidle', timeout=30000)
            time.sleep(3)  # Wait for any JS to execute and cookies to be set
            logger.info("Browser session established")

    def _close_browser(self):
        """Close Playwright browser."""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser closed")

    def scrape(self) -> List[Dict]:
        """
        Scrape all products from AEON myAEON2go (all categories).
        
        Returns:
            List of product dictionaries conforming to BaseScraper schema
        """
        try:
            # Initialize browser
            self._init_browser()
            
            # Discover categories
            if not self.discovered_categories:
                self.discovered_categories = self._discover_all_categories()
            
            if not self.discovered_categories:
                logger.error("No categories found, unable to scrape")
                return []
            
            all_products = []
            total_scraped = 0
            
            logger.info(f"Starting AEON scrape for {len(self.discovered_categories)} categories")
            
            for idx, category_id in enumerate(self.discovered_categories, 1):
                if self.max_products and total_scraped >= self.max_products:
                    logger.info(f"Reached max products limit: {self.max_products}")
                    break
                
                logger.info(f"Scraping category {idx}/{len(self.discovered_categories)} (ID: {category_id})")
                category_products = self._scrape_category(category_id)
                
                all_products.extend(category_products)
                total_scraped += len(category_products)
                
                logger.info(f"Scraped {len(category_products)} products (total so far: {total_scraped})")
                time.sleep(1.0)  # Rate limiting between categories
            
            logger.info(f"Total products scraped: {len(all_products)}")
            return all_products
        
        finally:
            # Always close browser
            self._close_browser()

    def _scrape_category(self, category_id: int) -> List[Dict]:
        """
        Scrape all products from a single category using cursor-based pagination.
        
        Args:
            category_id: AEON category ID (soft_category_gid)
            
        Returns:
            List of transformed product dictionaries
        """
        products = []
        cursor = None
        limit = 100  # Items per page
        
        while True:
            # Build API URL with query parameters
            params = f'limit={limit}&sort=listPosition&soft_category_gid={category_id}&moduleType=productListEntities'
            if cursor:
                params += f'&cursor={cursor}'
            
            url = f'{self.BASE_URL}/web-slug-configs/data?{params}'
            
            try:
                # Use Playwright to fetch the API endpoint
                response = self.page.goto(url, wait_until='networkidle', timeout=30000)
                
                if response.status != 200:
                    logger.error(f"HTTP {response.status} error scraping category {category_id}")
                    break
                
                # Parse JSON response
                content = self.page.content()
                # Extract JSON from the page (it's displayed as text in browser)
                json_text = self.page.evaluate('() => document.body.innerText')
                data = json.loads(json_text)
                
                # Extract products from response
                product_entities = data.get('data', {}).get('productListEntities', [])
                
                if not product_entities:
                    logger.info(f"No more products in category {category_id}")
                    break
                
                # Transform each product
                for entity in product_entities:
                    product = self._transform_product(entity)
                    if product:
                        products.append(product)
                
                # Check for next page cursor
                cursor = data.get('data', {}).get('cursor')
                if not cursor:
                    logger.info(f"Reached end of category {category_id} (no cursor)")
                    break
                
                logger.debug(f"Fetched {len(product_entities)} products, cursor: {cursor}")
                time.sleep(0.5)  # Rate limiting between pages
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error scraping category {category_id}: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error scraping category {category_id}: {e}", exc_info=True)
                break
        
        return products

    def _transform_product(self, entity: Dict) -> Optional[Dict]:
        """
        Transform AEON API product entity to standardized format.
        
        Args:
            entity: Raw product entity from API
            
        Returns:
            Standardized product dictionary or None if invalid
        """
        try:
            variant = entity.get('variant', {})
            inventory = entity.get('inventory', [{}])[0]  # Use first inventory location
            product = entity.get('product', {})
            
            # Extract core fields
            item_name = f"{variant.get('brandingText', '')} {variant.get('nameText', '')}".strip()
            extended_info = variant.get('extendedInfoText', '')
            if extended_info:
                item_name = f"{item_name} {extended_info}"
            
            # Price data
            price = inventory.get('price', 0)
            standard_price = inventory.get('standardPrice', 0)
            
            # Category path (use deepest category)
            categories = product.get('categories', [])
            category = 'Unknown'
            if categories:
                # Get the most specific category (last in path)
                last_category = categories[-1]
                category = last_category.get('name', 'Unknown').replace('_', ' ').title()
            
            # Stock availability
            available_count = inventory.get('availableCount', 0)
            available = available_count > 0
            
            # Build product record
            return {
                'item_name': item_name,
                'unit_price': float(price),
                'category': category,
                'brand': variant.get('brandingText', ''),
                'sku': entity.get('sku', ''),
                'available': available,
                'scraped_at': datetime.utcnow().isoformat(),
                'source': 'aeon_myaeon2go',
                'metadata': {
                    'gid': variant.get('gid'),
                    'standard_price': float(standard_price) if standard_price else None,
                    'sale_percentage': inventory.get('salePercentage'),
                    'stock_count': available_count,
                    'location': inventory.get('fulfillerLocationName'),
                    'external_id': variant.get('externalIds', [{}])[0].get('value') if variant.get('externalIds') else None,
                }
            }
            
        except Exception as e:
            logger.warning(f"Error transforming product: {e}")
            logger.debug(f"Problematic entity: {json.dumps(entity, indent=2)}")
            return None


def main():
    """Test the AEON scraper."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scraper = AeonScraper(max_products=50)  # Test with 50 products
    
    logger.info("Starting AEON test scrape...")
    raw_products = scraper.scrape()
    
    logger.info(f"Scraped {len(raw_products)} raw products")
    
    # Clean the products
    cleaned_products = scraper.clean(raw_products)
    
    logger.info(f"Cleaned to {len(cleaned_products)} products")
    
    # Show sample
    if cleaned_products:
        logger.info("\nSample products:")
        for product in cleaned_products[:5]:
            logger.info(f"  - {product['item_name']} | RM {product['unit_price']:.2f} | {product['category']}")
    
    # Save to file
    output_file = f"data/raw/aeon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(cleaned_products, f, indent=2)
    
    logger.info(f"\nSaved to {output_file}")


if __name__ == '__main__':
    main()
