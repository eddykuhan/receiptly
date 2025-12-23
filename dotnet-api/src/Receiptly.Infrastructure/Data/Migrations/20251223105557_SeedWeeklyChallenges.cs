using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Receiptly.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class SeedWeeklyChallenges : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(@"
                INSERT INTO weekly_challenges (""Id"", ""Title"", ""Description"", ""ChallengeType"", ""TargetCount"", ""PointsReward"", ""WeekStart"", ""WeekEnd"", ""IsActive"", ""CreatedAt"")
                VALUES 
                    (gen_random_uuid(), 'Receipt Collector', 'Upload 3 receipts this week', 'receipt_count', 3, 100, date_trunc('week', CURRENT_TIMESTAMP AT TIME ZONE 'UTC'), date_trunc('week', CURRENT_TIMESTAMP AT TIME ZONE 'UTC') + interval '7 days', true, NOW()),
                    (gen_random_uuid(), 'Store Explorer', 'Shop at 2 different stores', 'store_count', 2, 75, date_trunc('week', CURRENT_TIMESTAMP AT TIME ZONE 'UTC'), date_trunc('week', CURRENT_TIMESTAMP AT TIME ZONE 'UTC') + interval '7 days', true, NOW()),
                    (gen_random_uuid(), 'Big Spender', 'Spend $100 total this week', 'total_amount', 10000, 150, date_trunc('week', CURRENT_TIMESTAMP AT TIME ZONE 'UTC'), date_trunc('week', CURRENT_TIMESTAMP AT TIME ZONE 'UTC') + interval '7 days', true, NOW()),
                    (gen_random_uuid(), 'City Explorer', 'Scan receipts from 2 different cities', 'city_count', 2, 125, date_trunc('week', CURRENT_TIMESTAMP AT TIME ZONE 'UTC'), date_trunc('week', CURRENT_TIMESTAMP AT TIME ZONE 'UTC') + interval '7 days', true, NOW()),
                    (gen_random_uuid(), 'Consistency Streak', 'Upload receipts on 3 different days', 'day_count', 3, 80, date_trunc('week', CURRENT_TIMESTAMP AT TIME ZONE 'UTC'), date_trunc('week', CURRENT_TIMESTAMP AT TIME ZONE 'UTC') + interval '7 days', true, NOW())
                ON CONFLICT DO NOTHING;
            ");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(@"DELETE FROM weekly_challenges WHERE ""Title"" IN ('Receipt Collector', 'Store Explorer', 'Big Spender', 'City Explorer', 'Consistency Streak')");
        }
    }
}
