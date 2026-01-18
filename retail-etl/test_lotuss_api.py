import requests
import json
from urllib.parse import quote

class LotusAPIClient:
    def __init__(self):
        self.base_url = "https://api-o2o.lotuss.com.my/lotuss-mobile-bff"
        self.website_code = "malaysia_hy"
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en",
            "accept-encoding": "gzip, deflate, br, zstd",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "channel": "web",
            "version": "2.3.8",
            "key": "SeiRQmEDnaZXOlpfKhCjV4Bo2y6vAcW99QKmzifsgP2uCMN7wF3ahRXex84kH6qUVIWoY5Dp0GEljdAvS1JytOZcLbnBTr",
            "origin": "https://www.lotuss.com.my",
            "referer": "https://www.lotuss.com.my/"
        }

    def get_categories(self, category_id=4):
        """Get category tree starting from given category ID"""
        url = f"{self.base_url}/product/v1/categories/{category_id}"
        params = {"websiteCode": self.website_code}

        response = requests.get(url, headers=self.headers, params=params)
        return response.json()

    def get_products_by_category(self, category_url_key=None, category_id=None, offset=0, limit=15):
        """Get products by category URL key or category ID"""
        query = {
            "offset": offset,
            "limit": limit,
            "filter": {},
            "websiteCode": self.website_code
        }

        if category_url_key:
            query["filter"]["categoryUrlKey"] = category_url_key
        elif category_id:
            query["filter"]["categoryId"] = [category_id]

        # URL encode the JSON query
        query_str = json.dumps(query)
        encoded_query = quote(query_str)

        url = f"{self.base_url}/product/v2/products?q={encoded_query}"

        response = requests.get(url, headers=self.headers)
        return response.json()

def main():
    client = LotusAPIClient()

    print("=== Lotus's API Test ===\n")

    # Test categories API
    print("1. Getting categories...")
    categories = client.get_categories()
    print(f"Status: {categories.get('status', {}).get('message', 'Unknown')}")
    if categories.get('data', {}).get('children'):
        print(f"Found {len(categories['data']['children'])} top-level categories:")
        for i, cat in enumerate(categories['data']['children'], 1):
            print(f"  {i:2d}. {cat['name']} (ID: {cat['id']}, URL: {cat['urlKey']})")
    print()

    # Test products API with different categories
    test_categories = [
        ("baby-food", "Baby Food"),
        ("diapers", "Diapers"),
        ("milk-powder", "Milk Powder"),
        ("fresh-produce-1", "Fresh Produce")
    ]

    print("2. Testing product APIs...")
    for url_key, name in test_categories:
        print(f"\nTesting {name} (URL key: {url_key})...")
        try:
            products = client.get_products_by_category(category_url_key=url_key)
            status = products.get('status', {}).get('message', 'Unknown')
            total = products.get('meta', {}).get('total', 0)
            product_count = len(products.get('data', {}).get('products', []))

            print(f"  Status: {status}")
            print(f"  Total products: {total}")
            print(f"  Products in response: {product_count}")

            if product_count > 0:
                print("  Sample products:")
                for product in products['data']['products'][:2]:
                    print(f"    - {product.get('name', 'Unknown')}")

        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    main()