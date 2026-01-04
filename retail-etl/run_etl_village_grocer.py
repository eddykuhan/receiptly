#!/usr/bin/env python3
"""
Standalone script to run Village Grocer scraper and save raw data to JSON.

Usage:
    python run_etl_village_grocer.py                     # Scrape all collections
    python run_etl_village_grocer.py --collection fresh  # Single collection
    python run_etl_village_grocer.py --max 1000          # Limit to 1000 products
    python run_etl_village_grocer.py --collection groceries --max 500

Examples:
    # Full ETL pipeline (all collections)
    python run_etl_village_grocer.py

    # Test with limited products (debug mode)
    python run_etl_village_grocer.py --max 100

    # Specific collection only
    python run_etl_village_grocer.py --collection fresh
"""

import json
import os
import sys
import argparse
from datetime import datetime
from scrapers.village_grocer import VillageGrocerScraper

# Create data/raw directory if it doesn't exist
RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'raw')
os.makedirs(RAW_DATA_DIR, exist_ok=True)


def main():
    """Run Village Grocer scraper with optional filters."""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Run Village Grocer (Shopify) scraper and save raw data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--collection',
        type=str,
        nargs='+',
        help='Specific collection(s) to scrape (e.g., fresh, groceries)'
    )
    parser.add_argument(
        '--max',
        type=int,
        dest='max_products',
        help='Maximum products to scrape (for testing)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose logging'
    )
    
    args = parser.parse_args()
    
    # Prepare scraper arguments
    scraper_kwargs = {}
    if args.collection:
        scraper_kwargs['collections'] = args.collection
    if args.max_products:
        scraper_kwargs['max_products'] = args.max_products
    
    # Display configuration
    print("=" * 70)
    print("VILLAGE GROCER ETL SCRAPER")
    print("=" * 70)
    print("\nConfiguration:")
    if args.collection:
        print(f"  Collections: {', '.join(args.collection)}")
    else:
        print("  Collections: ALL (6 default collections)")
    if args.max_products:
        print(f"  Max products: {args.max_products}")
    else:
        print("  Max products: None (full scrape)")
    print()
    
    # Initialize scraper
    print("Initializing Village Grocer scraper...")
    scraper = VillageGrocerScraper(**scraper_kwargs)
    
    # Run scraper
    print(f"Scraping products from Village Grocer API...")
    products = scraper.run()
    
    print(f"\n✓ Scraped {len(products)} products")
    
    # Save to JSON file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"village_grocer_{timestamp}.json"
    filepath = os.path.join(RAW_DATA_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved to: {filepath}")
    
    # Show summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total products: {len(products):,}")
    
    if products:
        # Price analysis
        prices = [p['unit_price'] for p in products if p.get('unit_price', 0) > 0]
        if prices:
            print(f"Price range: RM {min(prices):.2f} - RM {max(prices):.2f}")
            print(f"Avg price: RM {sum(prices)/len(prices):.2f}")
        
        # Category analysis
        categories = {}
        for p in products:
            cat = p.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"Categories: {len(categories)}")
        print("\nTop 10 categories:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {cat:30} : {count:4,d} products")
        
        # Brand analysis
        brands = {}
        for p in products:
            brand = p.get('brand', 'Unbranded')
            brands[brand] = brands.get(brand, 0) + 1
        
        print(f"\nUnique brands: {len(brands)}")
        print("Top 10 brands:")
        for brand, count in sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {brand:30} : {count:4,d} products")
        
        # SKU analysis
        skus_with_value = [p for p in products if p.get('sku')]
        print(f"\nProducts with SKU: {len(skus_with_value)}/{len(products)} ({100*len(skus_with_value)/len(products):.1f}%)")
    
    print("\n" + "=" * 70)
    print(f"✓ ETL job completed successfully!")
    print("=" * 70)
    
    # Return exit code
    return 0 if products else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠ Scraper interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
