using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Pgvector;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddCanonicalItems : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterDatabase()
                .Annotation("Npgsql:PostgresExtension:vector", ",,");

            migrationBuilder.AddColumn<Guid>(
                name: "CanonicalItemId",
                table: "purchase_analytics_gold",
                type: "uuid",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "canonical_items",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    Name = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: false),
                    Category = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP"),
                    UpdatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_canonical_items", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "canonical_item_aliases",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    CanonicalItemId = table.Column<Guid>(type: "uuid", nullable: false),
                    Alias = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_canonical_item_aliases", x => x.Id);
                    table.ForeignKey(
                        name: "FK_canonical_item_aliases_canonical_items_CanonicalItemId",
                        column: x => x.CanonicalItemId,
                        principalTable: "canonical_items",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "canonical_item_embeddings",
                columns: table => new
                {
                    CanonicalItemId = table.Column<Guid>(type: "uuid", nullable: false),
                    Embedding = table.Column<Vector>(type: "vector(384)", nullable: true),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_canonical_item_embeddings", x => x.CanonicalItemId);
                    table.ForeignKey(
                        name: "FK_canonical_item_embeddings_canonical_items_CanonicalItemId",
                        column: x => x.CanonicalItemId,
                        principalTable: "canonical_items",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "idx_gold_canonical_item_id",
                table: "purchase_analytics_gold",
                column: "CanonicalItemId");

            migrationBuilder.CreateIndex(
                name: "idx_canonical_aliases_alias",
                table: "canonical_item_aliases",
                column: "Alias");

            migrationBuilder.CreateIndex(
                name: "idx_canonical_aliases_item_id",
                table: "canonical_item_aliases",
                column: "CanonicalItemId");

            migrationBuilder.CreateIndex(
                name: "idx_canonical_items_category",
                table: "canonical_items",
                column: "Category");

            migrationBuilder.CreateIndex(
                name: "idx_canonical_items_name",
                table: "canonical_items",
                column: "Name");

            migrationBuilder.AddForeignKey(
                name: "FK_purchase_analytics_gold_canonical_items_CanonicalItemId",
                table: "purchase_analytics_gold",
                column: "CanonicalItemId",
                principalTable: "canonical_items",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_purchase_analytics_gold_canonical_items_CanonicalItemId",
                table: "purchase_analytics_gold");

            migrationBuilder.DropTable(
                name: "canonical_item_aliases");

            migrationBuilder.DropTable(
                name: "canonical_item_embeddings");

            migrationBuilder.DropTable(
                name: "canonical_items");

            migrationBuilder.DropIndex(
                name: "idx_gold_canonical_item_id",
                table: "purchase_analytics_gold");

            migrationBuilder.DropColumn(
                name: "CanonicalItemId",
                table: "purchase_analytics_gold");

            migrationBuilder.AlterDatabase()
                .OldAnnotation("Npgsql:PostgresExtension:vector", ",,");
        }
    }
}
