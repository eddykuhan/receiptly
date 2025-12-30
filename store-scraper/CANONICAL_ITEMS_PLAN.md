# Canonical Items Plan

## 1. Purpose

The purpose of the **Canonical Items layer** is to establish a **single, stable definition of “what an item is”** across the platform.

It answers the question:

> “Are these different item names referring to the same product?”

This layer exists to decouple **item identity** from:
- Pricing
- Stores
- Geography
- User uploads
- Scraper data

---

## 2. What Canonical Items Are (and Are Not)

### Canonical Items ARE
- A stable identifier for a product (SKU-level abstraction)
- Shared across receipts, scrapers, analytics, and maps
- The source for search suggestions
- The join key for pricing (Gold layer)

### Canonical Items ARE NOT
- Price holders
- Store-specific
- Time-dependent
- Fuzzy or probabilistic at query time

All ambiguity is resolved **before** data reaches Gold.

---

## 3. Core Tables

### 3.1 canonical_items
Defines the product identity.

```
canonical_items
- canonical_item_id
- display_name
- normalized_name
- brand
- category
- size_value
- size_unit
- created_at
```

---

### 3.2 canonical_item_embeddings
Used only for semantic search and matching.

```
canonical_item_embeddings
- canonical_item_id
- embedding
- embedding_version
- created_at
```

---

### 3.3 canonical_item_aliases
Captures how items appear in the real world.

```
canonical_item_aliases
- alias_text
- canonical_item_id
- source
- confidence_score
- created_at
```

Aliases are learning signals and must never be deleted.

---

## 4. When Canonical Items Are Created

Canonical items are created **immediately** when a previously unseen item is encountered.

Creation happens in three situations:
1. User receipt upload (real-time)
2. Scraper ingestion (batch)
3. User correction feedback

There is no nightly or delayed canonical creation job.

---

## 5. Canonicalization Flow (Unified)

### Step 1: Normalize Raw Item Text
- Lowercase
- Remove punctuation
- Normalize units
- Extract brand if possible

### Step 2: Alias Lookup (Fast Path)
Exact match on normalized alias.

### Step 3: Vector Similarity Match
- ≥ 0.90 → auto-match
- 0.80–0.89 → match + flag
- < 0.80 → create new canonical item

### Step 4: Create Canonical Item (If Needed)
Create canonical item, embedding, and alias.

### Step 5: Always Store Alias
All observed forms are stored for learning.

---

## 6. Interaction with Pricing (Gold Layer)

Canonical items must exist **before** any price is written.

Gold tables reference:
```
canonical_item_id
```

Gold never performs fuzzy matching or vector search.

---

## 7. Search Bar Behavior

- Suggestions query `canonical_items`
- Item selection returns `canonical_item_id`
- Prices are resolved later from Gold

---

## 8. User Corrections

- Original alias retained
- Corrected alias added
- Confidence boosted

Canonical items are not rewritten.

---

## 9. De-duplication & Merging (Future)

Duplicate canonicals can be merged via explicit, auditable process.

---

## 10. Key Principles

- Canonical items are created on first sight
- Aliases accumulate
- Vectors live outside Gold
- Gold consumes canonical IDs only
- Search = what item
- Gold = what price
- Map = where to buy
