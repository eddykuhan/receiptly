# Quick Start Guide

## Why No Data Was Scraped?

The base `scraper.py` contains **template code** that needs customization for each website. Web scraping requires:

1. Inspecting the actual HTML structure of each website
2. Finding the correct CSS selectors
3. Handling different page layouts
4. Dealing with JavaScript-rendered content

This is time-consuming and fragile (breaks when websites change).

## ✅ **Recommended Solution: Google Places API**

### Step 1: Get API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **"Places API (New)"**
4. Go to **Credentials** → Create **API Key**
5. Copy your API key

### Step 2: Set Environment Variable

```bash
export GOOGLE_PLACES_API_KEY='your-api-key-here'
```

### Step 3: Run the Script

```bash
cd /Users/kuhan/Projects/receiptly/store-scraper
source venv/bin/activate
python quick_start.py
```

### Alternative: Hardcode API Key (for testing)

Edit `quick_start.py` and uncomment line 80:

```python
os.environ['GOOGLE_PLACES_API_KEY'] = 'your-key-here'
```

## 📊 **What You'll Get**

The script will fetch and save:

```json
{
  "store_name": "Jaya Grocer",
  "branch_name": "Jaya Grocer Gurney Paragon",
  "address": "Lot LG 26, 26A & 27, LG Floor, Gurney Paragon Mall, 163-D, Persiaran Gurney, 10250 George Town, Penang",
  "latitude": 5.438392,
  "longitude": 100.310181,
  "phone": "04-291 9883",
  "rating": 4.2,
  "total_ratings": 1234
}
```

## 💰 **Pricing**

- **Free tier**: 28,000 requests/month
- **Cost**: $0 for most personal use
- **Each search**: Counts as 1 request

## 🔧 **Option 2: Web Scraping (Advanced)**

If you want to scrape websites directly, you need to:

1. **Inspect the website** using browser DevTools
2. **Find CSS selectors** for store data
3. **Update the scraper class** with correct selectors

Example for a hypothetical website:

```python
class MyStoreScraper(StoreScraper):
    def scrape(self):
        response = self.session.get(f"{self.base_url}/locations")
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find actual selectors by inspecting the HTML
        stores = soup.find_all('div', class_='store-card')
        
        for store in stores:
            name = store.find('h2', class_='name').text
            address = store.find('p', class_='address').text
            # ... etc
```

## 🎯 **Recommendation**

**Use Google Places API** - it's:
- ✅ More reliable
- ✅ Includes GPS coordinates
- ✅ No maintenance needed
- ✅ Official and legal
- ✅ Free for reasonable use

Web scraping is only worth it if:
- You need data Google doesn't have
- You're scraping your own website
- You have specific requirements

## 📞 **Need Help?**

Run the quick start script and it will guide you through the setup!
