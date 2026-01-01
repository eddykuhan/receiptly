#!/usr/bin/env python3
"""
Standalone script to run Lotus scraper and save raw data to JSON.
Usage: python run_lotus_scraper.py
"""
import json
import os
from datetime import datetime
from scrapers.lotus import LotusScraper

# Create data/raw directory if it doesn't exist
RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'raw')
os.makedirs(RAW_DATA_DIR, exist_ok=True)

def main():
    print("Starting Lotus scraper...")
    
    # Initialize scraper (no max_products limit = scrape all)
    scraper = LotusScraper()
    
    # Run scraper
    print("Scraping products from Lotus API...")
    products = scraper.run()
    
    print(f"✓ Scraped {len(products)} products")
    
    # Save to JSON file
    filename = f"lotus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(RAW_DATA_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved to: {filepath}")
    
    # Show summary
    print("\nSummary:")
    print(f"  Total products: {len(products)}")
    
    if products:
        prices = [p['unit_price'] for p in products]
        print(f"  Price range: RM {min(prices):.2f} - RM {max(prices):.2f}")
        
        categories = {}
        for p in products:
            cat = p.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"  Categories: {len(categories)}")
        print("\n  Top 5 categories:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {cat}: {count} products")

if __name__ == "__main__":
    main()
