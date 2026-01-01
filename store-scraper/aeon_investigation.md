# AEON myAEON2go Investigation

## Site Structure

**Main Site:** https://aeonretail.com.my/ (corporate/marketing)
**E-commerce:** https://myaeon2go.com/ (online shopping)

## Protection
- DOME antibot protection (heavy)
- Likely client-side rendering with API calls

## Product URL Pattern
```
https://myaeon2go.com/product/{id}/{slug}
```

Examples:
- `https://myaeon2go.com/product/12/100-plus-original-isotonic-drink-28-24-4-x-325-ml`
- `https://myaeon2go.com/product/6806/dishwash-liquid-extra-nature-refill`
- `https://myaeon2go.com/product/12829/coho-salmon-steak-cut`

## Category/Listing Pages
- `/products/highlight/{id}/{slug}` - Featured/promotional listings
- `/m/deals-and-promotions` - Deals page
- `/brand/{id}/{name}` - Brand pages (TopValu, Wellness, Home Coordy, Daiso)

## Data Observed
Products show:
- Name
- Price (current + original for discounts)
- Product ID
- Image URLs (via thumbor CDN: `thumbor.asia-southeast1.aeon-my-prod.e.spresso.com`)
- Stock status ("ADD" button count)
- Unit pricing (e.g., "RM 1.03/each")

## ✅ API Discovery - No Antibot Required!

**Base API URL:** `https://myaeon2go.com/api/`

### Product Listing Endpoint
```
GET /api/web-slug-configs/data
```

**Query Parameters:**
- `limit` - Number of products to return (e.g., 4, 20, 100)
- `sort` - Sort order (e.g., "listPosition")
- `soft_category_gid` - Category ID (e.g., 1559 for "Pick of the Week")
- `moduleType` - Module type (e.g., "productListEntities")

**Example:**
```
https://myaeon2go.com/api/web-slug-configs/data?limit=4&sort=listPosition&soft_category_gid=1559&moduleType=productListEntities
```

### JSON Response Structure

```json
{
  "data": {
    "productListEntities": [
      {
        "type": 0,
        "variant": {
          "_id": "685c48a826b8ea09659b3ee5",
          "brandingText": "Daim",
          "nameText": "Bag",
          "extendedInfoText": "200 g",
          "gid": 56924,
          "slug": "daim-bag-200-g",
          "externalIds": [
            {"source": "AMY", "value": "12645183"}
          ],
          "images": [
            {
              "r512x400": "https://thumbor.asia-southeast1.aeon-my-prod.e.spresso.com/...",
              "original": "https://catalog-assets-asia-southeast1.aeon-my-prod.e.spresso.com/..."
            }
          ]
        },
        "inventory": [
          {
            "price": 14.99,
            "standardPrice": 19.9,
            "salePrice": 14.99,
            "salePercentage": 25,
            "availableCount": 164,
            "fulfillerLocationName": "myAEON2go Taman Maluri"
          }
        ],
        "product": {
          "categories": [
            {"name": "ALL", "path": "ALL"},
            {"name": "AEON_FRESH", "path": "ALL:AEON_FRESH"},
            {"name": "SNACKS", "path": "ALL:AEON_FRESH:SNACKS"},
            {"name": "CHOCOLATE_&_CANDY", "path": "ALL:AEON_FRESH:SNACKS:CHOCOLATE_&_CANDY"}
          ]
        },
        "sku": "12645183"
      }
    ],
    "cursor": "oTShNKEwwKChMA=="
  }
}
```

### Key Fields
- `variant.gid` - Product ID
- `variant.brandingText` - Brand name
- `variant.nameText` - Product name
- `variant.extendedInfoText` - Size/quantity (e.g., "200 g", "5 kg")
- `inventory[0].price` - Current price (RM)
- `inventory[0].standardPrice` - Original price
- `inventory[0].salePercentage` - Discount %
- `inventory[0].availableCount` - Stock quantity
- `sku` - SKU/barcode
- `product.categories` - Category hierarchy

### Category IDs (soft_category_gid)
Need to discover by browsing site:
- 1559 - "Pick of the Week"
- 1066 - "Featured Items"
- 928 - "Fresh Foods"
- 940 - "Ready to Eat"
- 1598 - "Electrical Appliances"

### Pagination
Uses cursor-based pagination:
- Response includes `"cursor": "oTShNKEwwKChMA=="`
- Pass cursor in next request to get more items

## Similar to
Built on **Boxed/Spresso platform** (common in SEA retail):
- Thumbor image CDN
- Similar URL patterns to other Boxed-powered sites
- "myboxed.com.my" references in assets
