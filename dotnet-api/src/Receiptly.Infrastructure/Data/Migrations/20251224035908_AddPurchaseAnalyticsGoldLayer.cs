using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddPurchaseAnalyticsGoldLayer : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "purchase_analytics_gold",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    ItemId = table.Column<Guid>(type: "uuid", nullable: false),
                    ReceiptId = table.Column<Guid>(type: "uuid", nullable: false),
                    UserId = table.Column<string>(type: "character varying(450)", maxLength: 450, nullable: false),
                    ItemName = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: false),
                    CanonicalName = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: true),
                    UnitPrice = table.Column<decimal>(type: "numeric(18,2)", nullable: false),
                    TotalPrice = table.Column<decimal>(type: "numeric(18,2)", nullable: false),
                    Quantity = table.Column<int>(type: "integer", nullable: false),
                    PurchaseDate = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    StoreName = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    StoreAddress = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: false),
                    StorePhoneNumber = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    Latitude = table.Column<double>(type: "double precision", nullable: true),
                    Longitude = table.Column<double>(type: "double precision", nullable: true),
                    LocationConfidence = table.Column<double>(type: "double precision", nullable: true),
                    ReceiptType = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    TransactionId = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    PaymentMethod = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    ReceiptStatus = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    IsCorrected = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    CorrectedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_purchase_analytics_gold", x => x.Id);
                });

            migrationBuilder.CreateIndex(
                name: "idx_gold_analytics",
                table: "purchase_analytics_gold",
                columns: new[] { "CanonicalName", "PurchaseDate", "Latitude", "Longitude" });

            migrationBuilder.CreateIndex(
                name: "idx_gold_canonical_name",
                table: "purchase_analytics_gold",
                column: "CanonicalName");

            migrationBuilder.CreateIndex(
                name: "idx_gold_item_id",
                table: "purchase_analytics_gold",
                column: "ItemId");

            migrationBuilder.CreateIndex(
                name: "idx_gold_location",
                table: "purchase_analytics_gold",
                columns: new[] { "Latitude", "Longitude" });

            migrationBuilder.CreateIndex(
                name: "idx_gold_purchase_date",
                table: "purchase_analytics_gold",
                column: "PurchaseDate");

            migrationBuilder.CreateIndex(
                name: "idx_gold_store_name",
                table: "purchase_analytics_gold",
                column: "StoreName");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "purchase_analytics_gold");
        }
    }
}
