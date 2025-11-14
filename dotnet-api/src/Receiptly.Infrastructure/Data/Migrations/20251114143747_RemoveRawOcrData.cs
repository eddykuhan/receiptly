using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class RemoveRawOcrData : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "RawOcrData",
                table: "receipts");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "RawOcrData",
                table: "receipts",
                type: "jsonb",
                nullable: true);
        }
    }
}
