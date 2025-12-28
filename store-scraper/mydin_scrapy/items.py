import scrapy


class MydinProductItem(scrapy.Item):
    """
    Scrapy Item for MYDIN products.
    Compatible with PurchaseAnalyticsGold schema.
    """
    # Item details
    item_name = scrapy.Field()
    canonical_name = scrapy.Field()
    unit_price = scrapy.Field()
    
    # Store context
    store_name = scrapy.Field()
    store_address = scrapy.Field()
    latitude = scrapy.Field()
    longitude = scrapy.Field()
    
    # Product metadata
    sku = scrapy.Field()
    category = scrapy.Field()
    stock_status = scrapy.Field()
    available = scrapy.Field()
    image_url = scrapy.Field()
    
    # Scraping metadata
    scraped_at = scrapy.Field()
    source = scrapy.Field()
