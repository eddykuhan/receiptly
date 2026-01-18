#!/usr/bin/env python
"""
Convenience script to run the MYDIN Scrapy spider programmatically.
"""
import argparse
import json
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from mydin_scrapy.spiders.mydin_spider import MydinSpider


def main():
    parser = argparse.ArgumentParser(description='Run MYDIN Scrapy spider')
    parser.add_argument(
        '--max-pages',
        type=int,
        default=5,
        help='Maximum number of pages to scrape (default: 5, use 0 for all pages)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/mydin_scrapy_products.json',
        help='Output JSON file path (default: data/mydin_scrapy_products.json)'
    )
    
    args = parser.parse_args()
    
    # Get Scrapy settings
    settings = get_project_settings()
    
    # Override output file
    settings.set('FEEDS', {
        args.output: {
            'format': 'json',
            'encoding': 'utf-8',
            'indent': 2,
            'overwrite': True,
        }
    })
    
    # Create crawler process
    process = CrawlerProcess(settings)
    
    # Determine max_pages
    max_pages = None if args.max_pages == 0 else args.max_pages
    
    # Run spider
    print(f"Starting MYDIN scraper...")
    print(f"Max pages: {'All' if max_pages is None else max_pages}")
    print(f"Output file: {args.output}")
    print("-" * 60)
    
    process.crawl(MydinSpider, max_pages=max_pages)
    process.start()
    
    # Print summary
    print("\n" + "=" * 60)
    print("Scraping complete!")
    print(f"Results saved to: {args.output}")
    
    # Load and display summary statistics
    try:
        with open(args.output, 'r') as f:
            data = json.load(f)
            
        if isinstance(data, list):
            products = data
        elif isinstance(data, dict) and 'products' in data:
            products = data['products']
        else:
            products = data
        
        print(f"\nTotal products scraped: {len(products)}")
        
        # Category breakdown
        if products:
            categories = {}
            for p in products:
                cat = p.get('category', 'Unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            print(f"\nTop categories:")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {cat}: {count}")
            
            # Price statistics
            prices = [p['unit_price'] for p in products if p.get('unit_price', 0) > 0]
            if prices:
                print(f"\nPrice range: RM {min(prices):.2f} - RM {max(prices):.2f}")
                print(f"Average price: RM {sum(prices)/len(prices):.2f}")
    except Exception as e:
        print(f"Could not load summary: {e}")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
