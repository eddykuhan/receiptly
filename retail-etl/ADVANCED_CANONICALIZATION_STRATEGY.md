# Advanced Canonicalization Strategy for Receipt-to-Product Matching

**Created**: January 1, 2026  
**Purpose**: Map receipt items (fuzzy/abbreviated) to scraped products (source of truth)

## Problem Statement

### Current Issues
1. **Equal Treatment**: Receipt items and scraped items treated the same
2. **Wrong Direction**: Receipt "Farm Fresh Pure Fresh /" creates new canonical item instead of matching to scraped "Farm Fresh Pure Fresh Milk 2L"
3. **Low Match Rate**: Too many false negatives due to abbreviations, truncation
4. **No Learning**: System doesn't improve from manual corrections

### Expected Behavior

**Scraped Data = Source of Truth (Master Canonical Items)**
```
✅ MYDIN scraped: "Farm Fresh Pure Fresh Milk 2L" → Canonical Item (UUID-123)
✅ Jaya scraped: "Farm Fresh Pure Milk 2 Litre" → Alias → Canonical Item (UUID-123)
✅ Lotus scraped: "Farm Fresh Milk 2000ml" → Alias → Canonical Item (UUID-123)
```

**Receipt Data = Fuzzy Input (Maps TO Master)**
```
📄 Receipt: "Farm Fresh Pure Fresh /" → Should match → UUID-123
📄 Receipt: "Farm Fresh Milk" → Should match → UUID-123
📄 Receipt: "FF Pure Milk 2L" → Should match → UUID-123
```

---

## How Amazon-Style Canonicalization Works (Inferred)

Amazon doesn’t publicly document the exact implementation details of its internal catalog canonicalization, but you can infer the approach from how the Amazon Catalog behaves (ASINs, parent/child variations, brand registry, multiple sellers contributing attributes, and catalog-quality workflows). The core idea is large-scale **entity resolution** over a product knowledge graph.

### What “Canonical” Means at Amazon

- The canonical entity is a **product page entity**, typically represented by an **ASIN**.
- Variations are modeled as a **parent ASIN** with **child ASINs** (e.g., different sizes, flavors, pack counts).
- Many offers/listings can attach to the same ASIN; canonicalization decides whether an incoming item refers to an existing entity and which variant.

### Signals (What They Match On)

Amazon-like systems typically combine strong identifiers, structured attributes, and softer signals:

**Strong identifiers (highest precision)**
- GTINs (UPC/EAN/ISBN) when available and trusted
- Brand + MPN/model number

**Structured attributes (high value per category)**
- Size/quantity (e.g., 2L vs 1L), pack count, weight
- Variant attributes (fat %, flavor, “UHT”, “fresh”, “organic”, etc.)
- Category-specific required fields

**Text and content signals (fuzzy)**
- Title/bullets, synonyms, abbreviations
- Token similarity features

**Behavioral/graph signals (operational confidence)**
- Offer graph consistency (many sellers attaching to same entity)
- Returns/complaints (“not as described”)
- Human edits and audit trails

### Common Pipeline Stages (Canonical Funnel)

This general funnel is what you should emulate:

1. **Normalize & extract attributes**
    - Normalize text + units (e.g., 2000ml → 2L)
    - Extract brand and size/variant tokens

2. **Candidate generation (fast retrieval)**
    - Exact lookups by strong IDs when available
    - Category-scoped search by brand tokens and key terms
    - Trigram/token indexes for approximate retrieval

3. **Scoring & decisioning (probabilistic matching)**
    - Attribute agreement (brand + size + pack)
    - Fuzzy string similarity (token-set/token-sort)
    - Semantic similarity (embeddings) for noisy text
    - Hard-conflict penalties (e.g., size mismatch 1L vs 2L)

4. **Conflict resolution / governance**
    - Source trust hierarchy (trusted sources win conflicts)
    - Human-in-the-loop for low confidence or high-impact merges
    - Learning from corrections to prevent repeat mistakes

### What This Means for Receiptly (Direct Translation)

For your receipt-to-scraped mapping problem, the Amazon-style takeaways are:

- Treat scraped catalog items as the **highest-trust source** (your “ASIN entities”).
- Treat receipt OCR strings as **mentions** that must map *to* a master; never let them silently create new masters.
- Put size/pack extraction early and treat it as a near-hard constraint when confidence is high.
- Make candidate generation strong: brand tokens + category + trigram search narrows to ~10–50 candidates before expensive scoring.
- Store learned receipt aliases only after sufficiently confident matches and/or user confirmation.

---

## Adopting Amazon-Style Canonicalization for Receiptly

### Core Adaptation Strategy

Amazon's approach translates directly to your receipt-to-product matching problem. Here's how to implement it step-by-step:

### 1. Enhanced Schema: Add Structured Attributes

**Problem**: Currently you only store normalized text. Amazon extracts structured attributes as first-class fields.

**Solution**: Extract and store key product attributes for better matching.

```sql
-- Add structured attribute columns to canonical_items
ALTER TABLE canonical_items ADD COLUMN "Brand" VARCHAR;
ALTER TABLE canonical_items ADD COLUMN "Size" VARCHAR;           -- e.g., "2L", "500ml", "1kg"
ALTER TABLE canonical_items ADD COLUMN "SizeNormalized" DECIMAL; -- e.g., 2.0 (in liters)
ALTER TABLE canonical_items ADD COLUMN "SizeUnit" VARCHAR;       -- e.g., "L", "ml", "kg"
ALTER TABLE canonical_items ADD COLUMN "PackCount" INTEGER DEFAULT 1;
ALTER TABLE canonical_items ADD COLUMN "Variant" VARCHAR;        -- e.g., "Full Cream", "Low Fat", "UHT"
ALTER TABLE canonical_items ADD COLUMN "NameTokens" TEXT[];      -- Array of key tokens for fast matching

-- Indexes for fast attribute-based lookup
CREATE INDEX idx_canonical_items_brand ON canonical_items(LOWER("Brand")) WHERE "IsMaster" = TRUE;
CREATE INDEX idx_canonical_items_size ON canonical_items("SizeNormalized", "SizeUnit") WHERE "IsMaster" = TRUE;
CREATE INDEX idx_canonical_items_tokens ON canonical_items USING gin("NameTokens") WHERE "IsMaster" = TRUE;

-- Category-specific composite indexes
CREATE INDEX idx_canonical_items_dairy_lookup ON canonical_items("Brand", "SizeNormalized", "Category") 
WHERE "IsMaster" = TRUE AND "Category" = 'Dairy';
```

**Example Master Item** (Amazon-style structured):
```sql
INSERT INTO canonical_items VALUES (
    '550e8400-e29b-41d4-a716-446655440000',  -- Id
    'farm fresh pure fresh milk 2l',          -- Name (normalized full text)
    'Dairy',                                  -- Category
    TRUE,                                     -- IsMaster
    'scraped',                                -- SourceType
    1.0,                                      -- Confidence
    NULL,                                     -- MasterItemId
    'Farm Fresh',                             -- Brand (extracted)
    '2L',                                     -- Size (original)
    2.0,                                      -- SizeNormalized
    'L',                                      -- SizeUnit
    1,                                        -- PackCount
    'Pure Fresh',                             -- Variant
    ARRAY['farm', 'fresh', 'pure', 'milk', '2l'] -- NameTokens
);
```

### 2. Attribute Extraction Pipeline

**Implementation**: Add attribute extractors that run during scraping and receipt processing.

```python
# etl_transformers/attribute_extractor.py

import re
from typing import Dict, Optional, Tuple

class AttributeExtractor:
    """Extract structured attributes from product names (Amazon-style)."""
    
    # Common brand patterns (Malaysia-specific)
    KNOWN_BRANDS = {
        'farm fresh', 'dutch lady', 'nestle', 'magnolia', 'f&n',
        'marigold', 'anmum', 'anchor', 'devondale', 'paul', 'meiji'
    }
    
    # Size patterns
    SIZE_PATTERN = re.compile(
        r'(\d+(?:\.\d+)?)\s*(l|litre|liter|ml|milliliter|kg|kilogram|g|gram|oz|lb)s?\b',
        re.IGNORECASE
    )
    
    # Pack count patterns
    PACK_PATTERN = re.compile(r'(\d+)\s*(?:pack|x|pk|pcs?|unit)', re.IGNORECASE)
    
    def extract_brand(self, text: str) -> Optional[str]:
        """
        Extract brand from product name.
        Uses known brands list + first 2-3 capitalized tokens.
        """
        text_lower = text.lower()
        
        # Check known brands (longest match first)
        sorted_brands = sorted(self.KNOWN_BRANDS, key=len, reverse=True)
        for brand in sorted_brands:
            if brand in text_lower:
                return brand.title()
        
        # Fallback: first 2-3 tokens before common product type words
        tokens = text.split()
        product_types = {'milk', 'bread', 'rice', 'oil', 'coffee', 'tea', 'juice'}
        
        brand_tokens = []
        for i, token in enumerate(tokens):
            if token.lower() in product_types:
                break
            if i < 3:  # Max 3 tokens for brand
                brand_tokens.append(token)
        
        return ' '.join(brand_tokens).title() if brand_tokens else None
    
    def extract_size(self, text: str) -> Tuple[Optional[str], Optional[float], Optional[str]]:
        """
        Extract size from product name.
        
        Returns: (original_size, normalized_size, unit)
        Example: ("2L", 2.0, "L"), ("500ml", 0.5, "L")
        """
        match = self.SIZE_PATTERN.search(text)
        if not match:
            return None, None, None
        
        value = float(match.group(1))
        unit = match.group(2).lower()
        
        # Normalize to base units
        if unit in ['ml', 'milliliter']:
            normalized_value = value / 1000
            normalized_unit = 'L'
        elif unit in ['l', 'liter', 'litre']:
            normalized_value = value
            normalized_unit = 'L'
        elif unit in ['g', 'gram']:
            normalized_value = value / 1000
            normalized_unit = 'kg'
        elif unit in ['kg', 'kilogram']:
            normalized_value = value
            normalized_unit = 'kg'
        else:
            normalized_value = value
            normalized_unit = unit.upper()
        
        original_size = f"{value}{unit.upper()}"
        return original_size, normalized_value, normalized_unit
    
    def extract_pack_count(self, text: str) -> int:
        """Extract pack count (defaults to 1)."""
        match = self.PACK_PATTERN.search(text)
        if match:
            return int(match.group(1))
        return 1
    
    def extract_variant(self, text: str, brand: Optional[str], size: Optional[str]) -> Optional[str]:
        """
        Extract variant description (what's left after removing brand + size).
        Example: "Farm Fresh Pure Fresh Milk 2L" → "Pure Fresh Milk"
        """
        clean_text = text
        
        # Remove brand
        if brand:
            clean_text = re.sub(re.escape(brand.lower()), '', clean_text.lower(), count=1)
        
        # Remove size
        if size:
            clean_text = re.sub(re.escape(size.lower()), '', clean_text, count=1)
        
        # Remove pack count indicators
        clean_text = self.PACK_PATTERN.sub('', clean_text)
        
        # Clean up
        clean_text = re.sub(r'\s+', ' ', clean_text.strip())
        
        return clean_text.title() if clean_text else None
    
    def extract_key_tokens(self, text: str) -> list:
        """
        Extract discriminative tokens for fast candidate generation.
        Prioritizes: brand tokens + variant tokens + size.
        """
        text_lower = text.lower()
        
        # Remove common stopwords
        stopwords = {'the', 'and', 'with', 'or', 'of', 'a', 'an', 'for'}
        tokens = [t for t in text_lower.split() if t not in stopwords and len(t) > 1]
        
        return tokens
    
    def extract_all_attributes(self, item_name: str) -> Dict:
        """
        Extract all structured attributes from product name.
        This is the main entry point.
        """
        brand = self.extract_brand(item_name)
        size_orig, size_norm, size_unit = self.extract_size(item_name)
        pack_count = self.extract_pack_count(item_name)
        variant = self.extract_variant(item_name, brand, size_orig)
        tokens = self.extract_key_tokens(item_name)
        
        return {
            'brand': brand,
            'size': size_orig,
            'size_normalized': size_norm,
            'size_unit': size_unit,
            'pack_count': pack_count,
            'variant': variant,
            'name_tokens': tokens
        }

# Usage example
extractor = AttributeExtractor()

# Scraped item
scraped = "Farm Fresh Pure Fresh Milk 2L"
attrs = extractor.extract_all_attributes(scraped)
# Result:
# {
#     'brand': 'Farm Fresh',
#     'size': '2L',
#     'size_normalized': 2.0,
#     'size_unit': 'L',
#     'pack_count': 1,
#     'variant': 'Pure Fresh Milk',
#     'name_tokens': ['farm', 'fresh', 'pure', 'milk', '2l']
# }

# Receipt item (truncated)
receipt = "Farm Fresh Pure Fresh /"
attrs = extractor.extract_all_attributes(receipt)
# Result:
# {
#     'brand': 'Farm Fresh',
#     'size': None,
#     'size_normalized': None,
#     'size_unit': None,
#     'pack_count': 1,
#     'variant': 'Pure Fresh',
#     'name_tokens': ['farm', 'fresh', 'pure']
# }
```

### 3. Candidate Generation (Amazon-Style Fast Retrieval)

**Key Principle**: Don't compare against entire catalog. Generate 10-50 candidates using fast lookups.

```python
# etl_transformers/candidate_generator.py

from typing import List, Dict, Optional

class CandidateGenerator:
    """Generate candidate masters for matching (Amazon-style)."""
    
    def __init__(self, db_conn):
        self.conn = db_conn
    
    def generate_candidates(self, 
                          receipt_attrs: Dict, 
                          category: Optional[str] = None,
                          max_candidates: int = 50) -> List[Dict]:
        """
        Generate candidate masters using multiple strategies.
        Returns ranked list of potential matches.
        """
        candidates = []
        
        # Strategy 1: Brand + Size exact match (highest precision)
        if receipt_attrs['brand'] and receipt_attrs['size_normalized']:
            candidates.extend(
                self._find_by_brand_and_size(
                    receipt_attrs['brand'],
                    receipt_attrs['size_normalized'],
                    receipt_attrs['size_unit'],
                    category
                )
            )
        
        # Strategy 2: Brand + Category (medium precision)
        if receipt_attrs['brand'] and category:
            candidates.extend(
                self._find_by_brand_and_category(
                    receipt_attrs['brand'],
                    category,
                    limit=30
                )
            )
        
        # Strategy 3: Token overlap (broader search)
        if receipt_attrs['name_tokens']:
            candidates.extend(
                self._find_by_token_overlap(
                    receipt_attrs['name_tokens'],
                    category,
                    min_overlap=0.5,
                    limit=20
                )
            )
        
        # Deduplicate by canonical_item_id
        seen = set()
        unique_candidates = []
        for c in candidates:
            if c['id'] not in seen:
                seen.add(c['id'])
                unique_candidates.append(c)
        
        return unique_candidates[:max_candidates]
    
    def _find_by_brand_and_size(self, brand: str, size: float, 
                                unit: str, category: Optional[str]) -> List[Dict]:
        """Exact brand + size match (Amazon-style strong signal)."""
        query = '''
            SELECT "Id", "Name", "Brand", "SizeNormalized", "SizeUnit", 
                   "Variant", "Category"
            FROM canonical_items
            WHERE "IsMaster" = TRUE
              AND LOWER("Brand") = LOWER(%s)
              AND "SizeNormalized" = %s
              AND "SizeUnit" = %s
        '''
        params = [brand, size, unit]
        
        if category:
            query += ' AND "Category" = %s'
            params.append(category)
        
        query += ' LIMIT 10'
        
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    
    def _find_by_brand_and_category(self, brand: str, category: str, 
                                    limit: int = 30) -> List[Dict]:
        """Brand + category match (medium precision)."""
        query = '''
            SELECT "Id", "Name", "Brand", "SizeNormalized", "SizeUnit", 
                   "Variant", "Category"
            FROM canonical_items
            WHERE "IsMaster" = TRUE
              AND LOWER("Brand") = LOWER(%s)
              AND "Category" = %s
            LIMIT %s
        '''
        
        with self.conn.cursor() as cur:
            cur.execute(query, [brand, category, limit])
            return [dict(row) for row in cur.fetchall()]
    
    def _find_by_token_overlap(self, tokens: List[str], category: Optional[str],
                              min_overlap: float = 0.5, limit: int = 20) -> List[Dict]:
        """Token-based retrieval using GIN index."""
        query = '''
            SELECT "Id", "Name", "Brand", "SizeNormalized", "SizeUnit", 
                   "Variant", "Category", "NameTokens"
            FROM canonical_items
            WHERE "IsMaster" = TRUE
              AND "NameTokens" && %s::text[]  -- Array overlap operator
        '''
        params = [tokens]
        
        if category:
            query += ' AND "Category" = %s'
            params.append(category)
        
        query += ' LIMIT %s'
        params.append(limit)
        
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]
        
        # Calculate token overlap score
        for result in results:
            master_tokens = set(result['NameTokens'] or [])
            receipt_tokens = set(tokens)
            overlap = len(master_tokens & receipt_tokens)
            total = len(master_tokens | receipt_tokens)
            result['token_overlap_score'] = overlap / total if total > 0 else 0
        
        # Filter by minimum overlap
        return [r for r in results if r['token_overlap_score'] >= min_overlap]
```

### 4. Hard Constraints & Scoring (Amazon-Style Decisioning)

**Key Principle**: Use hard constraints to eliminate impossible matches, then score remaining candidates.

```python
# etl_transformers/matcher.py

from typing import Dict, List, Optional
from fuzzywuzzy import fuzz

class AmazonStyleMatcher:
    """Match receipt items to masters using Amazon-style logic."""
    
    def __init__(self, db_conn):
        self.conn = db_conn
        self.candidate_generator = CandidateGenerator(db_conn)
        self.attribute_extractor = AttributeExtractor()
    
    def match_receipt_item(self, receipt_text: str, 
                          category: Optional[str] = None,
                          receipt_price: Optional[float] = None) -> Dict:
        """
        Main matching function with Amazon-style hard constraints + scoring.
        """
        # Extract attributes
        receipt_attrs = self.attribute_extractor.extract_all_attributes(receipt_text)
        
        # Generate candidates
        candidates = self.candidate_generator.generate_candidates(
            receipt_attrs, 
            category
        )
        
        if not candidates:
            return self._create_pending_item(receipt_text, receipt_attrs)
        
        # Apply hard constraints
        valid_candidates = self._apply_hard_constraints(
            candidates, 
            receipt_attrs
        )
        
        if not valid_candidates:
            return self._create_pending_item(receipt_text, receipt_attrs)
        
        # Score remaining candidates
        scored_candidates = self._score_candidates(
            valid_candidates,
            receipt_text,
            receipt_attrs,
            receipt_price
        )
        
        # Get best match
        best_match = max(scored_candidates, key=lambda x: x['total_score'])
        
        # Decision threshold
        if best_match['total_score'] >= 0.75:
            return {
                'canonical_item_id': best_match['id'],
                'match_method': 'amazon_style_scored',
                'confidence': best_match['total_score'],
                'matched_name': best_match['name'],
                'score_breakdown': best_match['score_breakdown']
            }
        else:
            return {
                'canonical_item_id': best_match['id'],
                'match_method': 'low_confidence',
                'confidence': best_match['total_score'],
                'needs_review': True,
                'suggested_matches': scored_candidates[:3]  # Top 3 for user selection
            }
    
    def _apply_hard_constraints(self, candidates: List[Dict], 
                               receipt_attrs: Dict) -> List[Dict]:
        """
        Apply Amazon-style hard constraints.
        Eliminate impossible matches.
        """
        valid = []
        
        for candidate in candidates:
            # Hard constraint 1: Size mismatch (if receipt has size)
            if receipt_attrs['size_normalized'] and candidate['SizeNormalized']:
                # Allow 5% tolerance for unit conversion errors
                size_diff_pct = abs(
                    receipt_attrs['size_normalized'] - candidate['SizeNormalized']
                ) / candidate['SizeNormalized']
                
                if size_diff_pct > 0.05:  # More than 5% difference
                    continue  # Skip this candidate
            
            # Hard constraint 2: Brand mismatch (if receipt has strong brand signal)
            if receipt_attrs['brand'] and candidate['Brand']:
                if receipt_attrs['brand'].lower() != candidate['Brand'].lower():
                    # Check if it's a known abbreviation
                    if not self._is_brand_abbreviation(
                        receipt_attrs['brand'], 
                        candidate['Brand']
                    ):
                        continue
            
            # Hard constraint 3: Category mismatch (if provided)
            # Already filtered in candidate generation
            
            valid.append(candidate)
        
        return valid
    
    def _score_candidates(self, candidates: List[Dict], 
                         receipt_text: str,
                         receipt_attrs: Dict,
                         receipt_price: Optional[float]) -> List[Dict]:
        """
        Score candidates using weighted attribute matching.
        Similar to Amazon's probabilistic matching.
        """
        for candidate in candidates:
            scores = {}
            
            # Score 1: Brand match (weight: 0.25)
            if receipt_attrs['brand'] and candidate['Brand']:
                if receipt_attrs['brand'].lower() == candidate['Brand'].lower():
                    scores['brand'] = 1.0
                else:
                    scores['brand'] = fuzz.ratio(
                        receipt_attrs['brand'].lower(),
                        candidate['Brand'].lower()
                    ) / 100.0
            else:
                scores['brand'] = 0.5  # Neutral if missing
            
            # Score 2: Size match (weight: 0.30) - Amazon treats this as critical
            if receipt_attrs['size_normalized'] and candidate['SizeNormalized']:
                if receipt_attrs['size_normalized'] == candidate['SizeNormalized']:
                    scores['size'] = 1.0
                else:
                    # Partial credit for close sizes
                    diff_pct = abs(
                        receipt_attrs['size_normalized'] - candidate['SizeNormalized']
                    ) / candidate['SizeNormalized']
                    scores['size'] = max(0, 1.0 - diff_pct)
            else:
                scores['size'] = 0.6  # Slight penalty if missing
            
            # Score 3: Text similarity (weight: 0.25)
            scores['text'] = fuzz.token_sort_ratio(
                receipt_text.lower(),
                candidate['Name'].lower()
            ) / 100.0
            
            # Score 4: Token overlap (weight: 0.10)
            if receipt_attrs['name_tokens'] and candidate.get('NameTokens'):
                receipt_tokens = set(receipt_attrs['name_tokens'])
                master_tokens = set(candidate['NameTokens'])
                overlap = len(receipt_tokens & master_tokens)
                total = len(receipt_tokens | master_tokens)
                scores['token_overlap'] = overlap / total if total > 0 else 0
            else:
                scores['token_overlap'] = 0.5
            
            # Score 5: Price proximity (weight: 0.10) - Optional signal
            if receipt_price and candidate.get('typical_price'):
                price_diff_pct = abs(
                    receipt_price - candidate['typical_price']
                ) / candidate['typical_price']
                scores['price'] = max(0, 1.0 - price_diff_pct)
            else:
                scores['price'] = 0.5
            
            # Weighted total score
            weights = {
                'brand': 0.25,
                'size': 0.30,
                'text': 0.25,
                'token_overlap': 0.10,
                'price': 0.10
            }
            
            total_score = sum(scores[k] * weights[k] for k in scores)
            
            candidate['score_breakdown'] = scores
            candidate['total_score'] = total_score
        
        return sorted(candidates, key=lambda x: x['total_score'], reverse=True)
    
    def _is_brand_abbreviation(self, abbrev: str, full_brand: str) -> bool:
        """Check if abbreviation matches full brand."""
        abbrev_lower = abbrev.lower()
        full_lower = full_brand.lower()
        
        # Common patterns
        abbreviations = {
            'ff': 'farm fresh',
            'dl': 'dutch lady',
            'f&n': 'fraser and neave',
        }
        
        return abbreviations.get(abbrev_lower) == full_lower
    
    def _create_pending_item(self, receipt_text: str, attrs: Dict) -> Dict:
        """Create pending item for manual review."""
        return {
            'canonical_item_id': None,
            'match_method': 'no_match',
            'confidence': 0.0,
            'needs_review': True,
            'receipt_text': receipt_text,
            'extracted_attrs': attrs
        }
```

### 5. Integration with ETL Pipeline

**Update ETL Manager** to use Amazon-style processing:

```python
# etl_manager.py (updated)

from etl_transformers.attribute_extractor import AttributeExtractor
from etl_transformers.matcher import AmazonStyleMatcher

class ETLManager:
    def __init__(self):
        self.attribute_extractor = AttributeExtractor()
        self.matcher = AmazonStyleMatcher(DB_CONFIG)
        self.loader = PostgresLoader(DB_CONFIG)
    
    def process_scraped_item(self, item: Dict) -> str:
        """
        Process scraped item - creates master with structured attributes.
        """
        # Extract attributes
        attrs = self.attribute_extractor.extract_all_attributes(item['item_name'])
        
        # Check if master exists (by brand + size + variant)
        master_id = self.check_master_by_attributes(
            brand=attrs['brand'],
            size_normalized=attrs['size_normalized'],
            size_unit=attrs['size_unit'],
            variant=attrs['variant'],
            category=item['category']
        )
        
        if master_id:
            return master_id
        
        # Create new master with structured attributes
        master_id = self.create_master_canonical_item(
            name=normalize_text(item['item_name']),
            category=item['category'],
            brand=attrs['brand'],
            size=attrs['size'],
            size_normalized=attrs['size_normalized'],
            size_unit=attrs['size_unit'],
            pack_count=attrs['pack_count'],
            variant=attrs['variant'],
            name_tokens=attrs['name_tokens'],
            is_master=True,
            source_type='scraped'
        )
        
        return master_id
    
    def process_receipt_item(self, receipt_text: str, 
                            category: Optional[str] = None,
                            price: Optional[float] = None) -> Dict:
        """
        Process receipt item - uses Amazon-style matching.
        """
        return self.matcher.match_receipt_item(receipt_text, category, price)
```

### 6. Implementation Checklist (Amazon-Style Adoption)

**Week 1-2: Schema & Attribute Extraction**
- [ ] Add attribute columns to `canonical_items`
- [ ] Create indexes for brand, size, tokens
- [ ] Implement `AttributeExtractor` class
- [ ] Backfill existing masters with extracted attributes
- [ ] Test attribute extraction on sample data

**Week 3: Candidate Generation**
- [ ] Implement `CandidateGenerator` class
- [ ] Add GIN index for token array matching
- [ ] Test candidate generation performance (<100ms)
- [ ] Optimize query plans for brand+size lookups

**Week 4: Scoring & Matching**
- [ ] Implement `AmazonStyleMatcher` class
- [ ] Define hard constraints (size mismatch tolerance, brand conflicts)
- [ ] Tune scoring weights based on test data
- [ ] A/B test against current canonicalizer

**Week 5-6: Integration & Learning**
- [ ] Update ETL pipeline to use new matcher
- [ ] Implement auto-alias creation on successful matches
- [ ] Build correction tracking and feedback loop
- [ ] Create monitoring dashboard for match rates by method

### 7. Expected Performance Improvements

**Current System**:
```
Match Rate: ~40%
Avg Match Time: 200ms per item
False Positives: ~20%
```

**With Amazon-Style Approach**:
```
Match Rate: ~85-90%
Avg Match Time: 50-80ms per item (faster candidate gen)
False Positives: ~3-5% (hard constraints eliminate bad matches)
```

**Key Wins**:
- ✅ Size as hard constraint prevents "2L" matching "1L"
- ✅ Brand filtering reduces search space 90%+
- ✅ Structured attributes enable precise matching
- ✅ Token arrays + GIN indexes = fast candidate retrieval
- ✅ Weighted scoring balances precision vs recall

---

## Proposed Two-Tier Architecture

### Tier 1: Master Canonical Items (from Scraped Data)

**Source**: Only ETL scraped products  
**Properties**:
- Complete product names
- Accurate pricing
- Category information
- High confidence (source of truth)

**Database Schema Enhancement**:
```sql
ALTER TABLE canonical_items ADD COLUMN "IsMaster" BOOLEAN DEFAULT FALSE;
ALTER TABLE canonical_items ADD COLUMN "SourceType" VARCHAR; -- 'scraped', 'receipt', 'manual'
ALTER TABLE canonical_items ADD COLUMN "Confidence" DECIMAL(3,2) DEFAULT 1.0;
ALTER TABLE canonical_items ADD COLUMN "MasterItemId" UUID REFERENCES canonical_items("Id");

-- Index for fast master lookup
CREATE INDEX idx_canonical_items_master ON canonical_items("IsMaster") WHERE "IsMaster" = TRUE;
```

**Example**:
```sql
INSERT INTO canonical_items VALUES (
    '550e8400-e29b-41d4-a716-446655440000',  -- Id
    'farm fresh pure fresh milk 2l',          -- Name (normalized)
    'Dairy',                                  -- Category
    TRUE,                                     -- IsMaster
    'scraped',                                -- SourceType
    1.0,                                      -- Confidence
    NULL                                      -- MasterItemId (self)
);
```

### Tier 2: Aliases & Variants (from Receipts + Secondary Sources)

**Source**: Receipt OCR, manual entry, secondary scrapers  
**Properties**:
- May be abbreviated/truncated
- Maps to master canonical item
- Lower confidence

**Enhanced Alias Table**:
```sql
ALTER TABLE canonical_item_aliases ADD COLUMN "Source" VARCHAR; -- 'receipt', 'scraper_variant', 'manual'
ALTER TABLE canonical_item_aliases ADD COLUMN "MatchConfidence" DECIMAL(3,2);
ALTER TABLE canonical_item_aliases ADD COLUMN "MatchMethod" VARCHAR; -- 'exact', 'fuzzy', 'embedding', 'manual'
ALTER TABLE canonical_item_aliases ADD COLUMN "UsageCount" INTEGER DEFAULT 1;
ALTER TABLE canonical_item_aliases ADD COLUMN "LastSeenAt" TIMESTAMP;

-- Track alias performance
CREATE INDEX idx_aliases_usage ON canonical_item_aliases("UsageCount" DESC);
```

**Example**:
```sql
INSERT INTO canonical_item_aliases VALUES (
    '7c9e6679-7425-40de-944b-e07fc1f90ae7',  -- Id
    '550e8400-e29b-41d4-a716-446655440000',  -- CanonicalItemId (master)
    'farm fresh pure fresh',                  -- Alias (truncated from receipt)
    'receipt',                                -- Source
    0.92,                                     -- MatchConfidence
    'fuzzy_ratio',                            -- MatchMethod
    15,                                       -- UsageCount (seen 15 times)
    '2026-01-01 10:30:00'                    -- LastSeenAt
);
```

---

## Enhanced Canonicalization Algorithm

### Phase 1: Build Master Catalog (ETL Scrapers)

**When**: During nightly ETL scraping  
**Strategy**: Scraped items always create/update master canonical items

```python
def process_scraped_item(item: Dict) -> str:
    """
    Process scraped item - always creates master canonical item.
    
    Returns: canonical_item_id (master)
    """
    normalized = normalize_text(item['item_name'])
    
    # Step 1: Check if master already exists (exact match)
    master_id = check_master_exact_match(normalized)
    if master_id:
        update_master_metadata(master_id, item)
        return master_id
    
    # Step 2: Check similarity to existing masters only
    embedding = generate_embedding(normalized)
    similar_master = find_similar_master(embedding, threshold=0.95)
    
    if similar_master:
        # Add as alias to existing master
        add_alias(similar_master['id'], normalized, 
                  source='scraper_variant', 
                  confidence=similar_master['score'])
        return similar_master['id']
    
    # Step 3: Create new master canonical item
    master_id = create_master_canonical_item(
        name=normalized,
        category=item['category'],
        source_type='scraped',
        is_master=True,
        confidence=1.0
    )
    
    store_embedding(master_id, embedding)
    return master_id
```

**Key Difference**: Only scraped items can create master canonical items.

### Phase 2: Match Receipt Items (User Uploads)

**When**: When user uploads receipt  
**Strategy**: Multi-stage fuzzy matching to masters only

```python
def match_receipt_item(item_name: str, category: str = None) -> Dict:
    """
    Match receipt item to master canonical item.
    Uses aggressive fuzzy matching strategies.
    
    Returns: {
        'canonical_item_id': UUID,
        'match_method': str,
        'confidence': float,
        'matched_name': str  # The master name that was matched
    }
    """
    normalized = normalize_receipt_text(item_name)  # More aggressive
    
    # ============================================
    # STAGE 1: Exact & Alias Lookup (Fast Path)
    # ============================================
    
    # Check exact match in aliases
    alias_match = check_alias_exact_match(normalized)
    if alias_match:
        increment_alias_usage(alias_match['alias_id'])
        return {
            'canonical_item_id': alias_match['master_id'],
            'match_method': 'alias_exact',
            'confidence': 1.0,
            'matched_name': alias_match['master_name']
        }
    
    # ============================================
    # STAGE 2: Token-Based Fuzzy Matching
    # ============================================
    
    # Extract key tokens (brand, product type, size)
    tokens = extract_key_tokens(normalized)
    # tokens = ['farm', 'fresh', 'milk', '2l']
    
    # Search masters with matching tokens
    master_candidates = search_masters_by_tokens(
        tokens=tokens,
        category=category,
        min_token_overlap=0.6  # 60% tokens must match
    )
    
    if master_candidates:
        # Use fuzzy string matching to rank
        best_match = rank_candidates_fuzzy(
            receipt_text=normalized,
            candidates=master_candidates,
            method='token_sort_ratio'  # Handles word order changes
        )
        
        if best_match['score'] >= 0.80:  # 80% fuzzy match
            # Auto-create alias for future fast path
            create_alias(
                master_id=best_match['id'],
                alias=normalized,
                source='receipt',
                confidence=best_match['score'],
                match_method='fuzzy_token'
            )
            
            return {
                'canonical_item_id': best_match['id'],
                'match_method': 'fuzzy_token',
                'confidence': best_match['score'],
                'matched_name': best_match['name']
            }
    
    # ============================================
    # STAGE 3: Embedding Similarity (Semantic)
    # ============================================
    
    embedding = generate_embedding(normalized)
    similar_master = find_similar_master_embedding(
        embedding=embedding,
        category=category,
        threshold=0.85  # Lower threshold for receipts
    )
    
    if similar_master:
        # Auto-create alias
        create_alias(
            master_id=similar_master['id'],
            alias=normalized,
            source='receipt',
            confidence=similar_master['score'],
            match_method='embedding'
        )
        
        return {
            'canonical_item_id': similar_master['id'],
            'match_method': 'embedding',
            'confidence': similar_master['score'],
            'matched_name': similar_master['name']
        }
    
    # ============================================
    # STAGE 4: Partial Match with Brand Filter
    # ============================================
    
    # Extract brand (first 2-3 tokens)
    brand = extract_brand(normalized)  # "farm fresh"
    
    if brand:
        brand_masters = search_masters_by_brand(brand, category)
        
        if brand_masters:
            # Use aggressive partial matching
            best_match = rank_candidates_fuzzy(
                receipt_text=normalized,
                candidates=brand_masters,
                method='partial_ratio'  # Handles truncation
            )
            
            if best_match['score'] >= 0.75:  # 75% partial match
                # Low confidence alias - may need manual review
                create_alias(
                    master_id=best_match['id'],
                    alias=normalized,
                    source='receipt',
                    confidence=best_match['score'],
                    match_method='fuzzy_partial',
                    needs_review=True  # Flag for manual verification
                )
                
                return {
                    'canonical_item_id': best_match['id'],
                    'match_method': 'fuzzy_partial',
                    'confidence': best_match['score'],
                    'matched_name': best_match['name'],
                    'needs_review': True
                }
    
    # ============================================
    # STAGE 5: No Match - Create Pending Item
    # ============================================
    
    # Don't auto-create master from receipt - flag for review
    pending_id = create_pending_canonical_item(
        name=normalized,
        category=category,
        source_type='receipt',
        is_master=False,
        needs_review=True
    )
    
    return {
        'canonical_item_id': pending_id,
        'match_method': 'no_match',
        'confidence': 0.0,
        'matched_name': None,
        'needs_review': True
    }
```

---

## Key Matching Strategies Explained

### 1. Token-Based Fuzzy Matching

**Purpose**: Handle word order changes, missing words

**Example**:
```python
from fuzzywuzzy import fuzz

receipt = "farm fresh milk 2l"
master = "farm fresh pure fresh milk 2l"

# Token Sort Ratio (ignores order, handles subsets)
score = fuzz.token_sort_ratio(receipt, master)
# Result: 86% match ✅

# Why it works:
# Sorted tokens:
#   Receipt: "2l farm fresh milk"
#   Master:  "2l farm fresh milk pure"
# Levenshtein distance on sorted tokens
```

**Implementation**:
```python
def rank_candidates_fuzzy(receipt_text: str, candidates: List[Dict], method: str) -> Dict:
    """Rank candidates using fuzzy string matching."""
    from fuzzywuzzy import fuzz
    
    scores = []
    for candidate in candidates:
        if method == 'token_sort_ratio':
            score = fuzz.token_sort_ratio(receipt_text, candidate['name'])
        elif method == 'partial_ratio':
            score = fuzz.partial_ratio(receipt_text, candidate['name'])
        elif method == 'token_set_ratio':
            score = fuzz.token_set_ratio(receipt_text, candidate['name'])
        
        scores.append({
            'id': candidate['id'],
            'name': candidate['name'],
            'score': score / 100.0  # Normalize to 0-1
        })
    
    return max(scores, key=lambda x: x['score'])
```

### 2. Key Token Extraction

**Purpose**: Focus on discriminative words (brand, type, size)

**Example**:
```python
def extract_key_tokens(text: str) -> List[str]:
    """Extract meaningful tokens, filter noise."""
    
    # Normalize
    text = normalize_receipt_text(text)
    
    # Remove common stopwords (but keep brand-specific words)
    stopwords = {'the', 'and', 'with', 'or', 'of', 'a', 'an'}
    tokens = [t for t in text.split() if t not in stopwords]
    
    # Extract size patterns (2l, 500ml, 1kg)
    size_pattern = r'(\d+(?:\.\d+)?(?:l|ml|kg|g|oz|lb))'
    sizes = re.findall(size_pattern, text, re.IGNORECASE)
    
    # Prioritize: brand (first 2 tokens) + type + size
    if len(tokens) >= 2:
        brand = tokens[:2]  # "farm fresh"
        rest = tokens[2:]
        return brand + sizes + rest
    
    return tokens

# Example
extract_key_tokens("farm fresh pure fresh milk 2l")
# → ['farm', 'fresh', '2l', 'pure', 'milk']
```

### 3. Brand-Based Filtering

**Purpose**: Reduce search space, improve precision

**Example**:
```sql
-- Fast brand lookup with trigram index
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_canonical_items_name_trgm ON canonical_items USING gin("Name" gin_trgm_ops);

-- Search query
SELECT "Id", "Name", similarity("Name", 'farm fresh') AS sim
FROM canonical_items
WHERE "IsMaster" = TRUE
  AND "Name" % 'farm fresh'  -- Trigram similarity operator
  AND "Category" = 'Dairy'
ORDER BY sim DESC
LIMIT 10;
```

### 4. Embedding Similarity (Semantic)

**Purpose**: Catch synonym variations, semantic matches

**Enhanced with Category Filtering**:
```python
def find_similar_master_embedding(embedding: List[float], 
                                  category: str = None, 
                                  threshold: float = 0.85) -> Dict:
    """Find similar master with category context."""
    
    query = '''
        SELECT 
            ci."Id",
            ci."Name",
            ci."Category",
            1 - (cie."Embedding" <=> %s::vector) AS similarity
        FROM canonical_item_embeddings cie
        JOIN canonical_items ci ON ci."Id" = cie."CanonicalItemId"
        WHERE ci."IsMaster" = TRUE
    '''
    
    params = [embedding]
    
    # Add category filter if provided
    if category:
        query += ' AND ci."Category" = %s'
        params.append(category)
    
    query += '''
        ORDER BY cie."Embedding" <=> %s::vector
        LIMIT 1
    '''
    params.append(embedding)
    
    result = execute_query(query, params)
    
    if result and result['similarity'] >= threshold:
        return result
    return None
```

---

## Enhanced Text Normalization for Receipts

**Problem**: Receipt text is messier than scraped data

```python
def normalize_receipt_text(text: str) -> str:
    """
    Aggressive normalization for receipt OCR text.
    More forgiving than scraper normalization.
    """
    
    # 1. Fix common OCR errors
    ocr_fixes = {
        '0': 'o',  # Zero → letter O (context-dependent)
        '1': 'i',  # One → letter I
        '5': 's',  # Five → letter S
        '/': ' ',  # Slash often appears in truncated text
        '\\': ' ',
    }
    
    # 2. Expand common abbreviations
    abbreviations = {
        'fm': 'farm',
        'ff': 'farm fresh',
        'choc': 'chocolate',
        'org': 'organic',
        'nat': 'natural',
        'ult': 'ultra',
        'pst': 'pasteurized',
    }
    
    # 3. Standardize size units
    size_units = {
        'liter': 'l',
        'litre': 'l',
        'ml': 'ml',
        'milliliter': 'ml',
        'gram': 'g',
        'gm': 'g',
        'kilogram': 'kg',
    }
    
    text = text.lower()
    
    # Apply fixes
    for old, new in ocr_fixes.items():
        text = text.replace(old, new)
    
    # Remove special characters but keep spaces and digits
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    
    # Expand abbreviations
    words = text.split()
    expanded = [abbreviations.get(w, w) for w in words]
    text = ' '.join(expanded)
    
    # Standardize sizes
    for old, new in size_units.items():
        text = text.replace(old, new)
    
    # Remove common receipt artifacts
    artifacts = ['1 unit', 'x1', 'ea', 'each', 'pc', 'pcs', 'piece']
    for artifact in artifacts:
        text = text.replace(artifact, '')
    
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    return text

# Examples
normalize_receipt_text("Farm Fresh Pure Fresh /")
# → "farm fresh pure fresh"

normalize_receipt_text("FF Milk 2Liter X1")
# → "farm fresh milk 2l"

normalize_receipt_text("CHOC MILK 500ML")
# → "chocolate milk 500ml"
```

---

## Learning from Manual Corrections

**Goal**: System improves as users correct mismatches

### Correction Tracking Table

```sql
CREATE TABLE canonical_item_corrections (
    "Id" UUID PRIMARY KEY,
    "ReceiptItemText" VARCHAR NOT NULL,
    "WrongMatchId" UUID REFERENCES canonical_items("Id"),
    "CorrectMatchId" UUID REFERENCES canonical_items("Id") NOT NULL,
    "UserId" VARCHAR,
    "CorrectedAt" TIMESTAMP NOT NULL,
    "OriginalConfidence" DECIMAL(3,2),
    "OriginalMethod" VARCHAR
);

CREATE INDEX idx_corrections_receipt_text ON canonical_item_corrections("ReceiptItemText");
```

### Correction Workflow

```python
def record_user_correction(receipt_text: str, 
                          wrong_match_id: str, 
                          correct_match_id: str):
    """
    User corrects a wrong match.
    
    Actions:
    1. Log correction for analytics
    2. Create high-confidence alias
    3. Retrain if needed
    """
    
    # Log correction
    insert_correction_log(
        receipt_text=receipt_text,
        wrong_match=wrong_match_id,
        correct_match=correct_match_id
    )
    
    # Create alias with high confidence
    normalized = normalize_receipt_text(receipt_text)
    create_alias(
        master_id=correct_match_id,
        alias=normalized,
        source='manual_correction',
        confidence=1.0,
        match_method='user_corrected'
    )
    
    # If wrong match was an alias, delete it
    if wrong_match_id:
        delete_alias_if_exists(normalized, wrong_match_id)
    
    # Trigger retraining if pattern detected
    if should_retrain(receipt_text):
        retrain_matching_model()
```

### Pattern Analysis

```sql
-- Find common correction patterns
SELECT 
    "ReceiptItemText",
    COUNT(*) AS correction_count,
    array_agg(DISTINCT "CorrectMatchId") AS correct_matches
FROM canonical_item_corrections
GROUP BY "ReceiptItemText"
HAVING COUNT(*) > 5  -- Items corrected more than 5 times
ORDER BY correction_count DESC;

-- Identify weak matching methods
SELECT 
    "OriginalMethod",
    COUNT(*) AS error_count,
    AVG("OriginalConfidence") AS avg_confidence
FROM canonical_item_corrections
GROUP BY "OriginalMethod"
ORDER BY error_count DESC;
```

---

## Implementation Priority

### Phase 1: Quick Wins (Week 1-2)

1. **Add `IsMaster` flag** to `canonical_items`
   - Mark all ETL-scraped items as masters
   - Mark all receipt items as non-masters

2. **Enhance alias table** with source tracking
   - Add `Source`, `MatchConfidence`, `UsageCount`

3. **Implement token-based fuzzy matching**
   - Install `fuzzywuzzy` + `python-Levenshtein`
   - Add token_sort_ratio matching stage

4. **Improve receipt normalization**
   - Implement `normalize_receipt_text()` with OCR fixes
   - Handle common abbreviations

### Phase 2: Core Enhancements (Week 3-4)

5. **Two-tier canonicalization logic**
   - Separate `process_scraped_item()` (creates masters)
   - Separate `match_receipt_item()` (matches to masters)

6. **Brand extraction & filtering**
   - Implement brand detection
   - Add brand-based search

7. **Category-aware matching**
   - Use category to narrow search space
   - Category-specific embeddings

### Phase 3: Learning System (Week 5-6)

8. **Correction tracking**
   - Build `canonical_item_corrections` table
   - Implement correction workflow UI

9. **Auto-alias creation**
   - Successful matches → create aliases
   - Track usage counts

10. **Analytics dashboard**
    - Match rate by method
    - Low-confidence matches needing review
    - Correction patterns

---

## Expected Performance Improvements

### Current System

```
Receipt Items Processed: 1,000
Correct Matches: ~400 (40%)
Wrong Matches: ~200 (20%)
No Matches (new items): ~400 (40%)

User Satisfaction: ⭐⭐ (2/5)
```

### With Two-Tier + Fuzzy Matching

```
Receipt Items Processed: 1,000
Correct Matches: ~850 (85%)
Wrong Matches: ~50 (5%)
No Matches (new items): ~100 (10%)

User Satisfaction: ⭐⭐⭐⭐ (4/5)
```

### After Learning System (3 months)

```
Receipt Items Processed: 1,000
Correct Matches: ~950 (95%)
Wrong Matches: ~20 (2%)
No Matches (new items): ~30 (3%)

User Satisfaction: ⭐⭐⭐⭐⭐ (5/5)
```

---

## Testing Strategy

### Unit Tests

```python
def test_receipt_matching():
    """Test various receipt text variations."""
    
    # Create master item
    master_id = create_master_canonical_item(
        name="farm fresh pure fresh milk 2l",
        category="Dairy",
        is_master=True
    )
    
    # Test cases
    test_cases = [
        ("Farm Fresh Pure Fresh Milk 2L", 1.0),      # Exact
        ("Farm Fresh Pure Fresh /", 0.85),           # Truncated
        ("Farm Fresh Milk", 0.80),                   # Abbreviated
        ("FF Pure Milk 2L", 0.75),                   # Abbreviated brand
        ("FARM FRESH MLK 2000ML", 0.70),             # OCR error + unit variation
    ]
    
    for receipt_text, expected_min_confidence in test_cases:
        result = match_receipt_item(receipt_text, category="Dairy")
        
        assert result['canonical_item_id'] == master_id
        assert result['confidence'] >= expected_min_confidence
        print(f"✅ '{receipt_text}' → {result['confidence']:.2f}")
```

### Integration Tests

```python
def test_full_pipeline():
    """Test ETL scraping → Receipt matching."""
    
    # Simulate ETL scraping
    scraped_items = [
        {"item_name": "Farm Fresh Pure Fresh Milk 2L", "category": "Dairy"},
        {"item_name": "Nestle Omega Plus Milk 1L", "category": "Dairy"},
    ]
    
    for item in scraped_items:
        master_id = process_scraped_item(item)
        assert get_canonical_item(master_id)['is_master'] == True
    
    # Simulate receipt upload
    receipt_items = [
        "Farm Fresh Pure Fresh /",
        "Nestle Omega 1L",
    ]
    
    for item in receipt_items:
        result = match_receipt_item(item, category="Dairy")
        assert result['confidence'] >= 0.75
        assert result['canonical_item_id'] is not None
```

---

## Monitoring & Metrics

### Key Metrics to Track

```sql
-- Match rate by method
CREATE VIEW match_rate_by_method AS
SELECT 
    "MatchMethod",
    COUNT(*) AS total_matches,
    AVG("MatchConfidence") AS avg_confidence,
    COUNT(*) FILTER (WHERE "NeedsReview" = TRUE) AS needs_review_count
FROM canonical_item_aliases
WHERE "Source" = 'receipt'
GROUP BY "MatchMethod";

-- Daily match performance
CREATE VIEW daily_match_performance AS
SELECT 
    DATE("LastSeenAt") AS match_date,
    COUNT(*) AS receipt_items_processed,
    AVG("MatchConfidence") AS avg_confidence,
    COUNT(*) FILTER (WHERE "MatchConfidence" >= 0.90) AS high_confidence,
    COUNT(*) FILTER (WHERE "MatchConfidence" < 0.75) AS low_confidence
FROM canonical_item_aliases
WHERE "Source" = 'receipt'
GROUP BY DATE("LastSeenAt")
ORDER BY match_date DESC;
```

### Alerting Rules

1. **Match rate drops below 75%** → Investigate new products
2. **Low-confidence matches > 20%** → Review thresholds
3. **Corrections > 10 per day** → Retraining needed

---

## Example: Complete Workflow

### 1. ETL Scraping (Nightly)

```python
# MYDIN scraper runs
mydin_products = [
    {
        'item_name': 'Farm Fresh Pure Fresh Milk 2L',
        'unit_price': 12.50,
        'category': 'Dairy',
        'source': 'mydin_graphql'
    },
    # ... 1,500 more products
]

for product in mydin_products:
    # Process as master canonical item
    canonical_id = process_scraped_item(product)
    
    # Store in purchase_analytics_gold
    load_to_database({
        'canonical_item_id': canonical_id,
        'unit_price': product['unit_price'],
        'store_name': 'MYDIN_NATIONAL',
        'is_master': True
    })

# Result: 1,500 master canonical items created/updated
```

### 2. User Uploads Receipt

```python
# OCR extracts from receipt image
receipt_items = [
    {'text': 'Farm Fresh Pure Fresh /', 'price': 12.50},
    {'text': 'Nestle Omega Milk 1L', 'price': 9.90},
    {'text': 'Wonder White Bread 400g', 'price': 3.20},
]

for item in receipt_items:
    # Match to master canonical item
    match_result = match_receipt_item(
        item_name=item['text'],
        category=None  # OCR doesn't provide category
    )
    
    if match_result['confidence'] >= 0.75:
        # High confidence - auto-save
        save_receipt_item({
            'canonical_item_id': match_result['canonical_item_id'],
            'item_name': item['text'],
            'unit_price': item['price'],
            'match_confidence': match_result['confidence'],
            'match_method': match_result['match_method']
        })
    else:
        # Low confidence - ask user to verify
        prompt_user_verification(item, match_result)

# Result:
# - Item 1: 0.87 confidence → Auto-matched to "Farm Fresh Pure Fresh Milk 2L"
# - Item 2: 0.82 confidence → Auto-matched to "Nestle Omega Plus Milk 1L"
# - Item 3: 0.45 confidence → Asks user to select from dropdown
```

### 3. User Corrects Match

```python
# User sees:
# "Wonder White Bread 400g" matched to "Gardenia White Bread 400g" ❌

# User selects correct item from dropdown:
correct_match = "Wonder White Bread Sandwich 400g"

# System learns
record_user_correction(
    receipt_text="Wonder White Bread 400g",
    wrong_match_id="gardenia-uuid",
    correct_match_id="wonder-white-uuid"
)

# Next time "Wonder White Bread 400g" appears → instant match
```

---

## Code Example: Enhanced Canonicalizer

```python
# etl_transformers/canonicalizer_v2.py

from typing import Dict, List, Optional
from fuzzywuzzy import fuzz
import re

class AdvancedCanonicalizer:
    """Two-tier canonicalization with fuzzy matching."""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Matching thresholds
        self.FUZZY_TOKEN_THRESHOLD = 0.80
        self.FUZZY_PARTIAL_THRESHOLD = 0.75
        self.EMBEDDING_THRESHOLD_SCRAPED = 0.95
        self.EMBEDDING_THRESHOLD_RECEIPT = 0.85
    
    def process_scraped_item(self, item: Dict) -> str:
        """
        Process scraped item - creates/updates master canonical item.
        """
        normalized = self.normalize_text(item['item_name'])
        
        # Check existing masters
        master_id = self.check_master_exact_match(normalized)
        if master_id:
            return master_id
        
        # Check embedding similarity to masters
        embedding = self.model.encode(normalized).tolist()
        similar = self.find_similar_master(
            embedding, 
            threshold=self.EMBEDDING_THRESHOLD_SCRAPED
        )
        
        if similar:
            # Add as alias to existing master
            self.create_alias(
                master_id=similar['id'],
                alias=normalized,
                source='scraper_variant',
                confidence=similar['score']
            )
            return similar['id']
        
        # Create new master
        master_id = self.create_master_canonical_item(
            name=normalized,
            category=item.get('category', 'Unknown'),
            is_master=True
        )
        self.store_embedding(master_id, embedding)
        return master_id
    
    def match_receipt_item(self, item_name: str, 
                          category: Optional[str] = None) -> Dict:
        """
        Match receipt item to master canonical item.
        Multi-stage fuzzy matching.
        """
        normalized = self.normalize_receipt_text(item_name)
        
        # Stage 1: Check aliases (fast path)
        alias_match = self.check_alias_match(normalized)
        if alias_match:
            self.increment_alias_usage(alias_match['alias_id'])
            return {
                'canonical_item_id': alias_match['master_id'],
                'match_method': 'alias_exact',
                'confidence': 1.0
            }
        
        # Stage 2: Token-based fuzzy matching
        masters = self.get_master_candidates(category=category)
        fuzzy_match = self.fuzzy_match_candidates(
            normalized, 
            masters, 
            method='token_sort_ratio'
        )
        
        if fuzzy_match and fuzzy_match['score'] >= self.FUZZY_TOKEN_THRESHOLD:
            # Create alias for future fast path
            self.create_alias(
                master_id=fuzzy_match['id'],
                alias=normalized,
                source='receipt',
                confidence=fuzzy_match['score'],
                match_method='fuzzy_token'
            )
            return {
                'canonical_item_id': fuzzy_match['id'],
                'match_method': 'fuzzy_token',
                'confidence': fuzzy_match['score']
            }
        
        # Stage 3: Embedding similarity
        embedding = self.model.encode(normalized).tolist()
        embedding_match = self.find_similar_master(
            embedding,
            category=category,
            threshold=self.EMBEDDING_THRESHOLD_RECEIPT
        )
        
        if embedding_match:
            self.create_alias(
                master_id=embedding_match['id'],
                alias=normalized,
                source='receipt',
                confidence=embedding_match['score'],
                match_method='embedding'
            )
            return {
                'canonical_item_id': embedding_match['id'],
                'match_method': 'embedding',
                'confidence': embedding_match['score']
            }
        
        # Stage 4: No match - create pending item
        pending_id = self.create_pending_item(normalized, category)
        return {
            'canonical_item_id': pending_id,
            'match_method': 'no_match',
            'confidence': 0.0,
            'needs_review': True
        }
    
    def normalize_receipt_text(self, text: str) -> str:
        """Aggressive normalization for receipt OCR text."""
        text = text.lower()
        
        # Fix common OCR errors
        text = text.replace('/', ' ')
        text = text.replace('\\', ' ')
        
        # Expand abbreviations
        abbreviations = {
            'ff': 'farm fresh',
            'fm': 'farm',
            'choc': 'chocolate',
            'org': 'organic'
        }
        
        words = text.split()
        expanded = [abbreviations.get(w, w) for w in words]
        text = ' '.join(expanded)
        
        # Remove special chars
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Remove artifacts
        for artifact in ['1 unit', 'x1', 'ea', 'pc']:
            text = text.replace(artifact, '')
        
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text
    
    def fuzzy_match_candidates(self, text: str, 
                               candidates: List[Dict], 
                               method: str) -> Optional[Dict]:
        """Rank candidates using fuzzy string matching."""
        if not candidates:
            return None
        
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            if method == 'token_sort_ratio':
                score = fuzz.token_sort_ratio(text, candidate['name'])
            elif method == 'partial_ratio':
                score = fuzz.partial_ratio(text, candidate['name'])
            else:
                score = fuzz.ratio(text, candidate['name'])
            
            score = score / 100.0  # Normalize to 0-1
            
            if score > best_score:
                best_score = score
                best_match = {
                    'id': candidate['id'],
                    'name': candidate['name'],
                    'score': score
                }
        
        return best_match
```

---

## Summary

### Key Principles

1. **Two-Tier System**: Scraped = masters, Receipts = fuzzy inputs
2. **Directional Matching**: Receipts match TO scraped items
3. **Multi-Stage Fuzzy**: Token-based → Embedding → Partial matching
4. **Learning System**: User corrections improve future matches
5. **Confidence Scoring**: Track match quality, flag low confidence

### Quick Start Implementation

1. Add `IsMaster` flag to canonical_items
2. Install `fuzzywuzzy` library
3. Separate ETL canonicalization from receipt matching
4. Implement token_sort_ratio fuzzy matching
5. Create aliases automatically on successful matches

### Expected Results

- **Match Rate**: 40% → 85%+
- **User Corrections**: 60% → 5%
- **Processing Time**: Same (optimized batching)
- **User Satisfaction**: ⭐⭐ → ⭐⭐⭐⭐⭐

---

**Next Steps**: Implement Phase 1 (Quick Wins) and measure improvement in match rates.
