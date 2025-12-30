import requests
import json
from urllib.parse import urlencode

class Aeon2GoAPIClient:
    def __init__(self):
        self.base_url = "https://myaeon2go.com"
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "accept-encoding": "gzip, deflate, br, zstd",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "referer": "https://myaeon2go.com/"
        }

    def get_products_by_category(self, gid=1066, limit=200, in_stock_only=True):
        """
        Get products using the discovered /api/product/ples endpoint

        Args:
            gid (int): Group/Category ID (default: 1066 - likely Baby & Kids)
            limit (int): Maximum number of products to return
            in_stock_only (bool): Filter to in-stock products only

        Returns:
            dict: API response or error information
        """
        endpoint = "/api/product/ples"

        params = {
            "getSmartBrand": "true",
            "isCarousel": "true",
            "inStockOnly": str(in_stock_only).lower(),
            "limit": str(limit),
            "excludeVariants": "",
            "serviceType": "",
            "skipProduct": "false",
            "gid": str(gid),
            "pleType": "softCategory"
        }

        url = f"{self.base_url}{endpoint}?{urlencode(params)}"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)

            # Check if we got a CAPTCHA challenge
            if response.status_code == 403:
                if "DataDome" in response.text or "captcha" in response.text.lower():
                    return {
                        "status": "blocked",
                        "message": "Request blocked by DataDome CAPTCHA protection",
                        "status_code": 403,
                        "response_headers": dict(response.headers),
                        "url": url
                    }
                else:
                    return {
                        "status": "forbidden",
                        "message": "Access forbidden",
                        "status_code": 403,
                        "response_headers": dict(response.headers),
                        "url": url
                    }

            elif response.status_code == 200:
                try:
                    data = response.json()
                    return {
                        "status": "success",
                        "data": data,
                        "status_code": 200,
                        "url": url
                    }
                except json.JSONDecodeError:
                    return {
                        "status": "success",
                        "data": response.text,
                        "status_code": 200,
                        "url": url
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Unexpected status code: {response.status_code}",
                    "status_code": response.status_code,
                    "response_text": response.text[:500],  # First 500 chars
                    "url": url
                }

        except requests.exceptions.Timeout:
            return {
                "status": "timeout",
                "message": "Request timed out",
                "url": url
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": f"Request failed: {str(e)}",
                "url": url
            }

    def test_different_categories(self):
        """
        Test the API with different category IDs to see if they work
        """
        test_categories = [
            1066,  # Original category (likely Baby & Kids)
            1001,  # Common category ID pattern
            2001,  # Another common pattern
            1,     # Root category
            100,   # Another potential category
        ]

        results = {}
        for gid in test_categories:
            print(f"Testing category ID: {gid}")
            result = self.get_products_by_category(gid=gid, limit=10)  # Smaller limit for testing
            results[gid] = result

            if result["status"] == "success":
                print(f"  ✅ Success! Status: {result['status_code']}")
                if isinstance(result.get("data"), dict):
                    # Try to extract product count if available
                    products = result["data"].get("data", {}).get("products", [])
                    print(f"  📦 Products found: {len(products) if isinstance(products, list) else 'Unknown'}")
                else:
                    print(f"  📄 Response type: {type(result.get('data'))}")
            elif result["status"] == "blocked":
                print(f"  🚫 Blocked by CAPTCHA: {result['message']}")
            else:
                print(f"  ❌ {result['status'].upper()}: {result['message']}")

            print()

        return results

def main():
    client = Aeon2GoAPIClient()

    print("=== Aeon2Go API Test ===\n")
    print("⚠️  Note: Aeon2Go uses DataDome CAPTCHA protection.")
    print("   All requests are expected to be blocked with 403 errors.\n")

    # Test the main API endpoint
    print("1. Testing main product API endpoint...")
    result = client.get_products_by_category()

    print(f"URL: {result.get('url', 'N/A')}")
    print(f"Status: {result['status'].upper()}")

    if result["status"] == "success":
        print("✅ SUCCESS! API is accessible")
        if isinstance(result.get("data"), dict):
            print(f"Response keys: {list(result['data'].keys())}")
        else:
            print(f"Response preview: {str(result['data'])[:200]}...")
    elif result["status"] == "blocked":
        print("🚫 BLOCKED: DataDome CAPTCHA protection active")
        print(f"Message: {result['message']}")
    else:
        print(f"❌ ERROR: {result['message']}")

    print()

    # Test different category IDs
    print("2. Testing different category IDs...")
    category_results = client.test_different_categories()

    # Summary
    print("3. Test Summary:")
    success_count = sum(1 for r in category_results.values() if r["status"] == "success")
    blocked_count = sum(1 for r in category_results.values() if r["status"] == "blocked")
    error_count = len(category_results) - success_count - blocked_count

    print(f"   Total categories tested: {len(category_results)}")
    print(f"   ✅ Successful: {success_count}")
    print(f"   🚫 Blocked by CAPTCHA: {blocked_count}")
    print(f"   ❌ Errors: {error_count}")

    if success_count == 0:
        print("\n📋 CONCLUSION: Aeon2Go API is completely protected by DataDome CAPTCHA.")
        print("   Automated access is not feasible without bypassing the protection system.")

if __name__ == "__main__":
    main()