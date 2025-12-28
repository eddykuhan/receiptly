using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddUniqueIndexToMasterProduct : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "idx_master_products_name",
                table: "master_products");

            migrationBuilder.CreateIndex(
                name: "idx_master_products_name",
                table: "master_products",
                column: "Name",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "idx_master_products_name",
                table: "master_products");

            migrationBuilder.CreateIndex(
                name: "idx_master_products_name",
                table: "master_products",
                column: "Name");
        }
    }
}
