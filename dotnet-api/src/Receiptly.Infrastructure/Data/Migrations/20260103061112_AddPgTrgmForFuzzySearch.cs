using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddPgTrgmForFuzzySearch : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Enable pg_trgm extension for fuzzy string matching
            migrationBuilder.Sql("CREATE EXTENSION IF NOT EXISTS pg_trgm;");
            
            // Create GIN index on canonical_items name for fuzzy matching
            migrationBuilder.Sql(
                "CREATE INDEX IF NOT EXISTS idx_canonical_items_name_trgm " +
                "ON canonical_items USING gin(\"Name\" gin_trgm_ops);");
            
            // Create GIN index on canonical_items brand for fuzzy matching
            migrationBuilder.Sql(
                "CREATE INDEX IF NOT EXISTS idx_canonical_items_brand_trgm " +
                "ON canonical_items USING gin(\"Brand\" gin_trgm_ops);");
            
            // Create composite index for location-based filtering
            migrationBuilder.Sql(
                "CREATE INDEX IF NOT EXISTS idx_gold_location_canonical " +
                "ON purchase_analytics_gold(\"CanonicalItemId\", \"Latitude\", \"Longitude\") " +
                "WHERE \"Latitude\" IS NOT NULL AND \"Longitude\" IS NOT NULL;");
            
            // Create index for pricing zone lookups
            migrationBuilder.Sql(
                "CREATE INDEX IF NOT EXISTS idx_gold_pricingzone_canonical " +
                "ON purchase_analytics_gold(\"CanonicalItemId\", \"PricingZoneId\") " +
                "WHERE \"PricingZoneId\" IS NOT NULL;");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            // Drop indexes
            migrationBuilder.Sql("DROP INDEX IF EXISTS idx_canonical_items_name_trgm;");
            migrationBuilder.Sql("DROP INDEX IF EXISTS idx_canonical_items_brand_trgm;");
            migrationBuilder.Sql("DROP INDEX IF EXISTS idx_gold_location_canonical;");
            migrationBuilder.Sql("DROP INDEX IF EXISTS idx_gold_pricingzone_canonical;");
            
            // Note: We don't drop the pg_trgm extension as other parts of the system might use it
        }
    }
    
}
