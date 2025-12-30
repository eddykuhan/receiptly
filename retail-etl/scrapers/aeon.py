"""
Aeon scraper adapter for the unified ETL pipeline.

Uses Selenium to scrape product data from Aeon (myAeon).
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


class AeonScraper(BaseScraper):
    """Aeon scraper using Selenium."""
    
    def __init__(self, store_url: str = "https://myaeon.com.my/view-all-products", max_pages: int = 5):
        """
        Initialize Aeon scraper.
        
        Args:
            store_url: Base URL for Aeon products
            max_pages: Maximum number of pages to scrape
        """
        super().__init__(
            store_name="Aeon Queensbay Mall", # Example store
            store_address="Queensbay Mall, 100, Persiaran Bayan Indah, 11900 Bayan Lepas, Pulau Pinang",
            latitude=5.3332,
            longitude=100.3067
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
        Scrape products from Aeon.
        
        Returns:
            List of product dictionaries.
        """
        self._setup_driver()
        all_products = []
        
        try:
            url = self.base_url
            print(f"Scraping Aeon: {url}")
            
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
            
            # TODO: Update these selectors based on actual Aeon DOM structure
            # Common e-commerce generic selectors
            product_cards = self.driver.find_elements(By.CSS_SELECTOR, '.product-item, .item-card, div[class*="product"]')
            
            if not product_cards:
                 product_cards = self.driver.find_elements(By.XPATH, '//div[contains(., "RM")]/ancestor::div[contains(@class, "card") or contains(@class, "col")]')
            
            print(f"Found {len(product_cards)} potential product cards")
            
            for index, card in enumerate(product_cards[:50]): 
                try:
                    product = self._extract_product_from_card(card)
                    if product:
                        all_products.append(product)
                except Exception as e:
                    continue

        except Exception as e:
            print(f"Error during Aeon scraping: {e}")
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
        
        for line in lines:
            if 'RM' in line:
                try:
                    price_str = line.replace('RM', '').replace(',', '').strip()
                    price = float(price_str)
                except:
                    continue
            elif len(line) > 5 and not name and not 'RM' in line: 
                name = line
        
        if not name or price == 0:
            return None
            
        return {
            'item_name': name,
            'unit_price': price,
            'category': 'Unknown',
            'brand': '',
            'sku': '',
            'product_url': '',
            'image_url': '',
            'available': True,
            'scraped_at': datetime.utcnow().isoformat(),
            'source': 'aeon_selenium_heuristic'
        }

if __name__ == "__main__":
    scraper = AeonScraper()
    products = scraper.run()
    if products:
        print(f"First product: {products[0]}")
