using Microsoft.EntityFrameworkCore;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Data.Configurations;

namespace Receiptly.Infrastructure.Data;

public class ApplicationDbContext : DbContext
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
        : base(options)
    {
    }

    public DbSet<Receipt> Receipts { get; set; }
    public DbSet<Item> Items { get; set; }
    public DbSet<UserCorrection> UserCorrections { get; set; }
    public DbSet<IssueReport> IssueReports { get; set; }
    public DbSet<UserDebugSession> UserDebugSessions { get; set; }
    
    // Points and Rewards System
    public DbSet<UserPoints> UserPoints { get; set; }
    public DbSet<PointTransaction> PointTransactions { get; set; }
    public DbSet<UserAchievement> UserAchievements { get; set; }
    public DbSet<WeeklyChallenge> WeeklyChallenges { get; set; }
    public DbSet<UserWeeklyProgress> UserWeeklyProgress { get; set; }
    public DbSet<VoucherReward> VoucherRewards { get; set; }
    public DbSet<UserVoucher> UserVouchers { get; set; }
    
    // Analytics Gold Layer
    public DbSet<PurchaseAnalyticsGold> PurchaseAnalyticsGold { get; set; }
    public DbSet<MasterProduct> MasterProducts { get; set; }
    
    // Canonical Items System
    public DbSet<CanonicalItem> CanonicalItems { get; set; }
    public DbSet<CanonicalItemAlias> CanonicalItemAliases { get; set; }
    public DbSet<CanonicalItemEmbedding> CanonicalItemEmbeddings { get; set; }
    public DbSet<Store> Stores { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Enable pgvector extension
        modelBuilder.HasPostgresExtension("vector");

        // Configure Points and Rewards System models
        modelBuilder.ConfigurePointsSystemModels();

        // Configure Receipt entity
        modelBuilder.Entity<Receipt>(entity =>
        {
            entity.ToTable("receipts");
            
            entity.HasKey(e => e.Id);
            
            // Required fields
            entity.Property(e => e.UserId)
                .IsRequired()
                .HasMaxLength(450);
            
            entity.Property(e => e.StoreName)
                .IsRequired()
                .HasMaxLength(200);
            
            entity.Property(e => e.StoreAddress)
                .IsRequired()
                .HasMaxLength(500);
            
            entity.Property(e => e.PurchaseDate)
                .IsRequired();
            
            // Decimal fields with precision
            entity.Property(e => e.TotalAmount)
                .HasColumnType("decimal(18,2)")
                .IsRequired();
            
            entity.Property(e => e.SubtotalAmount)
                .HasColumnType("decimal(18,2)");
            
            entity.Property(e => e.TaxAmount)
                .HasColumnType("decimal(18,2)");
            
            entity.Property(e => e.TipAmount)
                .HasColumnType("decimal(18,2)");
            
            // Optional string fields
            entity.Property(e => e.StorePhoneNumber)
                .HasMaxLength(50);
            
            entity.Property(e => e.PostalCode)
                .HasMaxLength(20);
            
            entity.Property(e => e.Country)
                .HasMaxLength(100);
            
            entity.Property(e => e.ReceiptType)
                .HasMaxLength(100);
            
            entity.Property(e => e.TransactionId)
                .HasMaxLength(100);
            
            entity.Property(e => e.PaymentMethod)
                .HasMaxLength(50);
            
            entity.Property(e => e.ImageUrl)
                .HasMaxLength(1000);
            
            entity.Property(e => e.S3Key)
                .HasMaxLength(500);
            
            entity.Property(e => e.OriginalFileName)
                .HasMaxLength(255);
            
            entity.Property(e => e.ImageHash)
                .HasMaxLength(64); // SHA256 produces 64-character hex string
            
            entity.Property(e => e.OcrProvider)
                .HasMaxLength(50);
            
            entity.Property(e => e.OcrStrategy)
                .HasMaxLength(50);
            
            entity.Property(e => e.ValidationMessage)
                .HasMaxLength(500);
            
            // Audit fields
            entity.Property(e => e.CreatedAt)
                .IsRequired()
                .HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.Property(e => e.UpdatedAt);
            
            entity.Property(e => e.ProcessedAt);
            
            // Indexes for performance
            entity.HasIndex(e => e.UserId);
            entity.HasIndex(e => e.PurchaseDate);
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.CreatedAt);
            entity.HasIndex(e => e.StoreName);
            entity.HasIndex(e => new { e.UserId, e.ImageHash }); // Composite index for duplicate detection
        });

        // Configure Item entity
        modelBuilder.Entity<Item>(entity =>
        {
            entity.ToTable("items");
            
            entity.HasKey(e => e.Id);
            
            // Required fields
            entity.Property(e => e.Name)
                .IsRequired()
                .HasMaxLength(300);
            
            entity.Property(e => e.Description)
                .HasMaxLength(1000);
            
            // Decimal fields
            entity.Property(e => e.Price)
                .HasColumnType("decimal(18,2)")
                .IsRequired();
            
            entity.Property(e => e.UnitPrice)
                .HasColumnType("decimal(18,2)");
            
            entity.Property(e => e.TotalPrice)
                .HasColumnType("decimal(18,2)");
            
            entity.Property(e => e.Quantity)
                .IsRequired();
            
            entity.Property(e => e.Category)
                .HasMaxLength(100);
            
            entity.Property(e => e.Sku)
                .HasMaxLength(100);
            
            entity.Property(e => e.Barcode)
                .HasMaxLength(100);
            
            // Audit fields
            entity.Property(e => e.CreatedAt)
                .IsRequired()
                .HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.Property(e => e.UpdatedAt);
            
            // Relationship
            entity.HasOne(e => e.Receipt)
                  .WithMany(e => e.Items)
                  .HasForeignKey(e => e.ReceiptId)
                  .OnDelete(DeleteBehavior.Cascade);
            
            // Indexes
            entity.HasIndex(e => e.ReceiptId);
            entity.HasIndex(e => e.Name);
        });

        // Configure UserCorrection entity
        modelBuilder.Entity<UserCorrection>(entity =>
        {
            entity.ToTable("user_corrections");
            
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.UserId)
                .IsRequired()
                .HasMaxLength(450);
            
            entity.Property(e => e.ReceiptId)
                .IsRequired();
            
            entity.Property(e => e.FieldName)
                .IsRequired()
                .HasMaxLength(100);
            
            entity.Property(e => e.IncorrectValue)
                .HasMaxLength(1000);
            
            entity.Property(e => e.CorrectedValue)
                .HasMaxLength(1000);
            
            entity.Property(e => e.Latitude)
                .HasPrecision(10, 7);
            
            entity.Property(e => e.Longitude)
                .HasPrecision(10, 7);
            
            entity.Property(e => e.CreatedAt)
                .IsRequired()
                .HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.HasOne(e => e.Receipt)
                .WithMany()
                .HasForeignKey(e => e.ReceiptId)
                .OnDelete(DeleteBehavior.Cascade);
            
            entity.HasIndex(e => e.UserId);
            entity.HasIndex(e => e.ReceiptId);
            entity.HasIndex(e => new { e.ReceiptId, e.FieldName });
        });

        // Configure IssueReport entity
        modelBuilder.Entity<IssueReport>(entity =>
        {
            entity.ToTable("issue_reports");
            
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.UserId)
                .IsRequired()
                .HasMaxLength(450);
            
            entity.Property(e => e.ReceiptId)
                .IsRequired();
            
            entity.Property(e => e.IssueType)
                .IsRequired()
                .HasMaxLength(50);
            
            entity.Property(e => e.Severity)
                .IsRequired()
                .HasMaxLength(20);
            
            entity.Property(e => e.Description)
                .HasMaxLength(2000);
            
            entity.Property(e => e.CreatedAt)
                .IsRequired()
                .HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.HasOne(e => e.Receipt)
                .WithMany()
                .HasForeignKey(e => e.ReceiptId)
                .OnDelete(DeleteBehavior.Cascade);
            
            entity.HasIndex(e => e.UserId);
            entity.HasIndex(e => e.ReceiptId);
            entity.HasIndex(e => e.IssueType);
            entity.HasIndex(e => e.Severity);
        });

        // Configure UserDebugSession entity
        modelBuilder.Entity<UserDebugSession>(entity =>
        {
            entity.ToTable("user_debug_sessions");
            
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.UserId)
                .IsRequired()
                .HasMaxLength(450);
            
            entity.Property(e => e.SessionId)
                .IsRequired()
                .HasMaxLength(100);
            
            entity.Property(e => e.Reason)
                .HasMaxLength(500);
            
            entity.Property(e => e.StartedAt)
                .IsRequired()
                .HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.Property(e => e.ExpiresAt)
                .IsRequired();
            
            entity.HasIndex(e => e.UserId);
            entity.HasIndex(e => new { e.SessionId, e.ExpiresAt });
        });

        // Configure PurchaseAnalyticsGold entity (gold layer for price history)
        modelBuilder.Entity<PurchaseAnalyticsGold>(entity =>
        {
            entity.ToTable("purchase_analytics_gold");
            
            entity.HasKey(e => e.Id);
            
            // Required fields
            entity.Property(e => e.ItemId)
                .IsRequired();
            
            entity.Property(e => e.ReceiptId); // Nullable for scraped data
            
            entity.Property(e => e.UserId)
                .HasMaxLength(450); // Nullable for scraped data
            
            entity.Property(e => e.ItemName)
                .IsRequired()
                .HasMaxLength(300);
            
            entity.Property(e => e.Source)
                .HasMaxLength(50)
                .HasDefaultValue("UserReceipt");
            
            entity.Property(e => e.CanonicalName)
                .HasMaxLength(300);
            
            entity.Property(e => e.CanonicalItemId); // Nullable - will be populated by ETL or LLM service
            
            // Decimal fields
            entity.Property(e => e.UnitPrice)
                .HasColumnType("decimal(18,2)")
                .IsRequired();
            
            entity.Property(e => e.TotalPrice)
                .HasColumnType("decimal(18,2)")
                .IsRequired();
            
            entity.Property(e => e.Quantity)
                .IsRequired();
            
            entity.Property(e => e.PurchaseDate)
                .IsRequired();
            
            entity.Property(e => e.StoreName)
                .IsRequired()
                .HasMaxLength(200);
            
            entity.Property(e => e.StoreAddress)
                .IsRequired()
                .HasMaxLength(500);
            
            entity.Property(e => e.StorePhoneNumber)
                .HasMaxLength(50);
            
            entity.Property(e => e.ReceiptType)
                .HasMaxLength(50);
            
            entity.Property(e => e.TransactionId)
                .HasMaxLength(100);
            
            entity.Property(e => e.PaymentMethod)
                .HasMaxLength(50);
            
            entity.Property(e => e.ReceiptStatus)
                .HasMaxLength(50);
            
            entity.Property(e => e.IsCorrected)
                .IsRequired()
                .HasDefaultValue(false);
            
            entity.Property(e => e.CreatedAt)
                .IsRequired()
                .HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            // Indexes for analytics queries
            entity.HasIndex(e => e.ItemId)
                .HasDatabaseName("idx_gold_item_id");
            
            entity.HasIndex(e => e.PurchaseDate)
                .HasDatabaseName("idx_gold_purchase_date");
            
            entity.HasIndex(e => e.StoreName)
                .HasDatabaseName("idx_gold_store_name");
            
            entity.HasIndex(e => e.CanonicalName)
                .HasDatabaseName("idx_gold_canonical_name");
            
            entity.HasIndex(e => e.CanonicalItemId)
                .HasDatabaseName("idx_gold_canonical_item_id");
            
            // Composite index for location-based queries (critical for price map)
            entity.HasIndex(e => new { e.Latitude, e.Longitude })
                .HasDatabaseName("idx_gold_location");
            
            // Composite index for time-series and product analysis
            entity.HasIndex(e => new { e.CanonicalName, e.PurchaseDate, e.Latitude, e.Longitude })
                .HasDatabaseName("idx_gold_analytics");
            
            // Foreign key to canonical_items (nullable - not all records will have this initially)
            entity.HasOne<CanonicalItem>()
                .WithMany()
                .HasForeignKey(e => e.CanonicalItemId)
                .OnDelete(DeleteBehavior.SetNull);
        });

        // Configure MasterProduct entity
        modelBuilder.Entity<MasterProduct>(entity =>
        {
            entity.ToTable("master_products");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Name).IsRequired();
            entity.HasIndex(e => e.Name).IsUnique().HasDatabaseName("idx_master_products_name");
        });

        // Configure CanonicalItem entity
        modelBuilder.Entity<CanonicalItem>(entity =>
        {
            entity.ToTable("canonical_items");
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.Name)
                .IsRequired()
                .HasMaxLength(300);
            
            entity.Property(e => e.Category)
                .IsRequired()
                .HasMaxLength(100);
            
            entity.Property(e => e.CreatedAt)
                .IsRequired()
                .HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.Property(e => e.UpdatedAt)
                .IsRequired()
                .HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.HasIndex(e => e.Name)
                .HasDatabaseName("idx_canonical_items_name");
            
            entity.HasIndex(e => e.Category)
                .HasDatabaseName("idx_canonical_items_category");
        });

        // Configure CanonicalItemAlias entity
        modelBuilder.Entity<CanonicalItemAlias>(entity =>
        {
            entity.ToTable("canonical_item_aliases");
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.Alias)
                .IsRequired()
                .HasMaxLength(300);
            
            entity.Property(e => e.CreatedAt)
                .IsRequired()
                .HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.HasOne(e => e.CanonicalItem)
                .WithMany()
                .HasForeignKey(e => e.CanonicalItemId)
                .OnDelete(DeleteBehavior.Cascade);
            
            entity.HasIndex(e => e.Alias)
                .HasDatabaseName("idx_canonical_aliases_alias");
            
            entity.HasIndex(e => e.CanonicalItemId)
                .HasDatabaseName("idx_canonical_aliases_item_id");
        });

        // Configure CanonicalItemEmbedding entity
        modelBuilder.Entity<CanonicalItemEmbedding>(entity =>
        {
            entity.ToTable("canonical_item_embeddings");
            entity.HasKey(e => e.CanonicalItemId);
            
            entity.Property(e => e.Embedding)
                .HasColumnType("vector(384)"); // all-MiniLM-L6-v2 produces 384-dim vectors
            
            entity.Property(e => e.CreatedAt)
                .IsRequired()
                .HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.HasOne(e => e.CanonicalItem)
                .WithOne()
                .HasForeignKey<CanonicalItemEmbedding>(e => e.CanonicalItemId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        // Configure Store entity
        modelBuilder.Entity<Store>(entity =>
        {
            entity.ToTable("stores");
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.Name)
                .IsRequired()
                .HasMaxLength(200);
            
            entity.Property(e => e.RetailChain)
                .HasMaxLength(100);
            
            entity.Property(e => e.PricingZoneId)
                .IsRequired()
                .HasMaxLength(100); // e.g., "MYDIN_NATIONAL"
            
            entity.Property(e => e.Address)
                .HasMaxLength(500);
            
            entity.Property(e => e.Latitude)
                .HasPrecision(10, 7)
                .IsRequired();
            
            entity.Property(e => e.Longitude)
                .HasPrecision(10, 7)
                .IsRequired();
            
            entity.Property(e => e.CreatedAt)
                .HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.Property(e => e.UpdatedAt)
                .HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            // Indexes for location-based search
            entity.HasIndex(e => new { e.Latitude, e.Longitude })
                .HasDatabaseName("idx_stores_location");
            
            // Index for zone lookup
            entity.HasIndex(e => e.PricingZoneId)
                .HasDatabaseName("idx_stores_pricing_zone");
        });
    }
}