"""
Lotus's Malaysia scraper adapter for the unified ETL pipeline.

Uses Selenium to scrape product data from Lotus's Online Store.
"""
import time
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


class LotusScraper(BaseScraper):
    """Lotus's scraper using Selenium."""
    
    def __init__(self, store_url: str = "https://www.lotuss.com.my/en/browse/all-products", max_pages: int = 5):
        """
        Initialize Lotus's scraper.
        
        Args:
            store_url: Base URL for Lotus's products
            max_pages: Maximum number of pages to scrape
        """
        super().__init__(
            store_name="Lotus's Penang E-Gate", # Example store
            store_address="Lebuh Tunku Kudin 1, 11700 Gelugor, Pulau Pinang",
            latitude=5.3761,
            longitude=100.3153
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
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def _close_driver(self):
        """Close WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def scrape(self) -> List[Dict]:
        """
        Scrape products from Lotus's.
        
        Returns:
            List of product dictionaries.
        """
        self._setup_driver()
        all_products = []
        
        try:
            # Note: URL structure might need adjustment based on specific category browsing
            url = self.base_url
            print(f"Scraping Lotus's: {url}")
            
            self.driver.get(url)
            
            # Wait for content
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except Exception as e:
                print(f"Timeout waiting for page: {e}")
                return []
            
            time.sleep(3) # Wait for hydration
            
            # Page iteration logic would go here. 
            # For now implementing scroll-to-load or pagination logic placeholder.
            
            # TODO: Update these selectors based on actual Lotus's DOM structure
            # Attempting generic selectors often found in React/Next/Vue apps
            product_cards = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="product-card"], div[data-testid*="product"], .product-item')
            
            if not product_cards:
                # Fallback: try looking for any list items with price info
                 product_cards = self.driver.find_elements(By.XPATH, '//div[contains(., "RM")]/ancestor::div[contains(@class, "card") or contains(@class, "item")]')
            
            print(f"Found {len(product_cards)} potential product cards")
            
            for index, card in enumerate(product_cards[:50]): # Limit for safety if selectors are too broad
                try:
                    product = self._extract_product_from_card(card)
                    if product:
                        all_products.append(product)
                except Exception as e:
                    # Stale element reference is common if DOM updates
                    continue

        except Exception as e:
            print(f"Error during Lotus scraping: {e}")
        finally:
            self._close_driver()
            
        return all_products

    def _extract_product_from_card(self, card) -> Dict:
        """Extract product info from a card WebElement."""
        text = card.text
        lines = text.split('\n')
        
        # Heuristic extraction
        name = ""
        price = 0.0
        
        # Assume price has 'RM'
        for line in lines:
            if 'RM' in line:
                try:
                    price_str = line.replace('RM', '').replace(',', '').strip()
                    price = float(price_str)
                except:
                    continue
            elif len(line) > 5 and not name: # First substantial line is likely name
                name = line
        
        if not name or price == 0:
            return None
            
        return {
            'item_name': name,
            'unit_price': price,
            'category': 'Unknown', # Need detailed selector or breadcrumb
            'brand': '',
            'sku': '', # Often hidden in data attributes
            'product_url': '',
            'image_url': '', # extract from <img src="...">
            'available': True,
            'scraped_at': datetime.utcnow().isoformat(),
            'source': 'lotuss_selenium_heuristic'
        }

if __name__ == "__main__":
    scraper = LotusScraper()
    products = scraper.run()
    if products:
        print(f"First product: {products[0]}")
