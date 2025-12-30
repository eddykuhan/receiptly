"""
MYDIN scraper adapter for the unified ETL pipeline.

Adapts the existing Selenium-based logic to BaseScraper interface.
"""
import time
import json
from typing import List, Dict
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from scrapers.base_scraper import BaseScraper


class MydinScraper(BaseScraper):
    """MYDIN scraper using Selenium."""
    
    def __init__(self, store_url: str = "https://mydin.my/category/all-products", max_pages: int = 5, pricing_zone_id: str = "MYDIN_NATIONAL"):
        """
        Initialize MYDIN scraper.
        
        Args:
            store_url: Base URL for MYDIN products
            max_pages: Maximum number of pages to scrape (prevent infinite loops)
            pricing_zone_id: Pricing Zone ID
        """
        super().__init__(
            pricing_zone_id=pricing_zone_id,
            store_name="MYDIN (National)", 
            store_address="Malaysia",
            latitude=None, 
            longitude=None
        )
        self.base_url = store_url
        self.max_pages = max_pages
        self.driver = None

    def _setup_driver(self):
        """Initialize Selenium WebDriver."""
        if self.driver:
            return

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        driver_path = ChromeDriverManager().install()
        # Workaround: webdriver-manager sometimes picks the wrong file (THIRD_PARTY_NOTICES, LICENSE)
        if "THIRD_PARTY_NOTICES" in driver_path or "LICENSE" in driver_path:
            import os
            driver_dir = os.path.dirname(driver_path)
            driver_path = os.path.join(driver_dir, "chromedriver")
            
        # Ensure executable permissions
        try:
            os.chmod(driver_path, 0o755)
        except Exception:
            pass  # Ignore if not allowed

        service = Service(driver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def _close_driver(self):
        """Close WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def scrape(self) -> List[Dict]:
        """
        Scrape products from MYDIN.
        
        Returns:
            List of product dictionaries.
        """
        self._setup_driver()
        all_products = []
        
        try:
            for page in range(1, self.max_pages + 1):
                url = f"{self.base_url}?page={page}"
                print(f"Scraping MYDIN page {page}: {url}")
                
                self.driver.get(url)
                
                # Wait for body
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except Exception as e:
                    print(f"Timeout waiting for page {page}: {e}")
                    break
                
                # Allow JS to execute
                time.sleep(3)
                
                # Retrieve data from window.__NUXT__
                products = self._extract_products_from_nuxt()
                
                if not products:
                    print(f"No products found on page {page}. Stopping.")
                    break
                
                all_products.extend(products)
                print(f"Found {len(products)} products on page {page}")
                
                time.sleep(2)  # Respectful delay
                
        except Exception as e:
            print(f"Error during MYDIN scraping: {e}")
        finally:
            self._close_driver()
            
        return all_products

    def _extract_products_from_nuxt(self) -> List[Dict]:
        """Extract product data from window.__NUXT__."""
        max_wait = 15
        poll_interval = 1
        waited = 0
        products_loaded = False
        
        # Poll for data
        while waited < max_wait:
            nuxt_data = self.driver.execute_script("return window.__NUXT__;")
            
            if nuxt_data and 'state' in nuxt_data:
                state = nuxt_data['state']
                for key in state.keys():
                    if key.startswith('$scategoryProducts-'):
                        category_data = state.get(key)
                        if category_data and isinstance(category_data, dict):
                            data_obj = category_data.get('data')
                            if data_obj is not None:
                                products_loaded = True
                                break
            
            if products_loaded:
                break
            
            time.sleep(poll_interval)
            waited += poll_interval
            
        if not products_loaded:
            print("Products did not load in time")
            return []

        # Extract items
        nuxt_data = self.driver.execute_script("return window.__NUXT__;")
        state = nuxt_data.get('state', {})
        
        scraped_items = []
        
        for key in state.keys():
            if key.startswith('$scategoryProducts-'):
                category_data = state.get(key)
                if category_data and isinstance(category_data, dict):
                    data_obj = category_data.get('data', {})
                    if isinstance(data_obj, dict):
                        items = data_obj.get('items', [])
                        
                        for item in items:
                            transformed = self._transform_item(item)
                            if transformed:
                                scraped_items.append(transformed)
                                
        return scraped_items

    def _transform_item(self, product: Dict) -> Dict:
        """Transform raw NUXT product to BaseScraper format."""
        name = product.get('custom_productname') or product.get('name', '')
        if not name:
            return None
            
        # Price extraction
        price = 0.0
        try:
            price_range = product.get('price_range', {})
            minimum_price = price_range.get('minimum_price', {})
            final_price = minimum_price.get('final_price', {})
            price = float(final_price.get('value', 0))
        except (ValueError, TypeError, AttributeError):
            pass
            
        # Category
        categories = product.get('categories', [])
        category = ''
        if categories and len(categories) > 0:
            category = categories[0].get('name', '') if isinstance(categories[0], dict) else ''
            
        # Availability
        salable_qty = product.get('salable_quantity', 0)
        available = salable_qty > 0

        # Image
        image = ''
        image_obj = product.get('image') or product.get('thumbnail')
        if image_obj and isinstance(image_obj, dict):
            image = image_obj.get('url', '')

        return {
            'item_name': name,
            'unit_price': price,
            'category': category,
            'brand': '', # Brand not explicitly in the snippet, maybe in attributes
            'sku': product.get('sku', ''),
            'product_url': '', # Not provided easily
            'image_url': image,
            'available': available,
            'scraped_at': datetime.utcnow().isoformat(),
            'source': 'mydin_selenium_nuxt'
        }

if __name__ == "__main__":
    scraper = MydinScraper(max_pages=2)
    products = scraper.run()
    if products:
        print(f"First product: {products[0]}")
