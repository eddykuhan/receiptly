"""
Base scraper abstract class for retail chain scrapers.

All scrapers must inherit from this class and implement the scrape() method.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime


class BaseScraper(ABC):
    """Abstract base class for retail chain scrapers."""
    
    def __init__(self, pricing_zone_id: str, store_name: str, store_address: str, latitude: Optional[float] = None, longitude: Optional[float] = None):
        """
        Initialize the scraper with store metadata.
        
        Args:
            pricing_zone_id: Unique ID for the pricing zone (e.g. "MYDIN_NATIONAL")
            store_name: Human readable name
            store_address: General address/region
            latitude: (Deprecated) validation location
            longitude: (Deprecated) validation location
        """
        self.pricing_zone_id = pricing_zone_id
        self.store_name = store_name
        self.store_address = store_address
        self.latitude = latitude
        self.longitude = longitude
    
    @abstractmethod
    def scrape(self) -> List[Dict]:
        """
        Scrape products from the retail chain.
        
        Returns:
            List of product dictionaries with the following schema:
            {
                'item_name': str,           # Raw product name
                'unit_price': float,        # Price in MYR
                'category': str,            # Product category
                'brand': str,               # Brand name (optional)
                'sku': str,                 # SKU/product code (optional)
                'available': bool,          # Stock availability
                'scraped_at': str,          # ISO timestamp
                'source': str               # Scraper identifier
            }
        """
        pass
    
    def clean(self, records: List[Dict]) -> List[Dict]:
        """
        Clean and validate scraped records.
        
        Args:
            records: Raw scraped records
            
        Returns:
            Cleaned and validated records with store metadata added
        """
        cleaned = []
        for record in records:
            # Add store metadata
            # Use PricingZoneId as StoreName for consistency with new schema
            record['store_name'] = self.pricing_zone_id
            record['pricing_zone_id'] = self.pricing_zone_id
            record['store_address'] = self.store_address
            
            # Scraped data represents a zone, so lat/long are None in purchase_analytics
            # Physical locations are now in the 'stores' table
            record['latitude'] = None 
            record['longitude'] = None
            
            # Validate required fields
            if not record.get('item_name') or not record.get('unit_price'):
                continue
            
            # Ensure price is float
            try:
                record['unit_price'] = float(record['unit_price'])
            except (ValueError, TypeError):
                continue
            
            # Set defaults
            record.setdefault('category', 'Unknown')
            record.setdefault('brand', '')
            record.setdefault('sku', '')
            record.setdefault('available', True)
            record.setdefault('scraped_at', datetime.utcnow().isoformat())
            
            cleaned.append(record)
        
        return cleaned
    
    def run(self) -> List[Dict]:
        """
        Execute the scraper and return cleaned records.
        
        Returns:
            Cleaned product records ready for transformation
        """
        print(f"Starting scrape: {self.store_name}")
        raw_records = self.scrape()
        cleaned_records = self.clean(raw_records)
        print(f"Scraped {len(cleaned_records)} products from {self.store_name}")
        return cleaned_records
