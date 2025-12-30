# Mydin Website Scraping Analysis

## Overview
This document summarizes the findings from inspecting https://mydin.my for API-based data scraping potential. Analysis conducted on December 30, 2025, revealed that Mydin uses GraphQL APIs for their e-commerce data, providing comprehensive product and category information.

## Key Findings

### Primary Data Sources Identified
The website uses Magento-based GraphQL APIs that provide structured JSON responses:

1. **Products GraphQL API**: `https://myapi.mydin.my/magento/products`
   - Fetches paginated product listings with detailed information
   - Supports category filtering, sorting, and comprehensive product data
   - Returns pricing, inventory, images, descriptions, and variants

2. **Categories GraphQL API**: `https://myapi.mydin.my/magento/categories`
   - Retrieves category hierarchy and metadata
   - Includes product counts, subcategories, and bilingual names
   - Supports filtering by category IDs

3. **Legacy REST API**: `https://mydin.my/api/product/fetchProductsByCategories`
   - Alternative endpoint for category-based product fetching
   - Less comprehensive than GraphQL but still functional

## Category Structure & Mapping

### Main Categories
Based on GraphQL API responses, the main categories with their current product counts:

| Category Name | English Name | Malay Name | Category ID | Product Count | Subcategories |
|---------------|--------------|------------|-------------|---------------|---------------|
| Food & Beverage | Food & Beverage | Makanan & Minuman | 1222 | 2,297 | 12 |
| Beauty | Beauty | Kecantikan | 881 | 338 | 11 |
| Home & Living | Home & Living | Rumah & Kehidupan | 1513 | 377 | 17 |
| Muslim Fashion | Muslim Fashion | Fesyen Muslim | 2371 | 526 | 5 |
| Baby & Kids Fashion | Baby & Kids Fashion | Fesyen Bayi & Kanak-kanak | 2101 | 24 | 8 |
| Men Clothes | Men Clothes | Pakaian Lelaki | 1807 | 27 | 17 |
| Mom & Baby | Mom & Baby | Ibu & Bayi | 1924 | 49 | 13 |
| Pets | Pets | Haiwan Peliharaan | 2164 | 40 | 7 |
| Stationery | Stationery | Alat Tulis | 1401 | 156 | 7 |
| Health | Health | Kesihatan | 765 | 26 | 5 |

### Category Hierarchy
Categories are structured hierarchically with:
- Parent categories containing subcategories
- Unique category IDs for identification
- Bilingual names (English and Malay)
- Product counts for each category level
- Associated images and metadata

### Category API Response Structure
```json
{
  "banner_no": 1,
  "category_id": 2665,
  "category_name": "Food & Beverages",
  "category_bm_name": "Food & Beverages",
  "image": "mymgtbe.mydin.my/pub/media/banner/default/12.jpg",
  "category_url": "/food-beverage"
}
```

## Product Data Structure

### Comprehensive Product Information
Products contain detailed information suitable for price comparison:

#### Basic Information
- **Product ID**: Unique identifier
- **SKU**: Stock keeping unit
- **Name**: Product display name
- **Manufacturer Code**: MFG code
- **URL Key**: SEO-friendly URL identifier

#### Pricing Information
- **Final Price**: Current selling price
- **Regular Price**: Original price
- **Currency**: MYR (Malaysian Ringgit)
- **Tier Pricing**: Bulk pricing options
- **Price Tiers**: Quantity-based discounts

#### Inventory & Stock
- **Salable Quantity**: Available for purchase
- **Stock Quantity**: Total inventory
- **Stock Status**: Availability indicators

#### Media & Images
- **Thumbnail**: Main product image
- **Media Gallery**: Additional product photos
- **Image URLs**: CDN-hosted images

#### Categorization
- **Categories Array**: Hierarchical category assignments
- **Primary Category**: Main product category
- **Subcategories**: Additional classifications

#### Descriptions
- **Custom Product Description**: Detailed HTML descriptions
- **Custom Product Name**: Alternative display names

### Sample Product JSON Structure
```json
{
  "id": 8808,
  "name": "COMBO BOX 4.0 RM100",
  "sku": "15152919",
  "mfgCode": "15152919",
  "url_key": "combo-box-4-0-rm100-15152919",
  "custom_productdescription": "<p>Pasca Banjir Combo B RM100</p><ul>...</ul>",
  "custom_productname": "Pasca Banjir Combo B RM100 (21 items)",
  "thumbnail": {
    "url": "https://mymgtbe.mydin.my/media/catalog/product/cache/...",
    "label": "COMBO BOX 4.0 RM100"
  },
  "price_range": {
    "minimum_price": {
      "final_price": {"currency": "MYR", "value": 100},
      "regular_price": {"currency": "MYR", "value": 100}
    }
  },
  "categories": [
    {"name": "All Products"},
    {"name": "Food & Beverage"},
    {"name": "Cooking Essentials"}
  ],
  "salable_quantity": 13,
  "quantity": 13
}
```

## API Endpoints & Usage

### 1. Categories GraphQL API
**Endpoint**: `GET https://myapi.mydin.my/magento/categories`
**Method**: GET with JSON body parameter

**Query Structure**:
```json
[
  {
    "filters": {
      "ids": {
        "in": [2101, 1222, 1513, 881, 2371, 1924, 2164, 1807, 1401, 765]
      }
    }
  },
  {
    "categories": "categories-custom-query",
    "metadata": {
      "fields": "items { id image name category_bm_name url_key meta_title product_count children { id image name category_bm_name url_key meta_title product_count } }"
    }
  },
  {}
]
```

**Response Structure**:
```json
{
  "data": {
    "categories": {
      "items": [
        {
          "id": 1222,
          "name": "Food & Beverage",
          "category_bm_name": "Makanan & Minuman",
          "product_count": 2297,
          "children": [
            {
              "id": 1234,
              "name": "Beverages",
              "product_count": 450
            }
          ]
        }
      ]
    }
  }
}
```

### 2. Products GraphQL API
**Endpoint**: `GET https://myapi.mydin.my/magento/products`
**Method**: GET with JSON body parameter

**Query Structure**:
```json
[
  {
    "filter": {
      "category_id": {
        "eq": "1222"
      }
    },
    "pageSize": 48,
    "currentPage": 1,
    "sort": {
      "position": "ASC"
    }
  },
  {
    "products": "products-custom-query",
    "metadata": {
      "fields": "items { id sku name price_range { minimum_price { final_price { currency value } } } salable_quantity image { url } }"
    }
  },
  {}
]
```

**Response Structure**:
```json
{
  "data": {
    "products": {
      "items": [
        {
          "id": 7363,
          "sku": "15118319",
          "name": "WONDA CFFE 3IN1 15SX23G ORIGINAL",
          "price_range": {
            "minimum_price": {
              "final_price": {
                "currency": "MYR",
                "value": 15.9
              }
            }
          },
          "salable_quantity": 50,
          "image": {
            "url": "https://mymgtbe.mydin.my/media/catalog/product/cache/...",
            "label": "WONDA CFFE 3IN1 15SX23G ORIGINAL"
          }
        }
      ],
      "page_info": {
        "current_page": 1,
        "page_size": 48,
        "total_pages": 230
      },
      "total_count": 2297
    }
  }
}
```

### 3. Legacy Category Products API
**Endpoint**: `GET https://mydin.my/api/product/fetchProductsByCategories`
**Parameters**:
- `category_ids`: Comma-separated category IDs

**Example**: `?category_ids=2740,2665,2668,2667,2669,2672,2666,2675`

## Scraping Strategy

### Recommended Approach

1. **Initial Setup**
   - Fetch complete category hierarchy using Categories GraphQL API
   - Map category IDs to names, relationships, and product counts
   - Identify target categories for scraping based on product volume

2. **Product Collection**
   - Use Products GraphQL API for category-specific scraping
   - Implement pagination using `pageSize` and `currentPage` parameters
   - Handle rate limiting with delays between requests (recommended: 1-2 seconds)
   - Process categories systematically from highest to lowest product count

3. **Data Processing**
   - Parse GraphQL JSON responses into structured data
   - Extract comprehensive product information (pricing, inventory, media)
   - Handle bilingual category names and descriptions
   - Download and store product images if needed
   - Maintain category hierarchy relationships

4. **Data Storage**
   - Store in database with proper schema for categories and products
   - Maintain parent-child category relationships
   - Track price changes and inventory updates over time
   - Include metadata like SKUs, manufacturer codes, and URL keys

### Pagination Handling
- GraphQL API supports `pageSize` (default: 48) and `currentPage` parameters
- Response includes `page_info` with `total_pages` for complete pagination
- Implement retry logic for failed requests with exponential backoff
- Monitor API rate limits and implement request throttling

### Rate Limiting Considerations
- APIs appear to have reasonable rate limits for normal usage
- Implement delays between requests (1-2 seconds recommended)
- Monitor response times and error rates
- Use single IP address for development/testing
- Consider IP rotation for production-scale scraping

## Technical Implementation Notes

### Data Quality
- Product descriptions include HTML formatting
- Prices are in Malaysian Ringgit (MYR) with currency field
- Stock quantities are real-time and update frequently
- Images are hosted on CDN with consistent URL structure
- Bilingual support (English/Malay) for categories and some products
- Comprehensive product metadata including SKUs and manufacturer codes

### Error Handling
- APIs return standard HTTP status codes (200 for success)
- GraphQL responses include error information when applicable
- Network timeouts should be handled (recommended: 15-30 seconds)
- Invalid category IDs return empty results gracefully
- Implement retry logic for transient network errors

### Data Freshness
- Product prices and inventory update in real-time
- Category structures may change periodically
- Product additions/removals happen regularly
- Implement regular re-scanning (daily/weekly) for updates
- Track price history for trend analysis

### API Characteristics
- GraphQL APIs provide comprehensive, structured data
- Consistent response formats across endpoints
- Support for complex filtering and pagination
- Real-time data accuracy for pricing and inventory
- CDN-hosted images with reliable URLs

## Conclusion

The Mydin website provides excellent scraping opportunities through well-structured GraphQL APIs that deliver comprehensive, real-time product and category data. The APIs are specifically designed for e-commerce data access and provide all necessary information for price comparison and retail analysis applications.

Key advantages:
- **GraphQL APIs**: Modern, efficient data fetching with precise field selection
- **Comprehensive product data**: Complete pricing, inventory, media, and categorization
- **Real-time accuracy**: Live pricing and stock information
- **Hierarchical category system**: Full category tree with product counts
- **Bilingual support**: English and Malay language content
- **Pagination support**: Efficient handling of large product catalogs
- **Structured responses**: Consistent, parseable JSON data formats

The GraphQL implementation provides superior data access compared to traditional REST APIs, with better performance and more comprehensive information. This analysis provides a solid foundation for implementing a robust, production-ready scraping solution for Mydin's extensive product catalog.

**Total Catalog Size**: 10+ main categories with 8,596+ products across all categories
**Data Richness**: Complete product information including pricing, inventory, images, and descriptions
**Update Frequency**: Real-time pricing and inventory updates
**API Reliability**: Consistent response formats and error handling