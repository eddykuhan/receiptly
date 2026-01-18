#!/usr/bin/env python
"""
Debug script to capture network requests and find the GraphQL/API endpoint for products.
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import json
import time


def capture_network_requests():
    """Capture network requests to find product API endpoint."""
    
    # Enable logging
    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}
    
    chrome_options = Options()
    # chrome_options.add_argument('--headless')  # Run with browser visible to debug
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
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
        time.sleep(5)  # Wait for API calls
        
        # Get performance logs
        logs = driver.get_log('performance')
        
        graphql_requests = []
        api_requests = []
        
        for entry in logs:
            try:
                log = json.loads(entry['message'])['message']
                if log['method'] == 'Network.responseReceived':
                    response = log['params']['response']
                    url = response['url']
                    
                    # Look for GraphQL or API endpoints
                    if 'graphql' in url.lower():
                        graphql_requests.append({
                            'url': url,
                            'status': response.get('status'),
                            'mimeType': response.get('mimeType')
                        })
                    elif 'api' in url.lower() or 'product' in url.lower():
                        api_requests.append({
                            'url': url,
                            'status': response.get('status'),
                            'mimeType': response.get('mimeType')
                        })
            except:
                pass
        
        print("\n=== GraphQL Requests ===")
        for req in graphql_requests:
            print(f"URL: {req['url']}")
            print(f"Status: {req['status']}")
            print(f"Type: {req['mimeType']}")
            print()
        
        print("\n=== API Requests ===")
        for req in api_requests:
            print(f"URL: {req['url']}")
            print(f"Status: {req['status']}")
            print(f"Type: {req['mimeType']}")
            print()
        
        # Try to find product elements on the page
        print("\n=== Looking for Product Elements ===")
        try:
            # Common product selectors
            selectors = [
                '.product-item',
                '[class*="product"]',
                '[data-product-id]',
                '.item',
                '[class*="card"]'
            ]
            
            for selector in selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"Found {len(elements)} elements with selector: {selector}")
                    if elements:
                        print(f"Sample element HTML (first 200 chars): {elements[0].get_attribute('outerHTML')[:200]}")
                    print()
        except Exception as e:
            print(f"Error finding elements: {e}")
        
        # Check if there's a Vue/Nuxt store
        print("\n=== Checking Vue Store ===")
        vue_data = driver.execute_script("""
            if (window.$nuxt && window.$nuxt.$store) {
                return window.$nuxt.$store.state;
            }
            return null;
        """)
        
        if vue_data:
            print("Vue store found!")
            with open('debug_vue_store.json', 'w', encoding='utf-8') as f:
                json.dump(vue_data, f, indent=2, ensure_ascii=False)
            print("Saved to debug_vue_store.json")
            
            # Look for products in the store
            def find_products_in_store(obj, path="", depth=0, max_depth=5):
                if depth > max_depth:
                    return
                
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key
                        
                        if isinstance(value, list) and len(value) > 0:
                            first_item = value[0]
                            if isinstance(first_item, dict):
                                product_fields = ['name', 'title', 'price', 'sku', 'id']
                                matching_fields = [f for f in product_fields if f in first_item]
                                if len(matching_fields) >= 2:
                                    print(f"\n🎯 Potential product array at: {current_path}")
                                    print(f"   Length: {len(value)}")
                                    print(f"   Matching fields: {matching_fields}")
                                    print(f"   Sample keys: {list(first_item.keys())[:15]}")
                        
                        find_products_in_store(value, current_path, depth + 1, max_depth)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj[:2]):
                        find_products_in_store(item, f"{path}[{i}]", depth + 1, max_depth)
            
            find_products_in_store(vue_data)
        else:
            print("No Vue store found")
        
        input("\nPress Enter to close browser...")
        
    finally:
        driver.quit()


if __name__ == '__main__':
    capture_network_requests()
