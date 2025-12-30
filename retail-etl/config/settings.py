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
from scrapers.aeon import AeonScraper

# Scraper configurations
SCRAPERS = [
    {
        'scraper_class': JayaGrocerScraper,
        'store_url': 'https://jggp.jayagrocer.com',
        'pricing_zone_id': 'JG_PENANG'
    },
    {
        'scraper_class': MydinScraper,
        'store_url': 'https://mydin.my/category/all-products',
        'max_pages': 10,
        'pricing_zone_id': 'MYDIN_NATIONAL'
    },
    # {
    #     'scraper_class': LotusScraper,
    #     'store_url': 'https://www.lotuss.com.my/en/browse/all-products',
    #     'max_pages': 5
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

# Logging
LOG_DIR = os.getenv('LOG_DIR', '/var/log/receiptly')
LOG_FILE = os.path.join(LOG_DIR, 'etl.log')
