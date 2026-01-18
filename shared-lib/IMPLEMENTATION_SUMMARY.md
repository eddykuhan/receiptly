# Shared Library Implementation Complete

## Summary

Successfully created `receiptly-core` shared library for product canonicalization used across both retail ETL and receipt upload flows.

## Architecture

```
receiptly/
├── shared-lib/                    ← NEW: Shared canonicalization library
│   ├── setup.py                   # Package configuration
│   ├── README.md                   # Documentation
│   ├── receiptly_core/
│   │   ├── __init__.py            # Public API exports
│   │   ├── attribute_extractor.py # Brand, size, pack_count extraction
│   │   ├── matcher.py             # Amazon-style matching (hard constraints + scoring)
│   │   ├── candidate_generator.py # Candidate pool generation
│   │   └── normalizer.py          # Text normalization utilities
├── retail-etl/                    # Uses receiptly-core
│   ├── requirements-shared.txt    # receiptly-core>=0.1.0
├── llm_service/                   # Uses receiptly-core
│   ├── requirements-shared.txt    # receiptly-core>=0.1.0
```

## Components

### 1. AttributeExtractor
- **Brands**: 300+ Malaysian brands (Milo, F&N, Farm Fresh, Dutch Lady, etc.)
- **Size**: Extracts and normalizes (g, kg, ml, L)
- **Pack Count**: Detects multi-packs (`"200g x 2"` → `pack_count=2`)
- **Variant**: Flavor/type detection

### 2. AmazonStyleMatcher
**Hard Constraints** (must ALL pass):
- Pack count exact match (2-pack ≠ single pack)
- Size within ±5% tolerance
- Brand exact match (if both present)

**Weighted Scoring** (for viable candidates):
- Brand: 25%
- Size: 30%
- Text similarity: 25%
- Token overlap: 10%
- Price: 10%

Threshold: 0.75 minimum

### 3. CandidateGenerator
Generates candidate pool using:
- Brand + size filtering
- Category filtering
- Token overlap (GIN index)

### 4. Normalizer
Text normalization for consistent matching:
- Lowercase
- Remove special characters
- Remove "1 unit" suffix
- Normalize whitespace

## Installation

```bash
# Install in both environments (editable mode for development)
cd /Users/kuhan/Projects/receiptly/retail-etl
pip install -e ../shared-lib

cd /Users/kuhan/Projects/receiptly/llm_service
pip install -e ../shared-lib
```

## Usage

### Retail ETL (Already Using)
```python
from receiptly_core import AttributeExtractor, AmazonStyleMatcher, CandidateGenerator

# Existing code continues to work with wrapper methods
canonicalizer = Canonicalizer(db_config)
canonical_id = canonicalizer.process_scraped_item("Nescafe Gold Jars 200g x 2")
```

### Receipt Upload (Updated)
```python
from receiptly_core import AttributeExtractor, AmazonStyleMatcher, CandidateGenerator

# Extract attributes
query_attrs = attribute_extractor.extract_all_attributes("Nescafe Gold Jars 200g x 2")
# {'brand': 'Nescafe', 'size_normalized': 200.0, 'size_unit': 'G', 'pack_count': 2}

# Generate candidates
candidates = candidate_gen.generate_candidates(
    brand=query_attrs.get('brand'),
    size_normalized=query_attrs.get('size_normalized'),
    size_unit=query_attrs.get('size_unit'),
    category="Unknown",
    name_tokens=["nescafe", "gold", "jars", "200g", "x", "2"]
)

# Match with hard constraints
best_match, score, breakdown = matcher.find_best_match(
    query_attributes=query_attrs,
    candidates=candidates,
    threshold=0.75
)
```

## Testing Results

✅ **Test Case**: Multi-pack vs Single-pack differentiation

```python
# Input 1: "Nescafe Gold Jars 200g x 2"
# → pack_count=2
# → Canonical ID: 1c59661f-78e3-4780-9554-85ef6b2e9fb8

# Input 2: "Nescafe Gold Jar 200g"
# → pack_count=1
# → Canonical ID: 70fadf02-5f01-4e2e-9cf2-79f2d2fa9c54

# Result: Different IDs ✅
# Hard constraint (pack_count must match) working correctly!
```

## Benefits

1. **Single Source of Truth**: One canonicalization logic for both flows
2. **Consistency**: Receipt uploads now use same AttributeExtractor as ETL
3. **Hard Constraints**: Prevents incorrect matching (multi-pack vs single)
4. **Maintainability**: Update logic once, applies everywhere
5. **Testability**: Shared components can be tested independently

## Files Updated

### Created
- `/shared-lib/setup.py`
- `/shared-lib/receiptly_core/__init__.py`
- `/shared-lib/receiptly_core/attribute_extractor.py` (from retail-etl)
- `/shared-lib/receiptly_core/matcher.py` (from retail-etl)
- `/shared-lib/receiptly_core/candidate_generator.py` (from retail-etl)
- `/shared-lib/receiptly_core/normalizer.py`
- `/shared-lib/README.md`
- `/retail-etl/requirements-shared.txt`
- `/llm_service/requirements-shared.txt`

### Modified
- `/retail-etl/etl_transformers/canonicalizer.py` (imports from receiptly_core)
- `/llm_service/services/canonicalizer.py` (rewritten to use receiptly_core)

## Next Steps

1. ✅ Shared library created and installed
2. ✅ Receipt upload flow updated to use shared components
3. ✅ Tested multi-pack differentiation (hard constraints working)
4. ⏳ Monitor ETL rebuild (running in background)
5. 🔄 Test full receipt upload flow with real receipts
6. 📊 Compare canonicalization accuracy before/after

## Rollback Plan

If issues arise:
```bash
# Retail ETL: Revert to local imports
cd /Users/kuhan/Projects/receiptly/retail-etl
pip uninstall receiptly-core
# Edit canonicalizer.py: from .attribute_extractor import AttributeExtractor

# LLM Service: Revert to old canonicalizer
cd /Users/kuhan/Projects/receiptly/llm_service
pip uninstall receiptly-core
git checkout services/canonicalizer.py
```

## Version History

- **v0.1.0** (2026-01-03): Initial shared library release
  - AttributeExtractor with fixed pack count regex
  - AmazonStyleMatcher with hard constraints
  - CandidateGenerator for efficient candidate pooling
  - Normalizer utilities
