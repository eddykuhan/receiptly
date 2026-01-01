# Lotus Website Scraping Analysis

## Overview
Lotus Malaysia (https://www.lotuss.com.my/en) uses a modern API-based architecture with JSON endpoints that can be scraped programmatically.

## Key Findings

### 1. **API Architecture**
- **Base URL**: `https://api-o2o.lotuss.com.my/lotuss-mobile-bff`
- **Product API**: `/product/v2/products`
- **Categories API**: `/product/v1/categories/{id}`
- **Content Type**: JSON (application/json)
- **Authentication**: Static API key in header

### 2. **Required Headers**
```python
headers = {
    'key': 'SeiRQmEDnaZXOlpfKhCjV4Bo2y6vAcW99QKmzifsgP2uCMN7wF3ahRXex84kH6qUVIWoY5Dp0GEljdAvS1JytOZcLbnBTr',
    'channel': 'web',
    'version': '2.3.8',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    'referer': 'https://www.lotuss.com.my/',
    'origin': 'https://www.lotuss.com.my'
}
```

### 3. **Product API Endpoint**

#### **URL Pattern**
```
GET https://api-o2o.lotuss.com.my/lotuss-mobile-bff/product/v2/products?q={query_json}
```

#### **Query Parameters (URL-encoded JSON)**
```python
query = {
    "offset": 0,           # Pagination offset
    "limit": 15,           # Items per page (can be increased to 99)
    "filter": {
        "categoryId": ["61116"]  # Category filter
    },
    "websiteCode": "malaysia_hy"  # Store type (hyper = Lotus hypermarket)
}
```

#### **Alternative: Fetch by SKUs**
```python
query = {
    "filter": {
        "sku": ["75199339", "75199257", ...]  # List of SKUs
    },
    "offset": 0,
    "limit": 99,
    "websiteCode": "malaysia_hy"
}
```

### 4. **Response Structure**
```json
{
    "status": {
        "code": 200,
        "message": "success"
    },
    "meta": {
        "total": 348,      // Total products in category
        "offset": 0,
        "limit": 15
    },
    "data": {
        "filters": [...],   // Available filters (brand, etc.)
        "products": [
            {
                "id": 128595,
                "sku": "75199238",
                "name": "G+G GOLDEN WISHES RM118",
                "stockStatus": "IN_STOCK",
                "sellingType": "qty",
                "weightPerPiece": 3,
                "unitOfWeight": "Each",
                "unitOfQuantity": "Each",
                "regularPricePerUOW": 39.33,
                "finalPricePerUOW": 37.33,
                "priceRange": {
                    "minimumPrice": {
                        "regularPrice": {
                            "value": 118.00,
                            "currency": "MYR",
                            "currencyPrefix": "RM"
                        },
                        "finalPrice": {
                            "value": 112.00,
                            "currency": "MYR"
                        },
                        "discount": {
                            "amountOff": 6.00,
                            "percentOff": 5.08
                        }
                    }
                },
                "breadcrumb": [
                    {
                        "id": 60303,
                        "level": 2,
                        "name": "Festive Hamper",
                        "urlKey": "festive-hamper"
                    }
                ],
                "links": {
                    "category": {
                        "id": 60282,
                        "name": "CNY 2023"
                    },
                    "brand": {
                        "id": "11871",
                        "name": "G+G"
                    }
                },
                "promotions": [
                    {
                        "offerText": "Special discounted price",
                        "specialFromDate": "2025-12-31 17:00:00",
                        "specialToDate": "2026-02-14 17:00:00",
                        "specialPrice": 112.00
                    }
                ],
                "mediaGallery": [
                    {
                        "url": "https://publish-p35803-e190640.adobeaemcloud.com/.../75199238_21766739546.jpg"
                    }
                ]
            }
        ]
    }
}
```

### 5. **Categories API**

#### **Get Category Tree**
```
GET https://api-o2o.lotuss.com.my/lotuss-mobile-bff/product/v1/categories/4?websiteCode=malaysia_hy
```

#### **Response Structure**
```json
{
    "status": {"code": 200, "message": "success"},
    "data": {
        "id": 4,
        "level": 1,
        "name": "Hyper",
        "children": [
            {
                "id": 61116,
                "level": 2,
                "name": "CNY 2026",
                "urlKey": "cny-2026",
                "children": [
                    {
                        "id": 61119,
                        "level": 3,
                        "name": "Grocery",
                        "urlKey": "grocery"
                    }
                ]
            },
            {
                "id": 6003,
                "level": 2,
                "name": "Baby",
                "urlKey": "baby"
            }
        ]
    }
}
```

### 6. **Scraping Strategy**

#### **Step 1: Fetch Category Tree**
```python
import requests
import urllib.parse

headers = {
    'key': 'SeiRQmEDnaZXOlpfKhCjV4Bo2y6vAcW99QKmzifsgP2uCMN7wF3ahRXex84kH6qUVIWoY5Dp0GEljdAvS1JytOZcLbnBTr',
    'channel': 'web',
    'version': '2.3.8',
    'accept': 'application/json',
    'user-agent': 'Mozilla/5.0 ...',
    'referer': 'https://www.lotuss.com.my/'
}

# Get all categories
response = requests.get(
    'https://api-o2o.lotuss.com.my/lotuss-mobile-bff/product/v1/categories/4',
    params={'websiteCode': 'malaysia_hy'},
    headers=headers
)
categories = response.json()['data']
```

#### **Step 2: Iterate Through Categories**
```python
def get_all_category_ids(category_tree, category_ids=[]):
    """Recursively extract all category IDs"""
    category_ids.append(category_tree['id'])
    for child in category_tree.get('children', []):
        get_all_category_ids(child, category_ids)
    return category_ids
```

#### **Step 3: Paginate Through Products**
```python
def scrape_category(category_id):
    products = []
    offset = 0
    limit = 99  # Max items per page
    
    while True:
        query = {
            "offset": offset,
            "limit": limit,
            "filter": {"categoryId": [str(category_id)]},
            "websiteCode": "malaysia_hy"
        }
        
        url = 'https://api-o2o.lotuss.com.my/lotuss-mobile-bff/product/v2/products'
        params = {'q': json.dumps(query)}
        
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        products.extend(data['data']['products'])
        
        # Check if more pages exist
        if offset + limit >= data['meta']['total']:
            break
            
        offset += limit
        time.sleep(1)  # Rate limiting
        
    return products
```

#### **Step 4: Extract Product Data**
```python
def extract_product_data(product):
    return {
        'item_name': product['name'],
        'category': product['breadcrumb'][-1]['name'] if product['breadcrumb'] else 'Unknown',
        'price': product['priceRange']['minimumPrice']['finalPrice']['value'],
        'original_price': product['priceRange']['minimumPrice']['regularPrice']['value'],
        'brand': product['links']['brand']['name'] if 'brand' in product['links'] else None,
        'sku': product['sku'],
        'stock_status': product['stockStatus'],
        'unit': product['unitOfWeight'],
        'weight_per_piece': product['weightPerPiece'],
        'image_url': product['mediaGallery'][0]['url'] if product['mediaGallery'] else None,
        'promotion': product['promotions'][0]['offerText'] if product['promotions'] else None,
        'special_price': product['promotions'][0]['specialPrice'] if product['promotions'] else None,
        'store_name': 'Lotus Malaysia',
        'scrape_date': datetime.now().isoformat()
    }
```

### 7. **Advantages**
✅ **Clean JSON API** - No HTML parsing needed  
✅ **Rich product data** - Includes brand, category, promotions, stock  
✅ **Pagination support** - Can fetch all products systematically  
✅ **Category hierarchy** - Easy to organize products  
✅ **Image URLs** - Direct links to product images  
✅ **No authentication** - Static API key works  

### 8. **Considerations**
⚠️ **Rate Limiting**: Add delays (1-2 seconds) between requests  
⚠️ **API Key Rotation**: Key might change - monitor for 401/403 errors  
⚠️ **Data Volume**: 348+ products per category × many categories  
⚠️ **Currency**: All prices in MYR (Malaysian Ringgit)  

### 9. **Example Implementation**

See `scrapers/lotus.py` (to be created) for full implementation following the JayaGrocer/Mydin pattern:

```python
class LotusScraper:
    BASE_URL = 'https://api-o2o.lotuss.com.my/lotuss-mobile-bff'
    
    def scrape(self, **kwargs):
        # 1. Fetch categories
        # 2. For each category, fetch products with pagination
        # 3. Transform to standard format
        # 4. Return list of products
```

### 10. **Comparison to Other Scrapers**

| Feature | Lotus | JayaGrocer | Mydin |
|---------|-------|------------|-------|
| Data Format | JSON API | GraphQL | REST API |
| Authentication | Static Key | None | None |
| Pagination | Offset/Limit | Cursor | Page Number |
| Product Data Quality | Excellent | Excellent | Good |
| Brand Information | ✅ Yes | ✅ Yes | ✅ Yes |
| Category Hierarchy | ✅ Deep (4 levels) | ✅ Yes | ✅ Yes |
| Stock Status | ✅ Yes | ❌ No | ❌ No |
| Promotion Details | ✅ Yes (dates, discounts) | ✅ Yes | ⚠️ Limited |

### 11. **Next Steps**

1. **Create scraper class** in `retail-etl/scrapers/lotus.py`
2. **Add to settings.py** scraper configuration
3. **Test with small category** to validate data format
4. **Run full scrape** for all categories
5. **Monitor for API changes** (check headers, response format)

### 12. **Sample Category IDs**
- **CNY 2026**: 61116 (348 products)
- **Grocery**: 61119
- **Hampers**: 61122
- **Cookies**: 61125
- **Drinks**: 61128
- **Fresh**: 61131
- **Baby**: 6003
- **AV & Tech**: 5976
- **Beverages**: 9405

### 13. **Estimated Product Count**
Based on category tree analysis: **10,000+ products** across all categories
