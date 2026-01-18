using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class RemoveIssueReportsTable : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "issue_reports");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "issue_reports",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    ReceiptId = table.Column<Guid>(type: "uuid", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP"),
                    Description = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: true),
                    IssueType = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    Severity = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    UserId = table.Column<string>(type: "character varying(450)", maxLength: 450, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_issue_reports", x => x.Id);
                    table.ForeignKey(
                        name: "FK_issue_reports_receipts_ReceiptId",
                        column: x => x.ReceiptId,
                        principalTable: "receipts",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_issue_reports_IssueType",
                table: "issue_reports",
                column: "IssueType");

            migrationBuilder.CreateIndex(
                name: "IX_issue_reports_ReceiptId",
                table: "issue_reports",
                column: "ReceiptId");

            migrationBuilder.CreateIndex(
                name: "IX_issue_reports_Severity",
                table: "issue_reports",
                column: "Severity");

            migrationBuilder.CreateIndex(
                name: "IX_issue_reports_UserId",
                table: "issue_reports",
                column: "UserId");
        }
    }
}
