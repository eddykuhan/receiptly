# Gold Layer Implementation Summary

## Overview
Implemented an append-only `purchase_analytics_gold` table for price history analysis by location and time. This enables fast price map queries without joins while preserving complete price history even after receipts are deleted.

## Components Implemented

### 1. Domain Model
**File:** `Receiptly.Domain/Models/PurchaseAnalyticsGold.cs`
- Denormalized table combining Item + Receipt fields
- Includes location data (Latitude, Longitude) for price map
- Tracks corrections (IsCorrected, CorrectedAt)
- Append-only: no UpdatedAt field

### 2. Database Configuration
**File:** `Receiptly.Infrastructure/Data/ApplicationDbContext.cs`
- DbSet<PurchaseAnalyticsGold> added
- Indexes created for:
  - `item_id` - Fast correction updates
  - `purchase_date` - Time-series queries
  - `store_name` - Store filtering
  - `canonical_name` - Product grouping
  - `(latitude, longitude)` - Geographic queries
  - `(canonical_name, purchase_date, latitude, longitude)` - Combined analytics

### 3. Service Layer
**Files:**
- `Receiptly.Core/Interfaces/IGoldLayerService.cs`
- `Receiptly.Infrastructure/Services/GoldLayerService.cs`

**Methods:**
- `AppendItemsAsync()` - Insert new items from receipt upload
- `UpdateCorrectionsAsync()` - Update canonical names when corrections applied

### 4. Integration Points

#### Receipt Processing
**File:** `Receiptly.Infrastructure/Services/ReceiptProcessingService.cs`
- Calls `AppendItemsAsync()` after successful receipt creation
- Items already have `CanonicalName` populated from `CanonicalizationService`

#### Corrections
**File:** `Receiptly.Core/Services/ReceiptCorrectionService.cs`
- Tracks item name corrections in dictionary
- Calls `UpdateCorrectionsAsync()` to sync to gold layer
- Uses `ExecuteUpdateAsync` for efficient bulk updates

#### Analytics
**File:** `Receiptly.Infrastructure/Services/PurchaseAnalyticsService.cs`
- Queries `PurchaseAnalyticsGold` directly (no joins)
- Filters by `Latitude IS NOT NULL AND Longitude IS NOT NULL` for map queries
- Removed `ApplyCorrectionsToRecordsAsync()` - corrections already in gold layer
- Removed dependency on `IReceiptCorrectionService`

### 5. Dependency Injection
**File:** `Receiptly.API/Configuration/ServiceCollectionExtensions.cs`
- Registered `IGoldLayerService` → `GoldLayerService` as scoped

### 6. Database Migration
**Migration:** `AddPurchaseAnalyticsGoldLayer`
- Creates `purchase_analytics_gold` table
- Creates all performance indexes
- Sets default values for `is_corrected` (false) and `created_at` (CURRENT_TIMESTAMP)

### 7. Backfill Script
**File:** `dotnet-api/database/backfill_gold_layer.sql`
- Populates gold layer from existing `items` + `receipts` data
- LEFT JOIN with `canonical_cache` to include corrected names
- Sets `is_corrected = true` where canonical name came from cache
- Provides summary statistics after insert

## Data Flow

### New Receipt Upload
```
1. OCR → Receipt + Items created
2. CanonicalizationService → Item.CanonicalName populated
3. ReceiptRepository.CreateAsync() → Receipt saved to DB
4. GoldLayerService.AppendItemsAsync() → Gold records inserted
```

### User Corrections
```
1. User corrects item name
2. ReceiptCorrectionService.ApplyCorrectionsAsync()
   - Updates Receipt.Items in memory
   - Tracks corrections in dictionary
3. GoldLayerService.UpdateCorrectionsAsync()
   - Bulk UPDATE using ExecuteUpdateAsync
   - Sets CanonicalName, IsCorrected = true, CorrectedAt
```

### Price Map Analytics
```
1. PurchaseAnalyticsService.GetPurchasesAsync()
2. Query gold layer directly:
   - Filter by date range
   - Filter by store name
   - Filter by product name (canonical)
   - Filter by location bounds (lat/long)
   - WHERE latitude IS NOT NULL AND longitude IS NOT NULL
3. Return denormalized data (no joins needed)
```

## Key Design Decisions

### 1. Append-Only for Purchases
✅ New receipt uploaded → INSERT new records  
✅ Receipt hard deleted → Gold records remain (preserve price history)  
❌ Receipt metadata updated → No action (keep original snapshot)  
⚠️ Corrections applied → UPDATE existing records in-place (not new snapshot)

**Rationale:** Each purchase happened at one specific location/time. Updates would duplicate the same purchase. Corrections fix OCR errors, not create new price points.

### 2. Canonical Cache Integration
- `canonical_cache` remains **LLM-exclusive**
- User corrections update gold layer only, not canonical_cache
- Gold layer reads from `Item.CanonicalName` (already populated from cache)
- Backfill script LEFT JOINs canonical_cache for historical data

### 3. Location Filtering
- Gold layer stores ALL items (regardless of lat/long)
- Price map queries filter by `WHERE latitude IS NOT NULL AND longitude IS NOT NULL`
- Enables broader analytics in future while serving map use case

### 4. Performance Optimizations
- Denormalized structure eliminates joins
- Composite indexes for common query patterns
- `ExecuteUpdateAsync` for efficient bulk corrections
- `AsNoTracking()` for read-only analytics queries

## Migration Instructions

### 1. Apply Migration
```bash
cd dotnet-api
dotnet ef database update --project src/Receiptly.Infrastructure --startup-project src/Receiptly.API
```

### 2. Run Backfill Script
```bash
# Connect to PostgreSQL
psql -h <RDS_HOST> -U <USERNAME> -d receiptly

# Run backfill
\i database/backfill_gold_layer.sql
```

### 3. Verify
```sql
-- Check record counts
SELECT COUNT(*) FROM purchase_analytics_gold;

-- Check location coverage
SELECT 
  COUNT(*) AS total_records,
  SUM(CASE WHEN latitude IS NOT NULL THEN 1 ELSE 0 END) AS with_location,
  SUM(CASE WHEN is_corrected THEN 1 ELSE 0 END) AS corrected
FROM purchase_analytics_gold;
```

## Testing Considerations

### Unit Tests Updated
- `PurchaseAnalyticsServiceTests.cs` - Removed `IReceiptCorrectionService` from constructor
- All 3 test cases updated and passing

### Integration Testing Needed
1. **New receipt upload** - Verify gold records created
2. **User corrections** - Verify canonical name updated in gold layer
3. **Price map query** - Verify only records with lat/long returned
4. **Receipt deletion** - Verify gold records remain
5. **Backfill** - Verify existing data populated correctly

## Future Enhancements

### Potential Additions
1. **Restore functionality** - Admin interface to view/restore deleted receipts using gold layer
2. **Price trend analysis** - Time-series queries on gold layer for product price changes
3. **Store comparison** - Compare prices across different store locations
4. **Data retention** - Add `archived_at` for old records to separate hot/cold storage
5. **Batch corrections** - Bulk update canonical names across multiple items

### Monitoring
- Track gold layer size growth over time
- Monitor query performance on composite indexes
- Log sync failures between transactional tables and gold layer
