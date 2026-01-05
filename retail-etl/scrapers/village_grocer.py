"""
Village Grocer Scraper (Bites.com.my)
https://www.bites.com.my/

Shopify-based platform with full JSON API access.
Scrapes products from all collections and normalizes to canonical format.

Integration Notes:
- Follows BaseScraper interface for ETL pipeline integration
- Uses async HTTP for efficient API pagination
- Implements deduplication by SKU across collections
- Returns standardized product format compatible with canonicalizer
"""

import json
import logging
import asyncio
from typing import Optional, List, Dict
from urllib.parse import urljoin
from datetime import datetime
import aiohttp

from scrapers.base_scraper import BaseScraper
from etl_transformers.category_normalizer import normalize_category

logger = logging.getLogger(__name__)


class VillageGrocerScraperConfig:
    """Configuration for Village Grocer scraper."""
    
    BASE_URL = "https://www.bites.com.my"
    COLLECTIONS_ENDPOINT = f"{BASE_URL}/collections"
    PRODUCTS_PER_PAGE = 250  # Max Shopify allows
    REQUEST_TIMEOUT = 30
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1  # seconds
    RATE_LIMIT_DELAY = 0.5  # seconds between requests
    
    # Collections to scrape (handle names from URL)
    # Excludes temporary promotions and deals
    COLLECTIONS = [
        "groceries",           # Main groceries: ~7,266 products
        "fridge",              # Refrigerated: ~2,046 products
        "fresh",               # Fresh produce: ~907 products
        "household",           # Household items: ~1,487 products
        "village-grocers-bakery",  # Baker's Village
        "bakery",              # Bakery products
    ]


class VillageGrocerProductParser:
    """Parse Shopify product JSON into ETL-compatible format."""
    
    @staticmethod
    def parse_product(product: dict) -> Optional[dict]:
        """
        Parse Shopify product JSON to BaseScraper format.
        
        Args:
            product: Shopify product object
            
        Returns:
            ETL-compatible product dict or None if invalid
        """
        try:
            if not product.get('id') or not product.get('title'):
                return None
            
            # Get first variant (Village Grocer typically has single variant per product)
            variant = product.get('variants', [{}])[0]
            
            # Return BaseScraper-compatible format
            return {
                'item_name': product['title'].strip(),
                'unit_price': float(variant.get('price', 0) or 0),
                'category': normalize_category(product.get('product_type', 'Uncategorized').strip()),  # Normalize category
                'brand': product.get('vendor', '').strip() or 'Unbranded',
                'sku': variant.get('sku', ''),
                'available': variant.get('available', True),
                'scraped_at': datetime.utcnow().isoformat(),
                'source': 'village_grocer',
                
                # Additional metadata (optional fields)
                'metadata': {
                    'product_id': str(product['id']),
                    'variant_id': str(variant.get('id', '')),
                    'size': variant.get('title', 'UNIT').strip(),
                    'grams': variant.get('grams', 0),
                    'tags': product.get('tags', []),
                    'url': urljoin(VillageGrocerScraperConfig.BASE_URL, f"/products/{product.get('handle', '')}"),
                    'image_url': product.get('featured_image', {}).get('src', '') if product.get('featured_image') else None,
                }
            }
        except Exception as e:
            logger.error(f"Error parsing product {product.get('id')}: {e}")
            return None


class VillageGrocerScraper(BaseScraper):
    """Village Grocer scraper using Shopify JSON API."""
    
    def __init__(self, store_url: str = None, max_products: int = None, 
                 pricing_zone_id: str = "VILLAGE_GROCER_MY", collections: List[str] = None):
        """
        Initialize Village Grocer scraper.
        
        Args:
            store_url: Not used (kept for interface compatibility)
            max_products: Maximum products to scrape (None = all)
            pricing_zone_id: Pricing Zone ID for this retailer
            collections: Specific collections to scrape (None = default collections)
        """
        super().__init__(
            pricing_zone_id=pricing_zone_id,
            store_name="Village Grocer",
            store_address="Malaysia",
            latitude=None,
            longitude=None
        )
        self.max_products = max_products
        self.collections = collections or VillageGrocerScraperConfig.COLLECTIONS
        self.config = VillageGrocerScraperConfig()
        self.session = None
        self.products = []
        self.stats = {
            'collections_processed': 0,
            'products_scraped': 0,
            'products_skipped': 0,
            'api_errors': 0,
            'errors': []
        }
    
    async def __aenter__(self):
        """Context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _fetch_json(self, url: str, params: dict = None) -> Optional[dict]:
        """
        Fetch and parse JSON from URL with retry logic.
        
        Args:
            url: URL to fetch
            params: Query parameters
            
        Returns:
            Parsed JSON or None on error
        """
        for attempt in range(self.config.RETRY_ATTEMPTS):
            try:
                async with self.session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        await asyncio.sleep(self.config.RATE_LIMIT_DELAY)
                        return await response.json()
                    elif response.status == 429:  # Rate limited
                        delay = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited. Waiting {delay}s")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"HTTP {response.status} for {url}")
                        self.stats['api_errors'] += 1
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.config.RETRY_ATTEMPTS}: {url}")
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
            
            if attempt < self.config.RETRY_ATTEMPTS - 1:
                await asyncio.sleep(self.config.RETRY_DELAY * (2 ** attempt))
        
        self.stats['api_errors'] += 1
        return None
    
    async def _fetch_collection_products(
        self,
        collection_handle: str
    ) -> list[dict]:
        """
        Fetch all products from a collection using pagination.
        
        Args:
            collection_handle: Collection handle/slug
            
        Returns:
            List of normalized product dicts
        """
        products = []
        page = 1
        
        logger.info(f"Fetching collection: {collection_handle}")
        
        while True:
            url = f"{self.config.COLLECTIONS_ENDPOINT}/{collection_handle}/products.json"
            params = {
                'limit': self.config.PRODUCTS_PER_PAGE,
                'page': page
            }
            
            data = await self._fetch_json(url, params)
            if not data or 'products' not in data:
                break
            
            page_products = data.get('products', [])
            if not page_products:
                break
            
            # Parse products
            for product in page_products:
                parsed = VillageGrocerProductParser.parse_product(product)
                if parsed:
                    products.append(parsed)
                    self.stats['products_scraped'] += 1
                else:
                    self.stats['products_skipped'] += 1
            
            logger.info(f"  Page {page}: {len(page_products)} products")
            
            # Check if we got fewer than limit (last page)
            if len(page_products) < self.config.PRODUCTS_PER_PAGE:
                break
            
            page += 1
        
        return products
    
    async def _scrape_async(self) -> List[Dict]:
        """
        Internal async scraping implementation.
        
        Returns:
            List of normalized products from all collections
        """
        if not self.session:
            raise RuntimeError("Scraper must be used as context manager")
        
        logger.info(f"Starting Village Grocer scrape: {len(self.collections)} collections")
        
        # Track SKUs to deduplicate products across collections
        seen_skus = set()
        
        for collection_handle in self.collections:
            try:
                collection_products = await self._fetch_collection_products(collection_handle)
                
                # Deduplicate by SKU
                for product in collection_products:
                    sku = product.get('sku', '')
                    if sku and sku not in seen_skus:
                        seen_skus.add(sku)
                        self.products.append(product)
                    elif not sku:
                        # Products without SKU are kept (might be unique items)
                        self.products.append(product)
                
                self.stats['collections_processed'] += 1
                logger.info(f"✓ {collection_handle}: {len(collection_products)} products ({len(self.products)} unique)")
                
                # Enforce max_products limit
                if self.max_products and len(self.products) >= self.max_products:
                    logger.info(f"Reached max_products limit: {self.max_products}")
                    break
                    
            except Exception as e:
                error_msg = f"Error scraping {collection_handle}: {e}"
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)
        
        logger.info(f"Scrape complete: {len(self.products)} unique products from {self.stats['collections_processed']} collections")
        return self.products
    
    def scrape(self) -> List[Dict]:
        """
        Scrape products from Village Grocer (implements BaseScraper interface).
        
        Returns:
            List of product dictionaries in BaseScraper format
        """
        async def _run():
            async with self:
                return await self._scrape_async()
        
        return asyncio.run(_run())
    
    def get_stats(self) -> dict:
        """Get scraping statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    # Test scraper
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test single collection
    scraper = VillageGrocerScraper(collections=['fresh'], max_products=5)
    products = scraper.run()
    
    if products:
        print(f"\n✓ Scraped {len(products)} products")
        print("\nSample product:")
        print(json.dumps(products[0], indent=2, default=str))
    else:
        print("✗ No products scraped")
        sys.exit(1)
