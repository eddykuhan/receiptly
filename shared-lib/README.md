# Receiptly Core - Shared Canonicalization Library

Shared library for product canonicalization used across Receiptly services.

## Components

### AttributeExtractor
Extracts structured attributes from product names:
- Brand detection (300+ Malaysian brands)
- Size extraction and normalization (g, kg, ml, L)
- Pack count detection (multi-packs vs singles)
- Variant detection (flavors, types)

### AmazonStyleMatcher
Implements Amazon's product matching approach:
- **Hard Constraints**: Rejects non-viable matches
  - Pack count must match exactly
  - Size within 5% tolerance
  - Brand must match (if present)
- **Weighted Scoring**: Ranks viable candidates
  - Brand: 25%
  - Size: 30%
  - Text similarity: 25%
  - Token overlap: 10%
  - Price: 10%

### CandidateGenerator
Generates candidate pool for matching:
- Brand-based filtering
- Size range filtering
- Vector similarity search

### Normalizer
Text normalization utilities for consistent matching.

## Installation

### Development (Editable)
```bash
# Install in retail-etl
cd /path/to/receiptly/retail-etl
pip install -e ../shared-lib

# Install in llm_service
cd /path/to/receiptly/llm_service
pip install -e ../shared-lib
```

### Production
```bash
pip install /path/to/receiptly/shared-lib
```

## Usage

```python
from receiptly_core import AttributeExtractor, AmazonStyleMatcher

# Extract attributes
extractor = AttributeExtractor()
attrs = extractor.extract_all_attributes("Milo Activ-Go 1kg")
# {'brand': 'Milo', 'size': '1kg', 'pack_count': 1, ...}

# Match with candidates
matcher = AmazonStyleMatcher()
best_match, score, breakdown = matcher.find_best_match(
    query_attributes=attrs,
    candidates=candidate_list,
    threshold=0.75
)
```

## Version

0.1.0 - Initial release with core canonicalization components
