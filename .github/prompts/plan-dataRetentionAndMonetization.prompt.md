# Data Retention and Monetization Strategy for Receiptly

## Problem Statement

When users upload receipts, we persist data in the receipts and items tables. However, when users delete receipts, all item information (price, transaction date, merchant name, address) is permanently lost. We need to retain this data for:
- Analytics and insights
- Potential future monetization (selling aggregated data to companies)
- Market intelligence

## Storage Architecture Decision: PostgreSQL vs Parquet on S3

### Comparison

| Aspect | PostgreSQL | Parquet on S3 | Hybrid (Recommended) |
|--------|-----------|---------------|---------------------|
| **Cost** | ~$0.115/GB/month (RDS) | ~$0.023/GB/month (S3 Standard)<br>~$0.01/GB/month (S3 Intelligent-Tiering) | Hot: Postgres<br>Cold: S3 |
| **Query Performance** | Fast for row-based queries<br>ACID compliance | Fast for columnar analytics<br>Slower for single-row lookups | Best of both |
| **Scalability** | Vertical (limited)<br>Storage limits | Horizontal (unlimited)<br>Petabyte scale | Unlimited |
| **Analytics** | Good for OLTP<br>Slower for OLAP | Optimized for OLAP<br>Columnar compression | Optimal |
| **Data Sharing** | Requires ETL/API | Direct file export<br>Presigned URLs | Easy export |
| **Query Tools** | Standard SQL | Athena, Presto, Spark<br>Pandas, DuckDB | Both ecosystems |
| **Transactions** | Full ACID support | Append-only<br>No updates | Postgres for active |
| **Maintenance** | Indexes, vacuuming<br>Backup/restore | None<br>S3 versioning | Minimal |
| **At 1M receipts** | ~$50-100/month | ~$5-10/month | ~$20-30/month |

### Recommendation: **Hybrid Data Lake Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
└──────────────┬───────────────────────────┬──────────────────┘
               │                           │
               ▼                           ▼
┌──────────────────────────┐   ┌─────────────────────────────┐
│   PostgreSQL (Hot Data)  │   │    S3 Data Lake (Cold)      │
│                          │   │                             │
│  • Active receipts       │   │  Bronze: Raw JSON backups   │
│  • Last 90 days deleted  │   │  Silver: Cleaned Parquet    │
│  • User profiles         │   │  Gold: Aggregated analytics │
│  • Real-time queries     │   │                             │
│                          │   │  • Historical receipts      │
│  Storage: 10-50 GB       │   │  • Price intelligence       │
│  Cost: ~$20/month        │   │  • Market trends            │
│                          │   │                             │
│                          │   │  Storage: Unlimited         │
│                          │   │  Cost: ~$5-10/month/TB      │
└──────────────┬───────────┘   └─────────────┬───────────────┘
               │                             │
               │     ┌───────────────────────┘
               │     │
               ▼     ▼
┌──────────────────────────────────────────────┐
│         AWS Athena (Query Engine)            │
│  • SQL queries on S3 Parquet files           │
│  • Serverless, pay per query                 │
│  • No infrastructure to manage               │
└──────────────────────────────────────────────┘
```

### Recommended Storage Strategy

**PostgreSQL (Operational Database):**
- Active receipts (not deleted)
- Soft-deleted receipts < 90 days old (for restore capability)
- User profiles and preferences
- Real-time price comparisons
- Shopping lists and favorites

**S3 + Parquet (Data Lake):**

**Bronze Layer (Raw):**
```
s3://receiptly-data-lake/bronze/receipts/
  year=2025/
    month=12/
      day=24/
        receipts_20251224_001.json.gz
        receipts_20251224_002.json.gz
```
- Raw JSON receipts as backup
- Immutable, complete data lineage
- GZIP compressed

**Silver Layer (Cleaned):**
```
s3://receiptly-data-lake/silver/price_intelligence/
  year=2025/
    month=12/
      price_intelligence_202512.parquet
```
- Cleaned, validated data
- Parquet columnar format
- Partitioned by date
- Anonymized user data

**Gold Layer (Aggregated):**
```
s3://receiptly-data-lake/gold/market_trends/
  market_trends_monthly.parquet
  market_trends_weekly.parquet
```
- Pre-aggregated analytics
- Ready for reporting/selling
- Highly compressed

## Data Retention Strategy

### Approach 1: Soft Delete with Data Archiving (Recommended)

**1. Soft Delete Pattern**
Instead of hard-deleting receipts, mark them as deleted but keep the data:

```sql
-- Add to Receipt table
ALTER TABLE receipts ADD COLUMN deleted_at TIMESTAMP NULL;
ALTER TABLE receipts ADD COLUMN deletion_reason VARCHAR(50); -- 'user_request', 'duplicate', etc.

-- Add to Item table  
ALTER TABLE items ADD COLUMN deleted_at TIMESTAMP NULL;
```

**Benefits:**
- Users think receipts are deleted
- You retain all data for analytics
- Can restore if needed
- Simple to implement

**2. Anonymized Data Warehouse (Gold Layer)**

Create separate tables for aggregated, anonymized data:

```sql
-- Price Intelligence Table
CREATE TABLE price_intelligence (
    id UUID PRIMARY KEY,
    item_canonical_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10,2) NOT NULL,
    merchant_name VARCHAR(255) NOT NULL,
    location_postal_code VARCHAR(20),
    location_lat DECIMAL(10,8),
    location_lng DECIMAL(11,8),
    transaction_date DATE NOT NULL,
    
    -- Metadata
    source_receipt_id UUID, -- Reference (optional, can be NULL after true deletion)
    data_quality_score DECIMAL(3,2), -- Based on OCR confidence
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_item_merchant (item_canonical_name, merchant_name),
    INDEX idx_location (location_postal_code, location_lat, location_lng),
    INDEX idx_date (transaction_date)
);

-- Market Trends Table (Aggregated)
CREATE TABLE market_trends (
    id UUID PRIMARY KEY,
    item_canonical_name VARCHAR(255) NOT NULL,
    merchant_name VARCHAR(255),
    postal_code VARCHAR(20),
    
    -- Time period
    year_month VARCHAR(7) NOT NULL, -- '2025-12'
    
    -- Aggregated metrics
    avg_price DECIMAL(10,2),
    min_price DECIMAL(10,2),
    max_price DECIMAL(10,2),
    transaction_count INT,
    unique_locations INT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    
    UNIQUE KEY uk_trend (item_canonical_name, merchant_name, postal_code, year_month)
);

-- User Shopping Patterns (Anonymized)
CREATE TABLE shopping_patterns (
    id UUID PRIMARY KEY,
    user_demographic_bucket VARCHAR(50), -- 'age_25_34_urban', etc. (anonymized)
    merchant_category VARCHAR(100),
    shopping_frequency VARCHAR(20), -- 'weekly', 'monthly'
    avg_basket_size DECIMAL(10,2),
    preferred_shopping_days JSON, -- [1,5,6] (Mon, Fri, Sat)
    year_month VARCHAR(7),
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Approach 2: Event Sourcing + Data Pipeline

**Architecture:**

```
User Action → Event Log → Processing Pipeline → Data Layers
                ↓
         (Immutable)    Raw (Bronze) → Cleaned (Silver) → Aggregated (Gold)
```

**Implementation:**

```sql
-- Event Store (Immutable)
CREATE TABLE receipt_events (
    id UUID PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL, -- 'receipt_created', 'receipt_deleted', 'item_price_updated'
    user_id VARCHAR(255), -- Can be hashed
    receipt_id UUID,
    event_data JSONB NOT NULL, -- Full receipt snapshot
    ocr_confidence DECIMAL(3,2),
    timestamp TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_event_type (event_type),
    INDEX idx_timestamp (timestamp)
);
```

## Implementation Plan

### Phase 1: Soft Delete (Immediate)

**Backend Changes (.NET):**

```csharp
// Domain/Models/Receipt.cs
public class Receipt
{
    // ... existing fields
    public DateTime? DeletedAt { get; set; }
    public string? DeletionReason { get; set; }
    public bool IsDeleted => DeletedAt.HasValue;
}

// Infrastructure/Repositories/ReceiptRepository.cs
public async Task<bool> SoftDeleteAsync(Guid id, string reason, CancellationToken ct)
{
    var receipt = await _context.Receipts
        .Include(r => r.Items)
        .FirstOrDefaultAsync(r => r.Id == id, ct);
    
    if (receipt == null) return false;
    
    receipt.DeletedAt = DateTime.UtcNow;
    receipt.DeletionReason = reason;
    
    // Also soft-delete items
    foreach (var item in receipt.Items)
    {
        item.DeletedAt = DateTime.UtcNow;
    }
    
    await _context.SaveChangesAsync(ct);
    return true;
}

// Update all queries to filter out deleted
public async Task<List<Receipt>> GetByUserIdAsync(string userId, CancellationToken ct)
{
    return await _context.Receipts
        .Include(r => r.Items.Where(i => i.DeletedAt == null))
        .Where(r => r.UserId == userId && r.DeletedAt == null)
        .ToListAsync(ct);
}
```

### Phase 2: Data Archiving Pipeline

**Option A: PostgreSQL Archive Tables (Simpler, for MVP)**

```csharp
// Infrastructure/Services/DataArchivingService.cs
public class DataArchivingService : IDataArchivingService
{
    public async Task ArchiveReceiptData(Receipt receipt, CancellationToken ct)
    {
        // Extract price intelligence to PostgreSQL table
        foreach (var item in receipt.Items)
        {
            var priceRecord = new PriceIntelligence
            {
                Id = Guid.NewGuid(),
                ItemCanonicalName = item.CanonicalName ?? item.Name,
                Category = item.Category,
                Price = item.Price,
                MerchantName = AnonymizeMerchant(receipt.StoreName),
                LocationPostalCode = receipt.PostalCode,
                LocationLat = receipt.Latitude,
                LocationLng = receipt.Longitude,
                TransactionDate = receipt.PurchaseDate.Date,
                SourceReceiptId = receipt.Id,
                DataQualityScore = CalculateQualityScore(receipt, item),
                CreatedAt = DateTime.UtcNow
            };
            
            await _context.PriceIntelligence.AddAsync(priceRecord, ct);
        }
        
        await _context.SaveChangesAsync(ct);
    }
}
```

**Option B: S3 Parquet Archive (Scalable, Cost-Effective)**

```csharp
// Infrastructure/Services/S3DataLakeService.cs
public class S3DataLakeService : IS3DataLakeService
{
    private readonly IAmazonS3 _s3Client;
    private readonly string _bucketName = "receiptly-data-lake";
    
    public async Task ArchiveToDataLake(Receipt receipt, CancellationToken ct)
    {
        // 1. Archive to Bronze (Raw JSON backup)
        await ArchiveToBronze(receipt, ct);
        
        // 2. Transform to Silver (Parquet price intelligence)
        await ArchiveToSilver(receipt, ct);
    }
    
    private async Task ArchiveToBronze(Receipt receipt, CancellationToken ct)
    {
        var date = receipt.PurchaseDate;
        var key = $"bronze/receipts/year={date.Year}/month={date.Month:D2}/day={date.Day:D2}/" +
                  $"receipt_{receipt.Id}.json.gz";
        
        var json = JsonSerializer.Serialize(receipt, new JsonSerializerOptions 
        { 
            WriteIndented = false 
        });
        
        var compressed = CompressGzip(json);
        
        await _s3Client.PutObjectAsync(new PutObjectRequest
        {
            BucketName = _bucketName,
            Key = key,
            InputStream = new MemoryStream(compressed),
            ContentType = "application/gzip",
            Metadata = 
            {
                ["receipt-id"] = receipt.Id.ToString(),
                ["user-id-hash"] = HashUserId(receipt.UserId),
                ["ocr-confidence"] = receipt.OcrConfidence?.ToString() ?? "0"
            }
        }, ct);
    }
    
    private async Task ArchiveToSilver(Receipt receipt, CancellationToken ct)
    {
        // Convert to Parquet-friendly format
        var priceRecords = receipt.Items.Select(item => new
        {
            Id = Guid.NewGuid(),
            ItemCanonicalName = item.CanonicalName ?? item.Name,
            Category = item.Category,
            Price = item.Price,
            Quantity = item.Quantity,
            MerchantName = receipt.StoreName,
            PostalCode = receipt.PostalCode,
            Latitude = receipt.Latitude,
            Longitude = receipt.Longitude,
            TransactionDate = receipt.PurchaseDate.Date,
            Year = receipt.PurchaseDate.Year,
            Month = receipt.PurchaseDate.Month,
            DataQualityScore = CalculateQualityScore(receipt, item),
            CreatedAt = DateTime.UtcNow
        }).ToList();
        
        // Batch writes to Parquet (collect multiple receipts before writing)
        await _parquetBatchService.AddBatch(priceRecords, ct);
    }
}

// Infrastructure/Services/ParquetBatchService.cs
public class ParquetBatchService
{
    private readonly List<PriceIntelligenceRecord> _batch = new();
    private readonly object _lock = new();
    
    public async Task AddBatch(List<dynamic> records, CancellationToken ct)
    {
        lock (_lock)
        {
            _batch.AddRange(records);
            
            // Flush when batch reaches 1000 records
            if (_batch.Count >= 1000)
            {
                await FlushToParquet(ct);
            }
        }
    }
    
    private async Task FlushToParquet(CancellationToken ct)
    {
        if (_batch.Count == 0) return;
        
        var date = DateTime.UtcNow;
        var key = $"silver/price_intelligence/year={date.Year}/month={date.Month:D2}/" +
                  $"batch_{Guid.NewGuid()}.parquet";
        
        using var stream = new MemoryStream();
        
        // Use Parquet.NET library
        var schema = new ParquetSchema(
            new DataField<string>("item_canonical_name"),
            new DataField<string>("category"),
            new DataField<decimal>("price"),
            new DataField<int>("quantity"),
            new DataField<string>("merchant_name"),
            new DataField<string>("postal_code"),
            new DataField<decimal?>("latitude"),
            new DataField<decimal?>("longitude"),
            new DataField<DateTime>("transaction_date"),
            new DataField<int>("year"),
            new DataField<int>("month"),
            new DataField<decimal>("data_quality_score")
        );
        
        using var writer = await ParquetWriter.CreateAsync(schema, stream);
        using var groupWriter = writer.CreateRowGroup();
        
        // Write columns
        await groupWriter.WriteColumnAsync(new DataColumn(
            schema.DataFields[0],
            _batch.Select(r => r.ItemCanonicalName).ToArray()
        ));
        
        // ... write other columns ...
        
        stream.Position = 0;
        
        await _s3Client.PutObjectAsync(new PutObjectRequest
        {
            BucketName = _bucketName,
            Key = key,
            InputStream = stream,
            ContentType = "application/octet-stream"
        }, ct);
        
        _batch.Clear();
    }
}
```

**Recommended: Hybrid Approach**

1. **Immediate (MVP):** Use PostgreSQL archive tables
   - Simpler implementation
   - Familiar SQL queries
   - Good for first 100K-1M receipts

2. **Future (Scale):** Migrate to S3 + Parquet
   - When PostgreSQL archive > 50GB
   - When you need to share/export data
   - When analytics queries become slow

3. **Long-term:** Implement data lifecycle
   - PostgreSQL: Last 90 days of deleted receipts
   - S3 Silver: All historical price intelligence
   - S3 Gold: Pre-aggregated market trends
    
    private decimal CalculateQualityScore(Receipt receipt, Item item)
    {
        var score = 1.0m;
        
        // Penalize low OCR confidence
        if (receipt.OcrConfidence.HasValue)
            score *= (decimal)receipt.OcrConfidence.Value;
        
        // Penalize missing location data
        if (!receipt.Latitude.HasValue)
            score *= 0.8m;
        
        // Penalize missing canonical name
        if (string.IsNullOrEmpty(item.CanonicalName))
            score *= 0.9m;
        
        return Math.Round(score, 2);
    }
}
```

### Phase 3: Background Job for Archiving

```csharp
// Infrastructure/Jobs/DataArchivingJob.cs
public class DataArchivingJob : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            // Find receipts marked for deletion but not yet archived
            var receiptsToArchive = await _context.Receipts
                .Where(r => r.DeletedAt.HasValue && r.IsArchived == false)
                .Take(100)
                .ToListAsync(stoppingToken);
            
            foreach (var receipt in receiptsToArchive)
            {
                await _archivingService.ArchiveReceiptData(receipt, stoppingToken);
                receipt.IsArchived = true;
            }
            
            await _context.SaveChangesAsync(stoppingToken);
            
            await Task.Delay(TimeSpan.FromHours(1), stoppingToken);
        }
    }
}
```

## Privacy & Legal Considerations

### 1. User Consent
Update Terms of Service and Privacy Policy:

```
"When you delete a receipt, we retain anonymized data including:
- Product prices and names
- Store locations (postal code only)
- Purchase dates

This data is used to:
- Improve price comparison features
- Provide market trends to all users
- May be shared with partners in aggregated, anonymized form

Your personal information (name, exact location, payment details) is NEVER retained."
```

### 2. Anonymization Strategy

```csharp
public class DataAnonymizationService
{
    // Hash user ID for pattern analysis
    public string AnonymizeUserId(string userId)
    {
        using var sha = SHA256.Create();
        var hash = sha.ComputeHash(Encoding.UTF8.GetBytes(userId + _secretSalt));
        return Convert.ToBase64String(hash);
    }
    
    // Round coordinates to postal code level
    public (decimal lat, decimal lng) FuzzyLocation(decimal? lat, decimal? lng)
    {
        if (!lat.HasValue || !lng.HasValue) 
            return (0, 0);
        
        // Round to ~1km precision (2 decimal places)
        return (Math.Round(lat.Value, 2), Math.Round(lng.Value, 2));
    }
    
    // Demographic bucketing instead of exact age
    public string GetDemographicBucket(User user)
    {
        var age = CalculateAge(user.BirthDate);
        var ageBucket = age switch
        {
            < 25 => "18_24",
            < 35 => "25_34",
            < 45 => "35_44",
            < 55 => "45_54",
            _ => "55_plus"
        };
        
        var urbanity = user.PostalCode.StartsWith("5") ? "urban" : "suburban";
        return $"age_{ageBucket}_{urbanity}";
    }
}
```

## Migration Script

```sql
-- 1. Add soft delete columns
ALTER TABLE receipts ADD COLUMN deleted_at TIMESTAMP NULL;
ALTER TABLE receipts ADD COLUMN deletion_reason VARCHAR(50);
ALTER TABLE receipts ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;

ALTER TABLE items ADD COLUMN deleted_at TIMESTAMP NULL;

-- 2. Create archive tables
CREATE TABLE price_intelligence (
    id UUID PRIMARY KEY,
    item_canonical_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10,2) NOT NULL,
    merchant_name VARCHAR(255) NOT NULL,
    location_postal_code VARCHAR(20),
    location_lat DECIMAL(10,8),
    location_lng DECIMAL(11,8),
    transaction_date DATE NOT NULL,
    source_receipt_id UUID,
    data_quality_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_item_merchant (item_canonical_name, merchant_name),
    INDEX idx_location (location_postal_code, location_lat, location_lng),
    INDEX idx_date (transaction_date)
);

CREATE TABLE market_trends (
    id UUID PRIMARY KEY,
    item_canonical_name VARCHAR(255) NOT NULL,
    merchant_name VARCHAR(255),
    postal_code VARCHAR(20),
    year_month VARCHAR(7) NOT NULL,
    avg_price DECIMAL(10,2),
    min_price DECIMAL(10,2),
    max_price DECIMAL(10,2),
    transaction_count INT,
    unique_locations INT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    
    UNIQUE KEY uk_trend (item_canonical_name, merchant_name, postal_code, year_month)
);

-- 3. Create indexes
CREATE INDEX idx_receipts_deleted ON receipts(deleted_at, is_archived);
CREATE INDEX idx_price_intel_item ON price_intelligence(item_canonical_name, transaction_date);
```

## Future Monetization Options

### 1. Data Products:
- Price trend API for retailers
- Market basket analysis reports
- Location-based demand forecasting
- Competitive pricing intelligence

### 2. Anonymized Datasets:
- Sell to market research firms
- Academic research partnerships
- Government statistics bureaus

### 3. Analytics Dashboards:
- Real-time price tracking subscriptions for businesses
- Consumer behavior insights

## Implementation Roadmap

### Required NuGet Packages

**For PostgreSQL Archive:**
```xml
<!-- Already have these -->
<PackageReference Include="Npgsql.EntityFrameworkCore.PostgreSQL" />
```

**For S3 + Parquet:**
```xml
<PackageReference Include="AWSSDK.S3" Version="3.7.*" />
<PackageReference Include="Parquet.Net" Version="4.0.*" />
<PackageReference Include="System.IO.Compression" Version="7.0.*" />
```

### Query Examples

**PostgreSQL (Using EF Core):**
```csharp
// Get price trends for an item
var trends = await _context.PriceIntelligence
    .Where(p => p.ItemCanonicalName == "Coca-Cola 1.5L")
    .Where(p => p.TransactionDate >= DateTime.UtcNow.AddMonths(-6))
    .GroupBy(p => new { p.MerchantName, p.TransactionDate.Year, p.TransactionDate.Month })
    .Select(g => new {
        Merchant = g.Key.MerchantName,
        Month = $"{g.Key.Year}-{g.Key.Month:D2}",
        AvgPrice = g.Average(p => p.Price),
        MinPrice = g.Min(p => p.Price),
        MaxPrice = g.Max(p => p.Price)
    })
    .ToListAsync();
```

**S3 + Athena (Using SQL):**
```sql
-- Create external table in Athena
CREATE EXTERNAL TABLE IF NOT EXISTS price_intelligence (
    item_canonical_name STRING,
    category STRING,
    price DECIMAL(10,2),
    quantity INT,
    merchant_name STRING,
    postal_code STRING,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    transaction_date DATE,
    data_quality_score DECIMAL(3,2)
)
PARTITIONED BY (year INT, month INT)
STORED AS PARQUET
LOCATION 's3://receiptly-data-lake/silver/price_intelligence/';

-- Repair partitions (discovers new data)
MSCK REPAIR TABLE price_intelligence;

-- Query price trends
SELECT 
    merchant_name,
    CONCAT(CAST(year AS VARCHAR), '-', LPAD(CAST(month AS VARCHAR), 2, '0')) as month,
    AVG(price) as avg_price,
    MIN(price) as min_price,
    MAX(price) as max_price,
    COUNT(*) as transaction_count
FROM price_intelligence
WHERE item_canonical_name = 'Coca-Cola 1.5L'
    AND year = 2025
    AND month >= 7
GROUP BY merchant_name, year, month
ORDER BY year DESC, month DESC, merchant_name;

-- Cost: ~$5 per TB scanned, typically queries cost < $0.01
```

**Accessing from .NET (Athena SDK):**
```csharp
public class AthenaQueryService
{
    private readonly IAmazonAthena _athenaClient;
    
    public async Task<List<PriceTrend>> GetPriceTrends(string itemName, int months)
    {
        var query = $@"
            SELECT merchant_name, year, month, 
                   AVG(price) as avg_price
            FROM price_intelligence
            WHERE item_canonical_name = '{itemName}'
              AND transaction_date >= DATE_ADD('month', -{months}, CURRENT_DATE)
            GROUP BY merchant_name, year, month
        ";
        
        var request = new StartQueryExecutionRequest
        {
            QueryString = query,
            QueryExecutionContext = new QueryExecutionContext 
            { 
                Database = "receiptly_data_lake" 
            },
            ResultConfiguration = new ResultConfiguration 
            { 
                OutputLocation = "s3://receiptly-athena-results/" 
            }
        };
        
        var response = await _athenaClient.StartQueryExecutionAsync(request);
        
        // Wait for query to complete and fetch results
        return await GetQueryResults(response.QueryExecutionId);
    }
}
```

### Recommended Approach:
1. ✅ **Phase 1 (Week 1-2):** Implement soft delete immediately
   - Add deleted_at columns
   - Update repository methods
   - Update API controllers
   - Frontend: No changes needed (delete still works)

2. ✅ **Phase 2A (Week 3-4):** PostgreSQL archive (MVP)
   - Database migration for price_intelligence table
   - Create DataArchivingService
   - Unit tests for archiving logic
   - **Good for: First 6-12 months, < 1M receipts**

3. ✅ **Phase 2B (Month 6+):** S3 Parquet migration (Scale)
   - Set up S3 data lake buckets
   - Implement S3DataLakeService
   - Backfill historical data from PostgreSQL to Parquet
   - **Trigger: When archive table > 50GB or need to export data**

4. ✅ **Phase 3 (Week 5-6):** Background job to archive
   - Implement DataArchivingJob
   - Configure job scheduling (Hangfire or AWS Lambda)
   - Monitor archiving performance
   - Set up CloudWatch alerts

5. ✅ **Phase 4 (Week 7-8):** Anonymize all personal data
   - Implement DataAnonymizationService
   - Test anonymization thoroughly
   - Security audit

6. ✅ **Phase 5 (Week 9):** Update privacy policy for transparency
   - Legal review
   - Update terms of service
   - User notification

7. ⏭️ **Phase 6 (Month 3-6):** Build aggregation pipeline
   - Market trends calculation (Gold layer)
   - Shopping patterns analysis
   - Real-time analytics dashboards
   - Set up AWS Athena for querying

8. ⏭️ **Phase 7 (Month 6-12):** GDPR compliance & monetization prep
   - Legal consultation
   - Compliance documentation
   - Data export API for GDPR
   - Partner data sharing agreements

### Decision Matrix

**Choose PostgreSQL Archive if:**
- ✅ You're in MVP/early stage (< 1M receipts)
- ✅ Team is more familiar with SQL than data engineering
- ✅ You need simple, fast implementation
- ✅ Budget allows for moderate database costs
- ✅ Don't need to export data externally yet

**Choose S3 + Parquet if:**
- ✅ You expect rapid growth (> 1M receipts/year)
- ✅ You plan to sell/share data with partners
- ✅ You need cost optimization ($5/month vs $50/month)
- ✅ You have data engineering expertise
- ✅ You want industry-standard data lake architecture

**Choose Hybrid (Recommended):**
- ✅ **Best of both worlds**
- ✅ Start with PostgreSQL, migrate to S3 later
- ✅ Keep hot data in Postgres, cold data in S3
- ✅ Gradual learning curve

## Key Considerations

### Data Quality
- Only archive receipts with OCR confidence > 70%
- Validate canonical names before archiving
- Track data lineage for audit trails

### Performance
- Archive in batches (100 receipts at a time)
- Run background job during off-peak hours
- Monitor database growth

### Compliance
- GDPR right to be forgotten (how to handle?)
- Data retention policies (how long to keep?)
- Cross-border data transfer regulations

### Security
- Encrypt sensitive data at rest
- Hash user identifiers
- Access control for archived data
- Regular security audits

## Success Metrics

- **Data Coverage:** % of deleted receipts successfully archived
- **Data Quality:** Average quality score of archived data
- **Storage Efficiency:** Archive table size vs active receipts
- **Query Performance:** Response time for analytics queries
- **Compliance:** Zero GDPR violations

This gives you valuable data while respecting user privacy and staying legally compliant!
