"""
Test script for Amazon-style canonicalization implementation.

Tests:
1. Attribute extraction from product names
2. Candidate generation from database
3. Matching with hard constraints and scoring
4. Full end-to-end canonicalization
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etl_transformers.attribute_extractor import AttributeExtractor
from etl_transformers.candidate_generator import CandidateGenerator
from etl_transformers.matcher import AmazonStyleMatcher
from etl_transformers.canonicalizer import Canonicalizer


def test_attribute_extraction():
    """Test attribute extraction from product names."""
    print("\n" + "="*80)
    print("TEST 1: Attribute Extraction")
    print("="*80)
    
    extractor = AttributeExtractor()
    
    test_cases = [
        "Farm Fresh Pure Fresh Milk 2L",
        "Farm Fresh Pure Fresh /",  # Receipt OCR variant
        "Dutch Lady Full Cream Milk 1 Litre",
        "Nestle Omega Plus Milk 500ml X 3 Pack",
        "Gardenia White Bread 400g",
        "Milo Activ-Go 1kg"
    ]
    
    for item in test_cases:
        attrs = extractor.extract_all_attributes(item)
        print(f"\n{item}")
        print(f"  Brand: {attrs['brand']}")
        print(f"  Size: {attrs['size']} → {attrs['size_normalized']} {attrs['size_unit']}")
        print(f"  Pack: {attrs['pack_count']}")
        print(f"  Variant: {attrs['variant']}")
        print(f"  Tokens: {attrs['name_tokens']}")


def test_candidate_generation():
    """Test candidate generation from database."""
    print("\n" + "="*80)
    print("TEST 2: Candidate Generation")
    print("="*80)
    
    load_dotenv()
    
    # Connect to database
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    
    generator = CandidateGenerator(conn)
    
    # Test case: Receipt item "Farm Fresh Pure Fresh /"
    print("\nQuery: Farm Fresh Pure Fresh / (Receipt OCR)")
    print("Extracted Attributes:")
    print("  Brand: Farm Fresh")
    print("  Size: 2.0 L (normalized)")
    print("  Category: Dairy")
    print("  Tokens: ['farm', 'fresh', 'pure']")
    
    candidates = generator.generate_candidates(
        brand="Farm Fresh",
        size_normalized=2.0,
        size_unit="L",
        category="Dairy",
        name_tokens=["farm", "fresh", "pure"],
        max_candidates=10
    )
    
    print(f"\nGenerated {len(candidates)} candidates:")
    for i, candidate in enumerate(candidates, 1):
        print(f"  {i}. {candidate.get('item_name', 'N/A')} - {candidate.get('brand', 'N/A')} {candidate.get('size', 'N/A')}")
    
    conn.close()


def test_matching():
    """Test matching with hard constraints and scoring."""
    print("\n" + "="*80)
    print("TEST 3: Matching (Hard Constraints + Scoring)")
    print("="*80)
    
    matcher = AmazonStyleMatcher()
    
    # Query attributes (receipt item)
    query_attrs = {
        'item_name': 'Farm Fresh Pure Fresh /',
        'brand': 'Farm Fresh',
        'size_normalized': 2.0,
        'size_unit': 'L',
        'name_tokens': ['farm', 'fresh', 'pure'],
        'category': 'Dairy',
        'price': 11.50
    }
    
    # Mock candidates (simulating database results)
    candidates = [
        {
            'id': '123e4567-e89b-12d3-a456-426614174000',
            'item_name': 'Farm Fresh Pure Fresh Milk 2L',
            'brand': 'Farm Fresh',
            'size': '2L',
            'size_normalized': 2.0,
            'size_unit': 'L',
            'name_tokens': ['farm', 'fresh', 'pure', 'milk'],
            'category': 'Dairy',
            'price': 11.90
        },
        {
            'id': '223e4567-e89b-12d3-a456-426614174001',
            'item_name': 'Farm Fresh Low Fat Milk 1.5L',
            'brand': 'Farm Fresh',
            'size': '1.5L',
            'size_normalized': 1.5,
            'size_unit': 'L',
            'name_tokens': ['farm', 'fresh', 'low', 'fat', 'milk'],
            'category': 'Dairy',
            'price': 9.50
        }
    ]
    
    print("\nQuery: Farm Fresh Pure Fresh / (Receipt)")
    print("\nCandidates:")
    for i, candidate in enumerate(candidates, 1):
        print(f"  {i}. {candidate['item_name']}")
    
    best_match, score, breakdown = matcher.find_best_match(
        query_attrs, candidates, threshold=0.75
    )
    
    print(f"\nBest Match: {best_match['item_name'] if best_match else 'None'}")
    print(f"Overall Score: {score:.3f}")
    print(f"\nScore Breakdown:")
    for component, value in breakdown.items():
        print(f"  {component}: {value:.3f}")


def test_end_to_end():
    """Test full end-to-end canonicalization."""
    print("\n" + "="*80)
    print("TEST 4: End-to-End Canonicalization")
    print("="*80)
    
    load_dotenv()
    
    db_config = {
        'host': os.getenv("DB_HOST"),
        'port': os.getenv("DB_PORT"),
        'database': os.getenv("DB_NAME"),
        'user': os.getenv("DB_USER"),
        'password': os.getenv("DB_PASSWORD")
    }
    
    canonicalizer = Canonicalizer(db_config)
    
    # Test receipt items
    receipt_items = [
        ("Farm Fresh Pure Fresh /", "Dairy", 11.50),
        ("Dutch Lady Full Cream 1L", "Dairy", 8.90),
        ("Milo Activ-Go", "Beverages", 15.50)
    ]
    
    print("\nTesting Receipt Item Canonicalization:")
    for item_name, category, price in receipt_items:
        print(f"\n{item_name} ({category})")
        
        result = canonicalizer.canonicalize_amazon_style(
            item_name=item_name,
            category=category,
            price=price
        )
        
        print(f"  Match Method: {result['match_method']}")
        print(f"  Canonical ID: {result['canonical_item_id'][:8]}...")
        if 'matched_name' in result:
            print(f"  Matched To: {result['matched_name']}")
        if 'confidence' in result:
            print(f"  Confidence: {result['confidence']:.3f}")
    
    canonicalizer.close()


if __name__ == "__main__":
    # Run all tests
    try:
        test_attribute_extraction()
        test_candidate_generation()
        test_matching()
        test_end_to_end()
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
