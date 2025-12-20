using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddUserFeedbackTables : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "issue_reports",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    ReceiptId = table.Column<Guid>(type: "uuid", nullable: false),
                    UserId = table.Column<string>(type: "character varying(450)", maxLength: 450, nullable: false),
                    IssueType = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    Description = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: true),
                    Severity = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP")
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

            migrationBuilder.CreateTable(
                name: "user_corrections",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    ReceiptId = table.Column<Guid>(type: "uuid", nullable: false),
                    UserId = table.Column<string>(type: "character varying(450)", maxLength: 450, nullable: false),
                    FieldName = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    IncorrectValue = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    CorrectedValue = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_user_corrections", x => x.Id);
                    table.ForeignKey(
                        name: "FK_user_corrections_receipts_ReceiptId",
                        column: x => x.ReceiptId,
                        principalTable: "receipts",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "user_debug_sessions",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    UserId = table.Column<string>(type: "character varying(450)", maxLength: 450, nullable: false),
                    SessionId = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    StartedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP"),
                    ExpiresAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    Reason = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_user_debug_sessions", x => x.Id);
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

            migrationBuilder.CreateIndex(
                name: "IX_user_corrections_ReceiptId",
                table: "user_corrections",
                column: "ReceiptId");

            migrationBuilder.CreateIndex(
                name: "IX_user_corrections_ReceiptId_FieldName",
                table: "user_corrections",
                columns: new[] { "ReceiptId", "FieldName" });

            migrationBuilder.CreateIndex(
                name: "IX_user_corrections_UserId",
                table: "user_corrections",
                column: "UserId");

            migrationBuilder.CreateIndex(
                name: "IX_user_debug_sessions_SessionId_ExpiresAt",
                table: "user_debug_sessions",
                columns: new[] { "SessionId", "ExpiresAt" });

            migrationBuilder.CreateIndex(
                name: "IX_user_debug_sessions_UserId",
                table: "user_debug_sessions",
                column: "UserId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "issue_reports");

            migrationBuilder.DropTable(
                name: "user_corrections");

            migrationBuilder.DropTable(
                name: "user_debug_sessions");
        }
    }
}
