# Category Deduplication Analysis

## Problem Summary

The `/analytics/categories` endpoint returns **duplicate categories with variations** in spelling, capitalization, and whitespace:

```
- "beverages" vs "Beverages"
- "Yogurt" vs "Yoghurt"
- "UHT Milk" vs "UHT Milk " (trailing space)
- "chilled and frozen" vs "Chilled and Frozen"
- "Ros???ÿWine" vs "Rosé Wine" (encoding issue)
```

**Root Causes:**
1. **Multiple data sources** (Jaya Grocer, Mydin, Lotus's, Aeon, Village Grocer)
2. **No case normalization** in database storage
3. **No whitespace trimming** in data ingestion
4. **UTF-8 encoding issues** in some sources
5. **Category stored as-is** from OCR without standardization

---

## Data Flow Analysis

```
[Receipt OCR] → [Item.Category] → [PurchaseAnalyticsGold.Category] → [GetCategoriesAsync()] → [API Response]
```

### Current Implementation

**File:** `PurchaseAnalyticsService.GetCategoriesAsync()` 
**Location:** `/dotnet-api/src/Receiptly.Infrastructure/Services/PurchaseAnalyticsService.cs` (lines 519-528)

```csharp
public async Task<List<string>> GetCategoriesAsync(CancellationToken cancellationToken = default)
{
    return await _context.PurchaseAnalyticsGold
        .AsNoTracking()
        .Where(g => g.Category != null)
        .Select(g => g.Category!)
        .Distinct()           // ❌ Case-sensitive distinct
        .OrderBy(c => c)
        .ToListAsync(cancellationToken);
}
```

**Problem:** `Distinct()` is case-sensitive in PostgreSQL. "Yogurt" ≠ "yogurt" ≠ "Yoghurt"

---

## Root Cause Breakdown

### 1. **Multiple Data Sources with Different Conventions**

Each retailer uses different category naming:
- **Jaya Grocer**: "Beverages", "Yogurt"
- **Mydin**: "beverages", "yogurt" 
- **Lotus's**: "Chilled and Frozen", "UHT Milk "
- **Aeon**: Case-mixed naming
- **Village Grocer**: "Yoghurt" (British spelling)

### 2. **No Normalization in ETL**

The `load_gold_layer.py` defines `GROCERY_CATEGORIES` but doesn't normalize:
- Doesn't enforce case (lowercase or title case)
- Doesn't trim whitespace
- Doesn't validate against standard list

### 3. **Database Storage As-Is**

Categories are stored directly from Item.Category without transformation:
```csharp
Category = item.Category  // ❌ Stored raw, no normalization
```

### 4. **UTF-8 Encoding Issues**

Some categories have mangled UTF-8:
- "Ros???ÿWine" should be "Rosé Wine"
- Likely from web scraping with encoding mismatch

---

## Solution Architecture

### **Option 1: Database-Level Deduplication (Recommended)**
Normalize categories in the query itself.

**Pros:**
- ✅ Zero data changes
- ✅ Works with existing data
- ✅ Can be deployed immediately
- ✅ Handles future duplicates automatically

**Cons:**
- ❌ Doesn't fix root cause
- ❌ Performance cost (LOWER, TRIM in each query)

### **Option 2: Data Cleanup + Normalization Service**
Create a category canonicalization service.

**Pros:**
- ✅ Fixes root cause
- ✅ Better performance
- ✅ Centralized category management
- ✅ Enables category grouping

**Cons:**
- ❌ Requires data migration
- ❌ More complex implementation

### **Option 3: Hybrid Approach (Best)**
1. Implement database normalization immediately (Option 1)
2. Add category normalization service for future data (Option 2)
3. Create migration to clean existing data

---

## Implementation Plan

### **Phase 1: Immediate Fix (Database Query)**

**File:** `PurchaseAnalyticsService.cs`

```csharp
public async Task<List<string>> GetCategoriesAsync(CancellationToken cancellationToken = default)
{
    return await _context.PurchaseAnalyticsGold
        .AsNoTracking()
        .Where(g => g.Category != null)
        .Select(g => EF.Functions.ToLower(g.Category!.Trim()))  // Normalize
        .Distinct()
        .OrderBy(c => c)
        .ToListAsync(cancellationToken);
}
```

**Issue:** Returns lowercase, but UI expects title case.

**Better Approach:**

```csharp
public async Task<List<string>> GetCategoriesAsync(CancellationToken cancellationToken = default)
{
    var categories = await _context.PurchaseAnalyticsGold
        .AsNoTracking()
        .Where(g => g.Category != null)
        .Select(g => EF.Functions.ToLower(g.Category!.Trim()))
        .Distinct()
        .OrderBy(c => c)
        .ToListAsync(cancellationToken);
    
    // Return with proper title casing
    return categories.Select(c => TitleCaseCategory(c)).ToList();
}

private string TitleCaseCategory(string category)
{
    // Normalize to title case
    var words = category.Split(' ', '-');
    return string.Join(" ", words.Select(w => 
        char.ToUpper(w[0]) + w.Substring(1).ToLower()
    ));
}
```

### **Phase 2: Category Normalization Service**

**New File:** `CategoryNormalizationService.cs`

```csharp
public class CategoryNormalizationService
{
    // Standard category mapping
    private static readonly Dictionary<string, string> CategoryAliases = new()
    {
        // Spelling variations
        {"yogurt", "Yogurt"},
        {"yoghurt", "Yogurt"},
        
        // Case variations
        {"beverages", "Beverages"},
        {"chilled and frozen", "Chilled and Frozen"},
        {"food essentials", "Food Essentials"},
        
        // Whitespace issues
        {"uht milk ", "UHT Milk"},
        {"adult milk ", "Adult Milk"},
        
        // Encoding issues
        {"ros ÿwine", "Rosé Wine"},
    };
    
    public string Normalize(string category)
    {
        if (string.IsNullOrWhiteSpace(category))
            return "Unknown";
            
        var normalized = category.Trim();
        var lowerKey = normalized.ToLower();
        
        if (CategoryAliases.TryGetValue(lowerKey, out var canonical))
            return canonical;
            
        // Default: title case
        return TitleCase(normalized);
    }
    
    private string TitleCase(string text)
    {
        var words = text.Split(' ', '-');
        return string.Join(" ", words.Select(w =>
            char.ToUpper(w[0]) + w.Substring(1).ToLower()
        ));
    }
}
```

### **Phase 3: Data Migration**

```sql
-- Backfill existing categories with normalization
UPDATE purchase_analytics_gold
SET "Category" = CASE 
    -- Spelling variations
    WHEN LOWER(TRIM("Category")) = 'yogurt' THEN 'Yogurt'
    WHEN LOWER(TRIM("Category")) = 'yoghurt' THEN 'Yogurt'
    
    -- Case variations
    WHEN LOWER(TRIM("Category")) = 'beverages' THEN 'Beverages'
    WHEN LOWER(TRIM("Category")) = 'chilled and frozen' THEN 'Chilled and Frozen'
    
    -- Whitespace variations
    WHEN LOWER(TRIM("Category")) = 'uht milk' THEN 'UHT Milk'
    
    -- Default: title case
    ELSE INITCAP(TRIM("Category"))
END
WHERE "Category" IS NOT NULL;
```

---

## Priority Issues

### **High Priority (User-Facing)**
1. ❌ "Yogurt" vs "Yoghurt" - Directly confuses users
2. ❌ "beverages" vs "Beverages" - Inconsistent UI display
3. ❌ "Ros???ÿWine" - Broken display

### **Medium Priority (Data Quality)**
1. Trailing whitespace ("UHT Milk ")
2. Case variations in category filter
3. Consistency across sources

### **Low Priority (Analytics)**
1. Category distribution accuracy
2. Filter performance

---

## Implementation Recommendations

### **Short Term (This Week)**
1. Implement Phase 1 (database-level normalization)
2. Update `GetCategoriesAsync()` with LOWER + TRIM
3. Test with existing data
4. Deploy to staging

### **Medium Term (This Sprint)**
1. Build `CategoryNormalizationService`
2. Create data migration script
3. Update ETL to use normalization
4. Backfill all categories in database

### **Long Term (Next Release)**
1. Add category validation in ETL pipeline
2. Create category whitelist/dictionary
3. Implement category reconciliation service
4. Monitor for new duplicate patterns

---

## Code Changes Required

### **1. Update PurchaseAnalyticsService.cs**

```csharp
// Before
.Select(g => g.Category!)
.Distinct()

// After
.Select(g => NormalizeCategory(g.Category!))
.Distinct()

private static string NormalizeCategory(string category)
{
    return category?.Trim().ToLower() ?? string.Empty;
}
```

### **2. Create CategoryNormalization Helper**

Can be in `PurchaseAnalyticsService` or separate utility class.

### **3. Update ETL Process**

Ensure `load_gold_layer.py` and scrapers normalize categories before database insert.

---

## Testing Strategy

```csharp
[Fact]
public async Task GetCategories_ShouldDeduplicate_CaseVariations()
{
    // Arrange: Insert "Yogurt", "yogurt", "YOGURT"
    // Act: Call GetCategoriesAsync()
    // Assert: Should return only one entry
}

[Fact]
public async Task GetCategories_ShouldTrimWhitespace()
{
    // Arrange: Insert "UHT Milk" and "UHT Milk "
    // Act: Call GetCategoriesAsync()
    // Assert: Should return only one entry
}

[Fact]
public async Task GetCategories_ShouldNormalizeSpelling()
{
    // Arrange: Insert "Yogurt" and "Yoghurt"
    // Act: Call GetCategoriesAsync()
    // Assert: Should return only one entry
}
```

---

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `PurchaseAnalyticsService.cs` | Add normalization to query | High |
| `CategoryNormalizationService.cs` | New service for normalization | High |
| `load_gold_layer.py` | Apply normalization in ETL | Medium |
| `*.scraper.py` | Validate categories before storing | Medium |
| Migration script | Backfill normalized categories | High |

---

## Next Steps

1. **Run data audit** to identify all duplicate patterns
2. **Create CategoryNormalizationService** 
3. **Update GetCategoriesAsync()** query
4. **Write unit tests** for normalization
5. **Execute data migration** to backfill
6. **Verify in UI** that duplicates are gone

---

## Related Issues

- **Item Canonicalization:** Follows same pattern but at item level
- **Store Name Deduplication:** Similar issue with store names
- **Encoding Issues:** Need UTF-8 validation in scrapers
