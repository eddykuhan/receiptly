import re
from datetime import datetime
from itemadapter import ItemAdapter


class MydinProductPipeline:
    """
    Pipeline to process MYDIN product items.
    - Normalizes product names
    - Validates required fields
    - Filters out invalid products
    """
    
    def __init__(self):
        self.items_processed = 0
        self.items_dropped = 0
    
    def normalize_name(self, name: str) -> str:
        """Normalize product name for canonical matching."""
        if not name:
            return ""
        name = re.sub(r'\s+', ' ', name.strip())
        return name
    
    def process_item(self, item, spider):
        """Process and validate each item."""
        adapter = ItemAdapter(item)
        
        # Validate required fields
        if not adapter.get('item_name'):
            self.items_dropped += 1
            spider.logger.warning(f"Dropped item without name: {item}")
            return None
        
        # Normalize canonical name
        if adapter.get('item_name'):
            adapter['canonical_name'] = self.normalize_name(adapter['item_name'])
        
        # Ensure unit_price is float
        if adapter.get('unit_price'):
            try:
                adapter['unit_price'] = float(adapter['unit_price'])
            except (ValueError, TypeError):
                adapter['unit_price'] = 0.0
        
        # Add timestamp if not present
        if not adapter.get('scraped_at'):
            adapter['scraped_at'] = datetime.utcnow().isoformat()
        
        # Add source if not present
        if not adapter.get('source'):
            adapter['source'] = 'mydin_scrapy_nuxt_data'
        
        self.items_processed += 1
        return item
    
    def close_spider(self, spider):
        """Log statistics when spider closes."""
        spider.logger.info(f"Pipeline processed {self.items_processed} items")
        spider.logger.info(f"Pipeline dropped {self.items_dropped} items")
