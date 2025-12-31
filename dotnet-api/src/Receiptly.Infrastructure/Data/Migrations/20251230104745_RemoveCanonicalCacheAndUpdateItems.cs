using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class RemoveCanonicalCacheAndUpdateItems : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "canonical_cache");

            migrationBuilder.AddColumn<Guid>(
                name: "CanonicalItemId",
                table: "items",
                type: "uuid",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "CanonicalItemId",
                table: "items");

            migrationBuilder.CreateTable(
                name: "canonical_cache",
                columns: table => new
                {
                    RawName = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: false),
                    CanonicalName = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_canonical_cache", x => x.RawName);
                });
        }
    }
}
