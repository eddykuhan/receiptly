"""
Configuration settings for the ETL pipeline.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'receiptly'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
}

# Import scrapers
from scrapers.jaya_grocer import JayaGrocerScraper
from scrapers.mydin import MydinScraper
from scrapers.lotus import LotusScraper
from scrapers.village_grocer import VillageGrocerScraper
from scrapers.village_grocer_location import VillageGrocerLocationScraper
# from scrapers.aeon import AeonScraper

# Scraper configurations
SCRAPERS = [
    {
        'scraper_class': JayaGrocerScraper,
        'store_url': 'https://jggp.jayagrocer.com',
        'pricing_zone_id': 'JG_PENANG'
    },
    {
        'scraper_class': MydinScraper,
        'store_url': 'https://myapi.mydin.my/magento/products',
        'max_pages': 100,
        'pricing_zone_id': 'MYDIN_NATIONAL',
        'target_categories': [1222, 1513]
    },
    {
        'scraper_class': LotusScraper,
        'store_url': 'https://api-o2o.lotuss.com.my/lotuss-mobile-bff',
        'max_pages': 100,
        'pricing_zone_id': 'LOTUSS_NATIONAL',
        # Lotus scraper uses GROCERY_CATEGORIES defined in scraper class (25 categories)
    },
    {
        'scraper_class': VillageGrocerScraper,
        'store_url': 'https://www.bites.com.my',  # Main catalog (Shopify API)
        'pricing_zone_id': 'VILLAGE_GROCER_MY',
        'max_products': None,  # None = scrape all products
        'collections': None,  # None = use default collections from VillageGrocerScraperConfig
    },
    # {
    #     'scraper_class': VillageGrocerLocationScraper,
    #     'location': 'Mont Kiara',
    #     'pricing_zone_id': 'VILLAGE_GROCER_MONT_KIARA_MY',
    #     'max_products': None,  # None = scrape all products
    #     'collections': None,  # None = use default location collections
    # },
    # {
    #     'scraper_class': AeonScraper,
    #     'store_url': 'https://myaeon.com.my/view-all-products',
    #     'max_pages': 5
    # }
]

# Canonicalization settings
SIMILARITY_THRESHOLD = 0.90  # Minimum similarity score for embedding match

# Scheduler settings
SCHEDULE_HOUR = 2  # Run at 2 AM
SCHEDULE_MINUTE = 0

# Raw data storage
RAW_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')
USE_LOCAL_CACHE = os.getenv('USE_LOCAL_CACHE', 'false').lower() == 'true'
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'etl.log')

# Checkpoint storage for resume capability
CHECKPOINT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'checkpoints')
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, 'etl_checkpoint.json')

# Ensure directories exist
for d in [LOG_DIR, RAW_DATA_DIR, CHECKPOINT_DIR]:
    if not os.path.exists(d):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            if d == LOG_DIR:
                LOG_DIR = './logs'
                os.makedirs(LOG_DIR, exist_ok=True)
                LOG_FILE = os.path.join(LOG_DIR, 'etl.log')

