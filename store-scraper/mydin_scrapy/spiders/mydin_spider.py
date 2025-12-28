import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from typing import Dict, List, Optional
import time
import json
from mydin_scrapy.items import MydinProductItem


class MydinSpider(scrapy.Spider):
    """
    Scrapy spider for MYDIN using Selenium to extract data from window.__NUXT__.
    Extracts product information including names, prices, SKUs, and stock levels.
    """
    name = "mydin"
    allowed_domains = ["mydin.my"]
    
    custom_settings = {
        'FEEDS': {
            'data/mydin_scrapy_products.json': {
                'format': 'json',
                'encoding': 'utf-8',
                'indent': 2,
                'overwrite': True,
            },
        },
    }
    
    def __init__(self, max_pages=None, *args, **kwargs):
        super(MydinSpider, self).__init__(*args, **kwargs)
        self.base_url = "https://mydin.my/category/all-products"
        self.store_name = "Mydin"
        self.store_address = "Malaysia"  # Generic - Mydin has multiple locations
        self.max_pages = int(max_pages) if max_pages else None
        self.current_page = 1
        self.driver = None
        
    def setup_driver(self):
        """Initialize Selenium WebDriver with headless Chrome."""
        if self.driver:
            return
            
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.logger.info("✓ WebDriver initialized")
    
    def close_driver(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            self.logger.info("✓ WebDriver closed")
    
    def start_requests(self):
        """Generate initial request for page 1."""
        # Setup driver before starting
        self.setup_driver()
        
        # We'll use Scrapy's Request but handle the actual scraping in parse
        url = f"{self.base_url}?page=1"
        yield scrapy.Request(url=url, callback=self.parse, dont_filter=True)
    
    def parse(self, response):
        """Parse the page and extract products from NUXT data."""
        # Navigate to the URL using Selenium
        self.driver.get(response.url)
        
        # Wait for page to load
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception as e:
            self.logger.error(f"Timeout waiting for page {self.current_page}: {e}")
            return
        
        # Give extra time for JavaScript to execute
        time.sleep(3)
        
        # Remove newsletter popups
        try:
            self.driver.execute_script("""
                document.querySelectorAll('[class*="ins-"]').forEach(el => el.remove());
                document.querySelectorAll('[id*="ins-"]').forEach(el => el.remove());
                document.body.style.overflow = 'auto';
            """)
        except:
            pass
        
        # Wait for products to load in NUXT state
        # Poll until data is not null or timeout
        max_wait = 15  # seconds
        poll_interval = 1  # second
        waited = 0
        products_loaded = False
        
        while waited < max_wait:
            nuxt_data = self.driver.execute_script("return window.__NUXT__;")
            
            if nuxt_data and 'state' in nuxt_data:
                state = nuxt_data['state']
                # Check if any $scategoryProducts-* has loaded data
                for key in state.keys():
                    if key.startswith('$scategoryProducts-'):
                        category_data = state.get(key)
                        if category_data and isinstance(category_data, dict):
                            data_obj = category_data.get('data')
                            if data_obj is not None:  # Data has loaded
                                products_loaded = True
                                self.logger.info(f"Products loaded after {waited} seconds")
                                break
            
            if products_loaded:
                break
            
            time.sleep(poll_interval)
            waited += poll_interval
        
        if not products_loaded:
            self.logger.warning(f"Products did not load after {max_wait} seconds")
        
        # Get the final NUXT data
        nuxt_data = self.driver.execute_script("return window.__NUXT__;")
        
        if not nuxt_data:
            self.logger.warning(f"No NUXT data found on page {self.current_page}")
            return
        
        # Extract products from NUXT state
        # Products are in state.$scategoryProducts-{category_id}.data.items
        products = []
        
        if 'state' in nuxt_data:
            state = nuxt_data['state']
            
            # Look for keys matching pattern $scategoryProducts-*
            for key in state.keys():
                if key.startswith('$scategoryProducts-'):
                    category_data = state.get(key)
                    
                    if category_data and isinstance(category_data, dict) and 'data' in category_data:
                        data_obj = category_data.get('data', {})
                        if isinstance(data_obj, dict):
                            items = data_obj.get('items', [])
                            if items:
                                products.extend(items)
                                self.logger.info(f"Found {len(items)} products in {key}")

        
        if not products:
            self.logger.info(f"No products found on page {self.current_page}. Stopping.")
            return
        
        self.logger.info(f"Total {len(products)} products on page {self.current_page}")
        
        # Process each product
        for product in products:
            try:
                item = self._create_item_from_product(product)
                if item:
                    yield item
            except Exception as e:
                self.logger.error(f"Error processing product: {e}")
                continue
        
        # Check if we should continue to next page
        if self.max_pages is None or self.current_page < self.max_pages:
            self.current_page += 1
            next_url = f"{self.base_url}?page={self.current_page}"
            
            # Add delay between pages
            time.sleep(2)
            
            yield scrapy.Request(url=next_url, callback=self.parse, dont_filter=True)
        else:
            self.logger.info(f"Reached max pages limit ({self.max_pages})")
    
    
    def _create_item_from_product(self, product: Dict) -> Optional[MydinProductItem]:
        """
        Transform raw product data to MydinProductItem.
        
        Product structure from MYDIN:
        {
            "id": 123,
            "sku": "ABC123",
            "name": "Product Name",
            "custom_productname": "Display Name",
            "custom_productdescription": "Description",
            "price_range": {
                "minimum_price": {
                    "final_price": {"value": 10.50, "currency": "MYR"},
                    "regular_price": {"value": 12.00, "currency": "MYR"}
                }
            },
            "quantity": 100,
            "salable_quantity": 100,
            "image": {"url": "https://..."},
            "thumbnail": {"url": "https://..."},
            "categories": [...]
        }
        
        Args:
            product: Product dictionary from NUXT state
            
        Returns:
            MydinProductItem or None if invalid
        """
        # Extract product name
        name = product.get('custom_productname') or product.get('name', '')
        
        if not name:
            return None
        
        # Extract SKU
        sku = product.get('sku', '')
        
        # Extract price from price_range structure
        price = 0.0
        try:
            price_range = product.get('price_range', {})
            minimum_price = price_range.get('minimum_price', {})
            final_price = minimum_price.get('final_price', {})
            price = float(final_price.get('value', 0))
        except (ValueError, TypeError, AttributeError):
            self.logger.warning(f"Could not extract price for product: {name}")
        
        # Extract stock/quantity
        quantity = product.get('quantity', 0)
        salable_quantity = product.get('salable_quantity', 0)
        available = salable_quantity > 0
        stock_status = 'in_stock' if available else 'out_of_stock'
        
        # Extract category (use first category if available)
        categories = product.get('categories', [])
        category = ''
        if categories and len(categories) > 0:
            category = categories[0].get('name', '') if isinstance(categories[0], dict) else ''
        
        # Extract image URL
        image = ''
        image_obj = product.get('image') or product.get('thumbnail')
        if image_obj and isinstance(image_obj, dict):
            image = image_obj.get('url', '')
        
        # Create item
        item = MydinProductItem()
        
        # Item details
        item['item_name'] = name
        item['canonical_name'] = name  # Will be normalized in pipeline
        item['unit_price'] = price
        
        # Store context
        item['store_name'] = self.store_name
        item['store_address'] = self.store_address
        item['latitude'] = None
        item['longitude'] = None
        
        # Product metadata
        item['sku'] = sku
        item['category'] = category
        item['stock_status'] = stock_status
        item['available'] = available
        item['image_url'] = image
        
        # Scraping metadata
        item['scraped_at'] = datetime.utcnow().isoformat()
        item['source'] = 'mydin_scrapy_nuxt_data'
        
        return item
    
    def closed(self, reason):
        """Called when spider closes."""
        self.close_driver()
