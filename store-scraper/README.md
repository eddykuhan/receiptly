# Store Location Scraper

A web scraper to extract store locations from Malaysian retailer websites for use with the Receiptly OCR system.

## Features

- 🏪 **Multi-Store Support**: Scrape locations from Jaya Grocer, Mydin, Lotus's, and more
- 📍 **Google Places Integration**: Alternative method using Google Places API
- 💾 **Multiple Export Formats**: Save data as JSON or CSV
- 🔧 **Extensible**: Easy to add new store scrapers

## Installation

```bash
cd store-scraper
pip install -r requirements.txt
```

## Usage

### Basic Scraping

```bash
python scraper.py
```

### Using Google Places API (Recommended)

The Google Places API provides more reliable and accurate data than web scraping.

1. Get a Google Places API key from [Google Cloud Console](https://console.cloud.google.com/)
2. Update the `main()` function in `scraper.py`:

```python
google_api_key = "YOUR_API_KEY_HERE"
google_scraper = GooglePlacesScraper(google_api_key)
jaya_locations = google_scraper.search_stores("Jaya Grocer", "Malaysia")
```

### Adding a New Store Scraper

Create a new class that inherits from `StoreScraper`:

```python
class NewStoreScraper(StoreScraper):
    def __init__(self):
        super().__init__("Store Name", "https://store-website.com")
    
    def scrape(self) -> List[StoreLocation]:
        locations = []
        # Implement scraping logic
        return locations
```

## Data Structure

Each store location contains:

```python
{
    "store_name": "Jaya Grocer",
    "branch_name": "Gurney Paragon",
    "address": "Lot LG 26, 26A & 27, LG Floor, Gurney Paragon Mall",
    "city": "Georgetown",
    "state": "Penang",
    "postal_code": "10250",
    "phone": "04-291 9883",
    "latitude": 5.4384,
    "longitude": 100.3102,
    "source_url": "https://..."
}
```

## Output Files

Scraped data is saved to the `data/` directory:

- `jaya_grocer_locations.json` - Jaya Grocer locations
- `mydin_locations.json` - Mydin locations
- `lotuss_locations.json` - Lotus's locations
- `*.csv` - CSV versions of the data

## Integration with Receiptly

The scraped location data can be used to:

1. **Validate OCR Results**: Match extracted addresses against known locations
2. **Auto-Complete Addresses**: Fill in missing address details
3. **Geocoding**: Convert addresses to GPS coordinates for map display
4. **Store Matching**: Improve fuzzy matching accuracy

### Example Integration

```python
# Load scraped locations
with open('data/jaya_grocer_locations.json', 'r') as f:
    known_locations = json.load(f)

# Match OCR result against known locations
def find_closest_location(ocr_address, known_locations):
    # Implement fuzzy matching logic
    pass
```

## Notes

### Web Scraping Considerations

- **Respect robots.txt**: Always check the website's robots.txt file
- **Rate Limiting**: Add delays between requests to avoid overloading servers
- **Terms of Service**: Ensure scraping complies with the website's ToS
- **Maintenance**: Website structures change; scrapers may need updates

### Google Places API

**Pros:**
- More reliable and accurate
- Includes GPS coordinates
- No website structure changes to worry about
- Officially supported

**Cons:**
- Requires API key
- Has usage limits (free tier: 28,000 requests/month)
- Costs money beyond free tier

## Troubleshooting

### Scraper Returns No Results

1. Check if the website structure has changed
2. Inspect the HTML using browser dev tools
3. Update CSS selectors in the scraper class
4. Consider using Google Places API instead

### Import Errors

```bash
pip install -r requirements.txt
```

### Rate Limiting

Add delays between requests:

```python
import time
time.sleep(1)  # Wait 1 second between requests
```

## Future Improvements

- [ ] Add more Malaysian retailers (AEON, Giant, Village Grocer)
- [ ] Implement retry logic for failed requests
- [ ] Add proxy support for large-scale scraping
- [ ] Create a database to store historical location data
- [ ] Add geocoding for addresses without coordinates
- [ ] Implement change detection (notify when stores open/close)

## License

This scraper is for educational and personal use only. Always respect website terms of service and robots.txt files.
