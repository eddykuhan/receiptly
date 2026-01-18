using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddAmazonStyleCanonicalization : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "Brand",
                table: "canonical_items",
                type: "character varying(100)",
                maxLength: 100,
                nullable: true);

            migrationBuilder.AddColumn<decimal>(
                name: "Confidence",
                table: "canonical_items",
                type: "numeric(3,2)",
                nullable: false,
                defaultValue: 1.0m);

            migrationBuilder.AddColumn<bool>(
                name: "IsMaster",
                table: "canonical_items",
                type: "boolean",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<Guid>(
                name: "MasterItemId",
                table: "canonical_items",
                type: "uuid",
                nullable: true);

            migrationBuilder.AddColumn<string[]>(
                name: "NameTokens",
                table: "canonical_items",
                type: "text[]",
                nullable: true);

            migrationBuilder.AddColumn<int>(
                name: "PackCount",
                table: "canonical_items",
                type: "integer",
                nullable: false,
                defaultValue: 1);

            migrationBuilder.AddColumn<string>(
                name: "Size",
                table: "canonical_items",
                type: "character varying(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.AddColumn<decimal>(
                name: "SizeNormalized",
                table: "canonical_items",
                type: "numeric(10,2)",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "SizeUnit",
                table: "canonical_items",
                type: "character varying(10)",
                maxLength: 10,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "SourceType",
                table: "canonical_items",
                type: "character varying(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Variant",
                table: "canonical_items",
                type: "character varying(200)",
                maxLength: 200,
                nullable: true);

            migrationBuilder.AddColumn<DateTime>(
                name: "LastSeenAt",
                table: "canonical_item_aliases",
                type: "timestamp with time zone",
                nullable: true);

            migrationBuilder.AddColumn<decimal>(
                name: "MatchConfidence",
                table: "canonical_item_aliases",
                type: "numeric(3,2)",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "MatchMethod",
                table: "canonical_item_aliases",
                type: "character varying(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Source",
                table: "canonical_item_aliases",
                type: "character varying(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.AddColumn<int>(
                name: "UsageCount",
                table: "canonical_item_aliases",
                type: "integer",
                nullable: false,
                defaultValue: 1);

            migrationBuilder.CreateIndex(
                name: "idx_canonical_items_brand",
                table: "canonical_items",
                column: "Brand",
                filter: "\"IsMaster\" = TRUE AND \"Brand\" IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "idx_canonical_items_dairy_lookup",
                table: "canonical_items",
                columns: new[] { "Brand", "SizeNormalized", "Category" },
                filter: "\"IsMaster\" = TRUE AND \"Category\" = 'Dairy'");

            migrationBuilder.CreateIndex(
                name: "idx_canonical_items_master",
                table: "canonical_items",
                column: "IsMaster",
                filter: "\"IsMaster\" = TRUE");

            migrationBuilder.CreateIndex(
                name: "idx_canonical_items_size",
                table: "canonical_items",
                columns: new[] { "SizeNormalized", "SizeUnit" },
                filter: "\"IsMaster\" = TRUE AND \"SizeNormalized\" IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "idx_canonical_items_tokens",
                table: "canonical_items",
                column: "NameTokens",
                filter: "\"IsMaster\" = TRUE")
                .Annotation("Npgsql:IndexMethod", "gin");

            migrationBuilder.CreateIndex(
                name: "IX_canonical_items_MasterItemId",
                table: "canonical_items",
                column: "MasterItemId");

            migrationBuilder.CreateIndex(
                name: "idx_canonical_aliases_usage",
                table: "canonical_item_aliases",
                column: "UsageCount",
                descending: new bool[0]);

            migrationBuilder.AddForeignKey(
                name: "FK_canonical_items_canonical_items_MasterItemId",
                table: "canonical_items",
                column: "MasterItemId",
                principalTable: "canonical_items",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_canonical_items_canonical_items_MasterItemId",
                table: "canonical_items");

            migrationBuilder.DropIndex(
                name: "idx_canonical_items_brand",
                table: "canonical_items");

            migrationBuilder.DropIndex(
                name: "idx_canonical_items_dairy_lookup",
                table: "canonical_items");

            migrationBuilder.DropIndex(
                name: "idx_canonical_items_master",
                table: "canonical_items");

            migrationBuilder.DropIndex(
                name: "idx_canonical_items_size",
                table: "canonical_items");

            migrationBuilder.DropIndex(
                name: "idx_canonical_items_tokens",
                table: "canonical_items");

            migrationBuilder.DropIndex(
                name: "IX_canonical_items_MasterItemId",
                table: "canonical_items");

            migrationBuilder.DropIndex(
                name: "idx_canonical_aliases_usage",
                table: "canonical_item_aliases");

            migrationBuilder.DropColumn(
                name: "Brand",
                table: "canonical_items");

            migrationBuilder.DropColumn(
                name: "Confidence",
                table: "canonical_items");

            migrationBuilder.DropColumn(
                name: "IsMaster",
                table: "canonical_items");

            migrationBuilder.DropColumn(
                name: "MasterItemId",
                table: "canonical_items");

            migrationBuilder.DropColumn(
                name: "NameTokens",
                table: "canonical_items");

            migrationBuilder.DropColumn(
                name: "PackCount",
                table: "canonical_items");

            migrationBuilder.DropColumn(
                name: "Size",
                table: "canonical_items");

            migrationBuilder.DropColumn(
                name: "SizeNormalized",
                table: "canonical_items");

            migrationBuilder.DropColumn(
                name: "SizeUnit",
                table: "canonical_items");

            migrationBuilder.DropColumn(
                name: "SourceType",
                table: "canonical_items");

            migrationBuilder.DropColumn(
                name: "Variant",
                table: "canonical_items");

            migrationBuilder.DropColumn(
                name: "LastSeenAt",
                table: "canonical_item_aliases");

            migrationBuilder.DropColumn(
                name: "MatchConfidence",
                table: "canonical_item_aliases");

            migrationBuilder.DropColumn(
                name: "MatchMethod",
                table: "canonical_item_aliases");

            migrationBuilder.DropColumn(
                name: "Source",
                table: "canonical_item_aliases");

            migrationBuilder.DropColumn(
                name: "UsageCount",
                table: "canonical_item_aliases");
        }
    }
}
