# PostgreSQL Database Setup for Receiptly

## Overview
This document describes the PostgreSQL database schema for storing receipt data processed by OCR services.

## Schema Design

### Tables

#### `receipts`
Stores complete receipt information including:
- **User Information**: `user_id` for user association
- **Store Information**: Extracted by Tesseract OCR
  - `store_name`, `store_address`, `store_phone_number`
  - `postal_code`, `country`
- **Receipt Details**: Extracted by Azure Document Intelligence
  - `purchase_date`, `total_amount`, `subtotal_amount`
  - `tax_amount`, `tip_amount`, `payment_method`
- **OCR Metadata**: Processing information
  - `ocr_provider` - Which service(s) were used
  - `ocr_confidence` - Azure confidence score
  - `location_confidence` - Tesseract location confidence
  - `ocr_strategy` - Preprocessing strategy (enhanced/simple/high_contrast)
  - `raw_ocr_data` - Full JSON response (JSONB for efficient querying)
- **Validation**: Receipt validity
  - `status` - Enum: PendingValidation(0), Valid(1), Invalid(2)
  - `is_valid_receipt`, `validation_confidence`, `validation_message`

#### `items`
Individual line items from receipts:
- `name`, `description`, `price`, `quantity`
- `unit_price`, `total_price`
- `category`, `sku`, `barcode`
- `confidence` - OCR confidence for this specific item
- Foreign key relationship to `receipts` with CASCADE delete

### Indexes
- User lookup: `idx_receipts_user_id`
- Date range queries: `idx_receipts_purchase_date`
- Status filtering: `idx_receipts_status`
- Store search: `idx_receipts_store_name`
- Item lookup: `idx_items_receipt_id`
- JSON search: `idx_receipts_raw_ocr_data` (GIN index)

## Local Development Setup

### 1. Install PostgreSQL

**macOS (using Homebrew)**:
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Or use Docker**:
```bash
docker run --name receiptly-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=receiptly_db \
  -p 5432:5432 \
  -d postgres:15
```

### 2. Create Database
```bash
# Connect to PostgreSQL
psql postgres

# Create database
CREATE DATABASE receiptly_db;

# Connect to the database
\c receiptly_db

# Run the schema script
\i database/schema.sql

# Verify tables
\dt

# Check receipt table structure
\d receipts

# Exit
\q
```

### 3. Update Connection String

In `appsettings.json` or `appsettings.Development.json`:
```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Host=localhost;Port=5432;Database=receiptly_db;Username=postgres;Password=postgres"
  }
}
```

### 4. Test Connection
```bash
cd /Users/kuhan/Projects/receiptly/dotnet-api
dotnet run --project src/Receiptly.API
```

## AWS RDS PostgreSQL Setup

### 1. Create RDS Instance via Terraform

The Terraform configuration in `/terraform` will create:
- PostgreSQL 15.x RDS instance
- Security groups for access
- Parameter groups for optimization
- Backup configuration

```bash
cd /Users/kuhan/Projects/receiptly/terraform/environments/staging
terraform plan
terraform apply
```

### 2. Get RDS Endpoint
```bash
terraform output rds_endpoint
```

### 3. Connect to RDS and Create Schema
```bash
# Get credentials from Terraform output or AWS Secrets Manager
export DB_HOST=$(terraform output -raw rds_endpoint)
export DB_USER="your-admin-user"
export DB_PASSWORD="your-password"

# Connect
psql -h $DB_HOST -U $DB_USER -d receiptly_db

# Run schema
\i database/schema.sql
```

### 4. Update Production Connection String

Store in AWS Secrets Manager or use environment variables:
```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Host=receiptly-db.xxxxx.us-east-1.rds.amazonaws.com;Port=5432;Database=receiptly_db;Username=admin;Password=your-secure-password;SSL Mode=Require"
  }
}
```

## Migrations (Alternative to SQL Script)

If you prefer using EF Core migrations:

```bash
# Install EF Core tools
dotnet tool install --global dotnet-ef --version 8.0.11

# Create migration
dotnet ef migrations add InitialCreate \
  --project src/Receiptly.Infrastructure \
  --startup-project src/Receiptly.API \
  --output-dir Data/Migrations

# Apply migration
dotnet ef database update \
  --project src/Receiptly.Infrastructure \
  --startup-project src/Receiptly.API
```

## Data Model Example

### Storing OCR Results

```csharp
var receipt = new Receipt
{
    Id = Guid.NewGuid(),
    UserId = "user-123",
    
    // Tesseract data
    StoreName = "JAYA GROCER",
    StoreAddress = "16-229, LG FLOOR THE GARDENS MALL 59200 KUALA LUMPUR",
    StorePhoneNumber = "0322831117",
    PostalCode = "59200",
    Country = "Malaysia",
    
    // Azure data
    PurchaseDate = DateTime.Parse("2022-12-15"),
    TotalAmount = 49.99m,
    TaxAmount = 2.50m,
    ReceiptType = "receipt.retailMeal",
    
    // OCR metadata
    OcrProvider = "Hybrid", // Both Tesseract + Azure
    OcrConfidence = 0.98,
    LocationConfidence = 1.0,
    OcrStrategy = "simple",
    RawOcrData = JsonSerializer.Serialize(fullOcrResponse), // JSONB
    
    // Validation
    Status = ReceiptStatus.Valid,
    IsValidReceipt = true,
    ValidationConfidence = 0.98,
    
    CreatedAt = DateTime.UtcNow,
    ProcessedAt = DateTime.UtcNow
};

// Add items
receipt.Items.Add(new Item
{
    Name = "CADBURY ROSES TUB PS 600G",
    Price = 49.99m,
    Quantity = 1,
    TotalPrice = 49.99m,
    Confidence = 0.975
});

await dbContext.Receipts.AddAsync(receipt);
await dbContext.SaveChangesAsync();
```

### Querying Data

```csharp
// Get user's recent receipts
var receipts = await dbContext.Receipts
    .Where(r => r.UserId == userId)
    .OrderByDescending(r => r.PurchaseDate)
    .Include(r => r.Items)
    .Take(20)
    .ToListAsync();

// Search by store
var storeReceipts = await dbContext.Receipts
    .Where(r => r.StoreName.Contains("JAYA"))
    .ToListAsync();

// Get receipts by date range
var monthReceipts = await dbContext.Receipts
    .Where(r => r.PurchaseDate >= startDate && r.PurchaseDate <= endDate)
    .Include(r => r.Items)
    .ToListAsync();

// Query raw OCR data (JSONB)
var azureReceipts = await dbContext.Receipts
    .Where(r => EF.Functions.JsonContains(
        r.RawOcrData, 
        @"{""doc_type"": ""receipt.retailMeal""}"))
    .ToListAsync();
```

## Monitoring and Maintenance

### Check Database Size
```sql
SELECT pg_size_pretty(pg_database_size('receiptly_db'));
```

### Monitor Table Sizes
```sql
SELECT 
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS size
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC;
```

### Index Usage
```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## Backup and Restore

### Backup
```bash
pg_dump -h localhost -U postgres receiptly_db > backup.sql
```

### Restore
```bash
psql -h localhost -U postgres receiptly_db < backup.sql
```

## Security Best Practices

1. **Never commit credentials** - Use environment variables or AWS Secrets Manager
2. **Use SSL/TLS** for RDS connections
3. **Rotate passwords** regularly
4. **Limit database user permissions** - Use principle of least privilege
5. **Enable RDS encryption** at rest and in transit
6. **Regular backups** - Enable automated backups in RDS
7. **Monitor access logs** - Enable PostgreSQL logging in RDS

## Troubleshooting

### Connection Issues
```bash
# Test connection
psql "Host=localhost;Port=5432;Database=receiptly_db;Username=postgres"

# Check if PostgreSQL is running
pg_isready -h localhost -p 5432
```

### Migration Issues
```bash
# Rollback last migration
dotnet ef database update PreviousMigrationName

# Remove last migration
dotnet ef migrations remove
```

## Related Documentation
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Npgsql Entity Framework Core Provider](https://www.npgsql.org/efcore/)
- [AWS RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
