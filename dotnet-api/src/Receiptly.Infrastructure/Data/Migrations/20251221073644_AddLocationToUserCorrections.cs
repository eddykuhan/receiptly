using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddLocationToUserCorrections : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<double>(
                name: "Latitude",
                table: "user_corrections",
                type: "double precision",
                precision: 10,
                scale: 7,
                nullable: true);

            migrationBuilder.AddColumn<double>(
                name: "Longitude",
                table: "user_corrections",
                type: "double precision",
                precision: 10,
                scale: 7,
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "Latitude",
                table: "user_corrections");

            migrationBuilder.DropColumn(
                name: "Longitude",
                table: "user_corrections");
        }
    }
}
