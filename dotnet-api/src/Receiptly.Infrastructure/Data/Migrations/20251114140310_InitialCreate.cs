using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "receipts",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    UserId = table.Column<string>(type: "character varying(450)", maxLength: 450, nullable: false),
                    StoreName = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    StoreAddress = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: false),
                    StorePhoneNumber = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    PostalCode = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    Country = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    PurchaseDate = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    TotalAmount = table.Column<decimal>(type: "numeric(18,2)", nullable: false),
                    SubtotalAmount = table.Column<decimal>(type: "numeric(18,2)", nullable: true),
                    TaxAmount = table.Column<decimal>(type: "numeric(18,2)", nullable: true),
                    TipAmount = table.Column<decimal>(type: "numeric(18,2)", nullable: true),
                    ReceiptType = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    TransactionId = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    PaymentMethod = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    ImageUrl = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    S3Key = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    OriginalFileName = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: true),
                    Latitude = table.Column<double>(type: "double precision", nullable: true),
                    Longitude = table.Column<double>(type: "double precision", nullable: true),
                    OcrProvider = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    OcrConfidence = table.Column<double>(type: "double precision", nullable: true),
                    LocationConfidence = table.Column<double>(type: "double precision", nullable: true),
                    OcrStrategy = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    RawOcrData = table.Column<string>(type: "jsonb", nullable: true),
                    Status = table.Column<int>(type: "integer", nullable: false),
                    ValidationConfidence = table.Column<double>(type: "double precision", nullable: true),
                    ValidationMessage = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    IsValidReceipt = table.Column<bool>(type: "boolean", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP"),
                    UpdatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    ProcessedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_receipts", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "items",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    Name = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: false),
                    Description = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    Price = table.Column<decimal>(type: "numeric(18,2)", nullable: false),
                    UnitPrice = table.Column<decimal>(type: "numeric(18,2)", nullable: true),
                    Quantity = table.Column<int>(type: "integer", nullable: false),
                    TotalPrice = table.Column<decimal>(type: "numeric(18,2)", nullable: true),
                    Category = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    Sku = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    Barcode = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    Confidence = table.Column<double>(type: "double precision", nullable: true),
                    ReceiptId = table.Column<Guid>(type: "uuid", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP"),
                    UpdatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_items", x => x.Id);
                    table.ForeignKey(
                        name: "FK_items_receipts_ReceiptId",
                        column: x => x.ReceiptId,
                        principalTable: "receipts",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_items_Name",
                table: "items",
                column: "Name");

            migrationBuilder.CreateIndex(
                name: "IX_items_ReceiptId",
                table: "items",
                column: "ReceiptId");

            migrationBuilder.CreateIndex(
                name: "IX_receipts_CreatedAt",
                table: "receipts",
                column: "CreatedAt");

            migrationBuilder.CreateIndex(
                name: "IX_receipts_PurchaseDate",
                table: "receipts",
                column: "PurchaseDate");

            migrationBuilder.CreateIndex(
                name: "IX_receipts_Status",
                table: "receipts",
                column: "Status");

            migrationBuilder.CreateIndex(
                name: "IX_receipts_StoreName",
                table: "receipts",
                column: "StoreName");

            migrationBuilder.CreateIndex(
                name: "IX_receipts_UserId",
                table: "receipts",
                column: "UserId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "items");

            migrationBuilder.DropTable(
                name: "receipts");
        }
    }
}
