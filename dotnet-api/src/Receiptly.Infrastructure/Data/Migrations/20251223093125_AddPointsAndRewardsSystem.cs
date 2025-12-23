using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddPointsAndRewardsSystem : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "point_transactions",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    UserId = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    Points = table.Column<int>(type: "integer", nullable: false),
                    TransactionType = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    Description = table.Column<string>(type: "text", nullable: true),
                    ReferenceId = table.Column<Guid>(type: "uuid", nullable: true),
                    EarnedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "NOW()"),
                    ExpiresAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    IsExpired = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_point_transactions", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "user_achievements",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    UserId = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    AchievementType = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    PointsAwarded = table.Column<int>(type: "integer", nullable: false),
                    UnlockedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "NOW()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_user_achievements", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "user_points",
                columns: table => new
                {
                    UserId = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    TotalPoints = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    AvailablePoints = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    LifetimePoints = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "NOW()"),
                    UpdatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "NOW()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_user_points", x => x.UserId);
                });

            migrationBuilder.CreateTable(
                name: "voucher_rewards",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    Title = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    Description = table.Column<string>(type: "text", nullable: true),
                    PointsRequired = table.Column<int>(type: "integer", nullable: false),
                    VoucherType = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    ValueRm = table.Column<decimal>(type: "numeric(10,2)", nullable: false),
                    IconUrl = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    IsActive = table.Column<bool>(type: "boolean", nullable: false, defaultValue: true),
                    DisplayOrder = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_voucher_rewards", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "weekly_challenges",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    ChallengeType = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    Title = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    Description = table.Column<string>(type: "text", nullable: true),
                    PointsReward = table.Column<int>(type: "integer", nullable: false),
                    TargetCount = table.Column<int>(type: "integer", nullable: false),
                    WeekStart = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    WeekEnd = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    IsActive = table.Column<bool>(type: "boolean", nullable: false, defaultValue: true),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "NOW()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_weekly_challenges", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "user_vouchers",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    UserId = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    VoucherRewardId = table.Column<Guid>(type: "uuid", nullable: false),
                    VoucherCode = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    PointsSpent = table.Column<int>(type: "integer", nullable: false),
                    ClaimedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "NOW()"),
                    RevealedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    RevealExpiresAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    IsRevealed = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_user_vouchers", x => x.Id);
                    table.ForeignKey(
                        name: "FK_user_vouchers_voucher_rewards_VoucherRewardId",
                        column: x => x.VoucherRewardId,
                        principalTable: "voucher_rewards",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "user_weekly_progress",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    UserId = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    ChallengeId = table.Column<Guid>(type: "uuid", nullable: false),
                    CurrentCount = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    TargetCount = table.Column<int>(type: "integer", nullable: false),
                    IsCompleted = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    CompletedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    WeekStart = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_user_weekly_progress", x => x.Id);
                    table.ForeignKey(
                        name: "FK_user_weekly_progress_weekly_challenges_ChallengeId",
                        column: x => x.ChallengeId,
                        principalTable: "weekly_challenges",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "idx_point_trans_expires",
                table: "point_transactions",
                column: "ExpiresAt");

            migrationBuilder.CreateIndex(
                name: "idx_point_trans_user",
                table: "point_transactions",
                column: "UserId");

            migrationBuilder.CreateIndex(
                name: "idx_user_achievement_type",
                table: "user_achievements",
                columns: new[] { "UserId", "AchievementType" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "idx_user_achievements",
                table: "user_achievements",
                column: "UserId");

            migrationBuilder.CreateIndex(
                name: "idx_user_vouchers",
                table: "user_vouchers",
                column: "UserId");

            migrationBuilder.CreateIndex(
                name: "IX_user_vouchers_VoucherRewardId",
                table: "user_vouchers",
                column: "VoucherRewardId");

            migrationBuilder.CreateIndex(
                name: "idx_user_challenge",
                table: "user_weekly_progress",
                columns: new[] { "UserId", "ChallengeId" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "idx_user_weekly_progress",
                table: "user_weekly_progress",
                columns: new[] { "UserId", "WeekStart" });

            migrationBuilder.CreateIndex(
                name: "IX_user_weekly_progress_ChallengeId",
                table: "user_weekly_progress",
                column: "ChallengeId");

            migrationBuilder.CreateIndex(
                name: "idx_weekly_challenges_active",
                table: "weekly_challenges",
                columns: new[] { "WeekStart", "IsActive" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "point_transactions");

            migrationBuilder.DropTable(
                name: "user_achievements");

            migrationBuilder.DropTable(
                name: "user_points");

            migrationBuilder.DropTable(
                name: "user_vouchers");

            migrationBuilder.DropTable(
                name: "user_weekly_progress");

            migrationBuilder.DropTable(
                name: "voucher_rewards");

            migrationBuilder.DropTable(
                name: "weekly_challenges");
        }
    }
}
