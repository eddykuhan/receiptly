# Lotus's Scraping Analysis

## Executive Summary

Lotus's provides a comprehensive REST API for product data access, making it highly suitable for automated price comparison and receipt scanning applications. Unlike initial assumptions, Lotus's does NOT require traditional web scraping - it offers clean, structured API endpoints.

## API Architecture

### Base Configuration
- **Base URL**: `https://api-o2o.lotuss.com.my/lotuss-mobile-bff`
- **Website Code**: `malaysia_hy` (for hypermarket products)
- **Authentication**: API key-based (`key` header)
- **Response Format**: JSON
- **Rate Limiting**: Not observed in testing

### Required Headers
```python
headers = {
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
```

## API Endpoints

### 1. Categories API
**Endpoint**: `GET /product/v1/categories/{category_id}`
**Purpose**: Retrieve category hierarchy and metadata

**Parameters**:
- `category_id`: Starting category ID (default: 4 for "Hyper")
- `websiteCode`: `malaysia_hy`

**Example Request**:
```
GET https://api-o2o.lotuss.com.my/lotuss-mobile-bff/product/v1/categories/4?websiteCode=malaysia_hy
```

**Response Structure**:
```json
{
  "status": {"code": 200, "message": "success"},
  "data": {
    "id": 4,
    "name": "Hyper",
    "children": [
      {
        "id": 6003,
        "name": "Baby",
        "urlKey": "baby",
        "children": [
          {
            "id": 6018,
            "name": "Baby Food",
            "urlKey": "baby-food",
            "children": [...]
          }
        ]
      }
    ]
  }
}
```

### 2. Products API
**Endpoint**: `GET /product/v2/products`
**Purpose**: Retrieve products by category with pagination

**Parameters** (URL-encoded JSON query):
- `q`: JSON query string containing:
  - `offset`: Pagination offset (default: 0)
  - `limit`: Products per page (default: 15, max observed: 15)
  - `filter`: Filter criteria
    - `categoryUrlKey`: Filter by category URL key (e.g., "baby-food")
    - `categoryId`: Filter by category ID array (e.g., [6018])
  - `websiteCode`: `malaysia_hy`

**Example Requests**:

**By Category URL Key**:
```
GET /product/v2/products?q=%7B%22offset%22:0,%22limit%22:15,%22filter%22:%7B%22categoryUrlKey%22:%22baby-food%22%7D,%22websiteCode%22:%22malaysia_hy%22%7D
```

**By Category ID**:
```
GET /product/v2/products?q=%7B%22offset%22:0,%22limit%22:15,%22filter%22:%7B%22categoryId%22:%5B6018%5D%7D,%22websiteCode%22:%22malaysia_hy%22%7D
```

**Response Structure**:
```json
{
  "status": {"code": 200, "message": "success"},
  "meta": {
    "total": 72,
    "offset": 0,
    "limit": 15
  },
  "data": {
    "sort": "position:ASC",
    "filters": [],
    "breadcrumb": [],
    "categoryMetaData": {
      "categoryId": null,
      "metaTitle": null,
      "metaKeywords": null,
      "metaDescription": null
    },
    "products": [
      {
        "id": 12345,
        "sku": "TENTEN_NATURAL_BABY_NOODLE_BROCCOLI_150G",
        "name": "TENTEN NATURAL BABY NOODLE BROCCOLI 150G",
        "price": 5.90,
        "special_price": null,
        "image": "https://...",
        "url_key": "tenten-natural-baby-noodle-broccoli-150g",
        "stock_status": "IN_STOCK",
        "categories": [...],
        // ... additional product fields
      }
    ]
  }
}
```

## Category Hierarchy

### Top-Level Categories (Level 2)
Based on API response, here are the main product categories:

| Category Name | ID | URL Key | Product Count |
|---------------|----|---------|---------------|
| AV & Tech | 5976 | av-tech | Unknown |
| Baby | 6003 | baby | 455+ (across subcategories) |
| Bakery | 6504 | bakery | Unknown |
| ... | ... | ... | ... |

### Baby Category Breakdown (Example)
The Baby category (ID: 6003) contains several subcategories:

| Subcategory | ID | URL Key | Product Count |
|-------------|----|---------|---------------|
| Baby Feeding | 6006 | baby-feeding | Unknown |
| Baby Food | 6018 | baby-food | 72 |
| Baby Toiletries | 6030 | baby-toiletries | Unknown |
| Diapers | 6048 | diapers | 126 |
| Milk Powder | 6057 | milk-powder | 257 |
| Travel & Changing | 6072 | travel-changing | Unknown |

## Implementation Strategy

### Python Client Implementation
```python
import requests
import json
from urllib.parse import quote

class LotusAPIClient:
    def __init__(self):
        self.base_url = "https://api-o2o.lotuss.com.my/lotuss-mobile-bff"
        self.website_code = "malaysia_hy"
        # Headers as shown above

    def get_categories(self, category_id=4):
        # Implementation as shown in test script

    def get_products_by_category(self, category_url_key=None, category_id=None, offset=0, limit=15):
        # Implementation as shown in test script

    def get_all_products_in_category(self, category_url_key):
        """Paginate through all products in a category"""
        all_products = []
        offset = 0
        limit = 15

        while True:
            response = self.get_products_by_category(
                category_url_key=category_url_key,
                offset=offset,
                limit=limit
            )

            products = response.get('data', {}).get('products', [])
            if not products:
                break

            all_products.extend(products)
            offset += limit

            # Safety check to prevent infinite loops
            if offset > 1000:  # Arbitrary large number
                break

        return all_products
```

### Data Extraction for Receipt Scanning
For price comparison in receipt scanning applications, focus on:

1. **High-Volume Categories**: Baby products, household items, groceries
2. **Product Mapping**: Use SKU/name matching against receipt items
3. **Price Updates**: Regular API polling for price changes
4. **Store Location**: All products are from Lotus's hypermarkets

### Integration with Receiptly
```python
# Example integration
def find_lotuss_price(receipt_item_name, receipt_item_price):
    """Find Lotus's price for a receipt item"""
    client = LotusAPIClient()

    # Search across relevant categories
    search_categories = ['baby-food', 'diapers', 'milk-powder', 'groceries']

    for category in search_categories:
        products = client.get_all_products_in_category(category)

        for product in products:
            if fuzzy_match(receipt_item_name, product['name']):
                lotuss_price = product['price']
                # Compare prices, calculate savings, etc.
                return {
                    'lotuss_price': lotuss_price,
                    'savings': receipt_item_price - lotuss_price,
                    'product_name': product['name']
                }

    return None
```

## Advantages Over Traditional Scraping

1. **Reliability**: Structured API vs fragile HTML parsing
2. **Completeness**: Access to all product metadata
3. **Performance**: Faster data retrieval
4. **Legal Compliance**: API usage vs potential ToS violations
5. **Real-time Data**: Current pricing and availability

## Comparison with Mydin

| Aspect | Lotus's | Mydin |
|--------|---------|-------|
| API Type | REST | GraphQL |
| Authentication | API Key | None required |
| Categories | Hierarchical | Flat structure |
| Pagination | Offset-based | Cursor-based |
| Product Count | High (1000s) | Moderate (100s) |
| Data Richness | Comprehensive | Basic |

## Next Steps

1. **Complete Category Mapping**: Map all product categories
2. **Product Schema Analysis**: Document complete product JSON structure
3. **Price Comparison Logic**: Implement fuzzy matching algorithms
4. **Caching Strategy**: Cache API responses for performance
5. **Error Handling**: Implement retry logic and rate limiting
6. **Integration Testing**: Test with actual receipt data

## Conclusion

Lotus's provides an excellent API for automated price comparison, surpassing initial expectations. The structured data access makes it highly suitable for receipt scanning applications, offering a reliable alternative to traditional web scraping methods.