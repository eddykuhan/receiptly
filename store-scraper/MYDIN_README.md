# Mydin Web Scraper

A Python web scraper for extracting product and price data from Mydin's online store using Selenium and Nuxt.js data extraction.

## Features

- **Nuxt.js Data Extraction**: Extracts structured JSON from `window.__NUXT__.data`
- **Selenium Automation**: Headless Chrome for JavaScript rendering
- **Pagination Support**: Automatically navigates through all product pages
- **Gold Layer Compatible**: Output format matches PurchaseAnalyticsGold schema
- **Comprehensive Metadata**: Includes SKU, stock status, categories, and images

## Installation

```bash
cd store-scraper
pip install -r requirements.txt
```

**Note**: This will install Selenium and automatically download ChromeDriver via webdriver-manager.

## Usage

### Basic Scraping

```bash
python mydin_scraper.py
```

By default, this scrapes the first 5 pages for testing. To scrape all products (~181 pages):

```python
# Edit mydin_scraper.py, line 241:
products = scraper.scrape_all_products(max_pages=None, delay=2.0)
```

### Output Format

The scraper generates `data/mydin_products.json`:

```json
{
  "store_name": "Mydin",
  "store_address": "Malaysia",
  "total_products": 240,
  "scraped_at": "2025-12-27T16:45:00.000Z",
  "products": [
    {
      "item_name": "Product Name",
      "canonical_name": "Product Name",
      "unit_price": 12.50,
      "store_name": "Mydin",
      "store_address": "Malaysia",
      "latitude": null,
      "longitude": null,
      "sku": "SKU123",
      "category": "Category Name",
      "stock_status": "in_stock",
      "available": true,
      "image_url": "https://...",
      "scraped_at": "2025-12-27T16:45:00.000Z",
      "source": "mydin_nuxt_data"
    }
  ]
}
```

## Customization

### Adjust Pages to Scrape

```python
# Scrape first 10 pages
products = scraper.scrape_all_products(max_pages=10, delay=2.0)

# Scrape all pages (181 total)
products = scraper.scrape_all_products(max_pages=None, delay=2.0)
```

### Change Rate Limiting

```python
# Increase delay to 3 seconds
products = scraper.scrape_all_products(max_pages=5, delay=3.0)
```

### Custom Output Location

```python
scraper.save_to_json(products, filename="custom_output.json")
```

## Technical Details

### How It Works

1. **Selenium Setup**: Initializes headless Chrome with webdriver-manager
2. **Page Navigation**: Navigates to each page with `?page=N` parameter
3. **Wait for Load**: Waits for page to fully render (15s timeout)
4. **Remove Popups**: Dismisses newsletter overlays using JavaScript
5. **Extract Data**: Executes `return window.__NUXT__;` to get structured data
6. **Parse Products**: Recursively searches NUXT data for product objects
7. **Transform**: Converts to gold layer compatible format
8. **Save**: Outputs to JSON file

### Data Extraction Strategy

Mydin uses Nuxt.js which pre-loads product data in `window.__NUXT__.data`. This contains:
- Product names, SKUs, prices
- Stock status and availability
- Categories and images
- Full metadata

This approach is more reliable than HTML parsing as the data structure is consistent.

## Notes

- **Headless Mode**: Runs in headless Chrome (no visible browser window)
- **Rate Limiting**: Default 2-second delay between pages to avoid overwhelming server
- **Multiple Locations**: Mydin has multiple branches - this scraper doesn't specify a particular location
- **Total Products**: Approximately 8,656 products across 181 pages (48 per page)

## Troubleshooting

**ChromeDriver issues**: webdriver-manager should auto-download, but if it fails:
```bash
pip install --upgrade webdriver-manager
```

**Timeout errors**: Increase wait time in `extract_nuxt_data()`:
```python
WebDriverWait(self.driver, 30).until(...)  # Increase from 15 to 30
```

**No products extracted**: The NUXT data structure may have changed. Check browser console for `window.__NUXT__` structure.

## Scrapy-Based Scraper (Recommended)

A more robust implementation using the Scrapy framework with integrated Selenium for JavaScript rendering.

### Installation

```bash
cd store-scraper
pip install -r requirements.txt
```

This will install Scrapy, scrapy-selenium, and all other dependencies.

### Usage

**Basic scraping (2 pages for testing):**

```bash
python run_mydin_scrapy.py --max-pages 2
```

**Scrape all pages:**

```bash
python run_mydin_scrapy.py --max-pages 0
```

**Custom output file:**

```bash
python run_mydin_scrapy.py --max-pages 5 --output data/custom_output.json
```

### Features

- **Scrapy Framework**: Better performance with concurrent requests, automatic retry logic, and built-in stats
- **Selenium Integration**: Handles JavaScript rendering to extract `window.__NUXT__` data
- **Pipeline Processing**: Automatic data validation, normalization, and filtering
- **AutoThrottle**: Adaptive rate limiting to avoid overwhelming the server
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **JSON Export**: Clean, structured output compatible with gold layer schema

### Output Format

Same as the Selenium version - produces JSON with product details compatible with PurchaseAnalyticsGold schema.

### Advantages Over Selenium-Only Version

| Feature | Selenium-Only | Scrapy + Selenium |
|---------|---------------|-------------------|
| **Architecture** | Monolithic script | Modular (spiders, items, pipelines) |
| **Error Handling** | Manual | Built-in retry logic |
| **Rate Limiting** | Fixed delay | Adaptive AutoThrottle |
| **Data Validation** | In scraper | Separate pipeline |
| **Logging** | Basic print statements | Comprehensive Scrapy logging |
| **Extensibility** | Requires refactoring | Easy to add middleware/pipelines |
| **Stats Collection** | Manual | Automatic |

## Comparison with Jaya Grocer Scraper


| Feature | Jaya Grocer | Mydin |
|---------|-------------|-------|
| **Method** | Shopify JSON API | Selenium + Nuxt data |
| **Speed** | Fast (direct API) | Slower (browser rendering) |
| **Dependencies** | requests only | selenium, webdriver-manager |
| **Reliability** | Very high | High |
| **Maintenance** | Low | Medium |

## Next Steps

- ✅ **Scrapy Implementation**: Migrated to Scrapy framework for better performance and maintainability
- Verify NUXT data structure extraction (may need refinement for actual product data)
- Add support for specific Mydin branch locations
- Implement GraphQL API approach for faster scraping (if available)
- Schedule regular scrapes for price tracking
