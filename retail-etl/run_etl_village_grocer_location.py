#!/usr/bin/env python
"""
Run Village Grocer Location-Specific ETL (Mont Kiara)
Scrapes location-based pricing and inventory from vgo.bites.com.my

Usage:
    python run_etl_village_grocer_location.py                          # Full ETL pipeline
    python run_etl_village_grocer_location.py --collection fresh       # Single collection
    python run_etl_village_grocer_location.py --max 1000               # Limit products
    python run_etl_village_grocer_location.py --collection fresh --max 100
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.village_grocer_location import VillageGrocerLocationScraper
from config.settings import RAW_DATA_DIR

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'logs', 'etl.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def analyze_products(products):
    """Generate analytics summary for products."""
    if not products:
        return {}
    
    prices = [p.get('unit_price', 0) for p in products if p.get('unit_price')]
    categories = {}
    brands = {}
    
    for product in products:
        cat = product.get('category', 'Uncategorized')
        brand = product.get('brand', 'Unbranded')
        
        categories[cat] = categories.get(cat, 0) + 1
        brands[brand] = brands.get(brand, 0) + 1
    
    # Sort by count
    top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]
    top_brands = sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10]
    
    products_with_sku = sum(1 for p in products if p.get('sku'))
    
    return {
        'total_products': len(products),
        'price_range': {
            'min': min(prices) if prices else 0,
            'max': max(prices) if prices else 0,
            'avg': sum(prices) / len(prices) if prices else 0
        },
        'categories': {
            'total_unique': len(categories),
            'top_10': top_categories
        },
        'brands': {
            'total_unique': len(brands),
            'top_10': top_brands
        },
        'sku_coverage': {
            'with_sku': products_with_sku,
            'total': len(products),
            'coverage_pct': (products_with_sku / len(products) * 100) if products else 0
        }
    }


def save_products_to_json(products, location='mont-kiara'):
    """Save products to JSON file in data/raw/ folder."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"village_grocer_location_{location}_{timestamp}.json"
    filepath = os.path.join(RAW_DATA_DIR, filename)
    
    # Ensure directory exists
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    with open(filepath, 'w') as f:
        json.dump(products, f, indent=2, default=str)
    
    return filepath, filename


def main():
    parser = argparse.ArgumentParser(
        description="Run Village Grocer Location-Specific (Mont Kiara) scraper and save raw data",
        epilog="""
Standalone script to run Village Grocer location store scraper and save raw data to JSON.

Usage Examples:
    # Full ETL pipeline (all collections)
    python run_etl_village_grocer_location.py

    # Test with limited products (debug mode)
    python run_etl_village_grocer_location.py --max 100

    # Specific collection only
    python run_etl_village_grocer_location.py --collection fresh

    # Multiple collections with limit
    python run_etl_village_grocer_location.py --collection fresh fridge --max 500
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--collection',
        nargs='*',
        help='Specific collection(s) to scrape (e.g., fresh, groceries). Default: all collections'
    )
    parser.add_argument(
        '--max',
        type=int,
        dest='max_products',
        help='Maximum products to scrape (for testing)'
    )
    parser.add_argument(
        '--location',
        default='Mont Kiara',
        help='Store location name (default: Mont Kiara)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Build scraper kwargs
    kwargs = {
        'location': args.location,
        'max_products': args.max_products,
    }
    
    if args.collection:
        # Filter to only provided collections
        kwargs['collections'] = args.collection
    
    print("\n" + "="*70)
    print("VILLAGE GROCER LOCATION-SPECIFIC ETL (Mont Kiara)")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Location: {args.location}")
    if args.collection:
        print(f"  Collections: {', '.join(args.collection)}")
    else:
        print(f"  Collections: All (default)")
    if args.max_products:
        print(f"  Max products: {args.max_products}")
    print()
    
    try:
        logger.info(f"Starting Village Grocer location ETL: {args.location}")
        
        # Initialize and run scraper
        scraper = VillageGrocerLocationScraper(**kwargs)
        products = scraper.scrape()
        
        if not products:
            print("✗ Failed to scrape products")
            logger.error("No products scraped")
            return 1
        
        # Save to JSON
        filepath, filename = save_products_to_json(products, location='mont-kiara')
        print(f"✓ Scraped {len(products)} products")
        print(f"✓ Saved to: {filename}\n")
        
        # Get statistics
        stats = scraper.get_stats()
        analytics = analyze_products(products)
        
        # Display summary
        print("SUMMARY:")
        print(f"  Total products: {analytics['total_products']}")
        print(f"  Price range: RM {analytics['price_range']['min']:.2f} - RM {analytics['price_range']['max']:.2f}")
        print(f"  Average price: RM {analytics['price_range']['avg']:.2f}")
        print(f"  Categories: {analytics['categories']['total_unique']}")
        
        print(f"\n  Top categories:")
        for cat, count in analytics['categories']['top_10'][:5]:
            print(f"    - {cat}: {count} products")
        
        print(f"\n  Unique brands: {analytics['brands']['total_unique']}")
        print(f"  Top brands:")
        for brand, count in analytics['brands']['top_10'][:3]:
            print(f"    - {brand}: {count} products")
        
        print(f"\n  Products with SKU: {analytics['sku_coverage']['with_sku']}/{analytics['sku_coverage']['total']} ({analytics['sku_coverage']['coverage_pct']:.1f}%)")
        
        print(f"\nScraper Statistics:")
        print(f"  Collections processed: {stats['collections_processed']}")
        print(f"  API errors: {stats['api_errors']}")
        if stats['errors']:
            print(f"  Errors encountered:")
            for error in stats['errors'][:3]:
                print(f"    - {error}")
        
        print(f"\n✓ ETL job completed successfully")
        print(f"  File: {filepath}")
        print("="*70 + "\n")
        
        logger.info(f"ETL completed: {len(products)} products, saved to {filename}")
        return 0
        
    except Exception as e:
        print(f"✗ ETL failed: {e}")
        logger.error(f"ETL error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
