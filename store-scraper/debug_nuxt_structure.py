#!/usr/bin/env python
"""
Debug script to inspect the NUXT data structure from MYDIN website.
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json
import time


def inspect_nuxt_data():
    """Fetch and inspect the NUXT data structure."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        url = "https://mydin.my/category/all-products?page=1"
        print(f"Navigating to {url}...")
        driver.get(url)
        
        # Wait for page load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)
        
        # Get NUXT data
        nuxt_data = driver.execute_script("return window.__NUXT__;")
        
        if nuxt_data:
            # Save to file for inspection
            with open('debug_nuxt_structure.json', 'w', encoding='utf-8') as f:
                json.dump(nuxt_data, f, indent=2, ensure_ascii=False)
            
            print("✓ NUXT data saved to debug_nuxt_structure.json")
            
            # Print structure overview
            print("\n=== NUXT Data Structure ===")
            print(f"Top-level keys: {list(nuxt_data.keys())}")
            
            if 'data' in nuxt_data:
                print(f"\nData keys: {list(nuxt_data['data'].keys()) if isinstance(nuxt_data['data'], dict) else 'Not a dict'}")
                
                # Try to find product-like structures
                def find_products(obj, path="", depth=0, max_depth=5):
                    """Recursively search for product arrays."""
                    if depth > max_depth:
                        return
                    
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            current_path = f"{path}.{key}" if path else key
                            
                            # Check if this looks like a product array
                            if isinstance(value, list) and len(value) > 0:
                                first_item = value[0]
                                if isinstance(first_item, dict):
                                    # Check for product-like fields
                                    product_fields = ['name', 'title', 'price', 'sku', 'id']
                                    matching_fields = [f for f in product_fields if f in first_item]
                                    if matching_fields:
                                        print(f"\n🎯 Potential product array at: {current_path}")
                                        print(f"   Length: {len(value)}")
                                        print(f"   Matching fields: {matching_fields}")
                                        print(f"   Sample item keys: {list(first_item.keys())[:10]}")
                            
                            find_products(value, current_path, depth + 1, max_depth)
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj[:3]):  # Check first 3 items
                            find_products(item, f"{path}[{i}]", depth + 1, max_depth)
                
                print("\n=== Searching for Product Arrays ===")
                find_products(nuxt_data['data'])
        else:
            print("✗ No NUXT data found")
    
    finally:
        driver.quit()


if __name__ == '__main__':
    inspect_nuxt_data()
