using Microsoft.EntityFrameworkCore.Migrations;
using Pgvector;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddPgVectorToMasterProduct : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterDatabase()
                .Annotation("Npgsql:PostgresExtension:vector", ",,");

            migrationBuilder.AddColumn<Vector>(
                name: "Embedding",
                table: "master_products",
                type: "vector(1536)",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "Embedding",
                table: "master_products");

            migrationBuilder.AlterDatabase()
                .OldAnnotation("Npgsql:PostgresExtension:vector", ",,");
        }
    }
}
