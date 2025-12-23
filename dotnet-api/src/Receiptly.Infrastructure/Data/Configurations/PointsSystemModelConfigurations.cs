using Microsoft.EntityFrameworkCore;
using Receiptly.Domain.Models;

namespace Receiptly.Infrastructure.Data.Configurations;

public static class PointsSystemModelConfigurations
{
    public static void ConfigurePointsSystemModels(this ModelBuilder modelBuilder)
    {
        // Configure UserPoints entity
        modelBuilder.Entity<UserPoints>(entity =>
        {
            entity.ToTable("user_points");
            entity.HasKey(e => e.UserId);
            
            entity.Property(e => e.UserId).HasMaxLength(255);
            entity.Property(e => e.TotalPoints).HasDefaultValue(0);
            entity.Property(e => e.AvailablePoints).HasDefaultValue(0);
            entity.Property(e => e.LifetimePoints).HasDefaultValue(0);
            entity.Property(e => e.CreatedAt).HasDefaultValueSql("NOW()");
            entity.Property(e => e.UpdatedAt).HasDefaultValueSql("NOW()");
        });

        // Configure PointTransaction entity
        modelBuilder.Entity<PointTransaction>(entity =>
        {
            entity.ToTable("point_transactions");
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.Id).HasDefaultValueSql("gen_random_uuid()");
            entity.Property(e => e.UserId).IsRequired().HasMaxLength(255);
            entity.Property(e => e.TransactionType).IsRequired().HasMaxLength(50);
            entity.Property(e => e.EarnedAt).HasDefaultValueSql("NOW()");
            entity.Property(e => e.IsExpired).HasDefaultValue(false);
            
            entity.HasIndex(e => e.UserId).HasDatabaseName("idx_point_trans_user");
            entity.HasIndex(e => e.ExpiresAt).HasDatabaseName("idx_point_trans_expires");
        });

        // Configure UserAchievement entity
        modelBuilder.Entity<UserAchievement>(entity =>
        {
            entity.ToTable("user_achievements");
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.Id).HasDefaultValueSql("gen_random_uuid()");
            entity.Property(e => e.UserId).IsRequired().HasMaxLength(255);
            entity.Property(e => e.AchievementType).IsRequired().HasMaxLength(100);
            entity.Property(e => e.UnlockedAt).HasDefaultValueSql("NOW()");
            
            entity.HasIndex(e => e.UserId).HasDatabaseName("idx_user_achievements");
            entity.HasIndex(e => new { e.UserId, e.AchievementType })
                .IsUnique()
                .HasDatabaseName("idx_user_achievement_type");
        });

        // Configure WeeklyChallenge entity
        modelBuilder.Entity<WeeklyChallenge>(entity =>
        {
            entity.ToTable("weekly_challenges");
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.Id).HasDefaultValueSql("gen_random_uuid()");
            entity.Property(e => e.ChallengeType).IsRequired().HasMaxLength(100);
            entity.Property(e => e.Title).IsRequired().HasMaxLength(255);
            entity.Property(e => e.IsActive).HasDefaultValue(true);
            entity.Property(e => e.CreatedAt).HasDefaultValueSql("NOW()");
            
            entity.HasIndex(e => new { e.WeekStart, e.IsActive })
                .HasDatabaseName("idx_weekly_challenges_active");
        });

        // Configure UserWeeklyProgress entity
        modelBuilder.Entity<UserWeeklyProgress>(entity =>
        {
            entity.ToTable("user_weekly_progress");
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.Id).HasDefaultValueSql("gen_random_uuid()");
            entity.Property(e => e.UserId).IsRequired().HasMaxLength(255);
            entity.Property(e => e.CurrentCount).HasDefaultValue(0);
            entity.Property(e => e.IsCompleted).HasDefaultValue(false);
            
            entity.HasOne(e => e.Challenge)
                .WithMany()
                .HasForeignKey(e => e.ChallengeId)
                .OnDelete(DeleteBehavior.Cascade);
            
            entity.HasIndex(e => new { e.UserId, e.WeekStart })
                .HasDatabaseName("idx_user_weekly_progress");
            entity.HasIndex(e => new { e.UserId, e.ChallengeId })
                .IsUnique()
                .HasDatabaseName("idx_user_challenge");
        });

        // Configure VoucherReward entity
        modelBuilder.Entity<VoucherReward>(entity =>
        {
            entity.ToTable("voucher_rewards");
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.Id).HasDefaultValueSql("gen_random_uuid()");
            entity.Property(e => e.Title).IsRequired().HasMaxLength(255);
            entity.Property(e => e.VoucherType).IsRequired().HasMaxLength(50);
            entity.Property(e => e.ValueRm).HasColumnType("decimal(10,2)");
            entity.Property(e => e.IconUrl).HasMaxLength(500);
            entity.Property(e => e.IsActive).HasDefaultValue(true);
            entity.Property(e => e.DisplayOrder).HasDefaultValue(0);
        });

        // Configure UserVoucher entity
        modelBuilder.Entity<UserVoucher>(entity =>
        {
            entity.ToTable("user_vouchers");
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.Id).HasDefaultValueSql("gen_random_uuid()");
            entity.Property(e => e.UserId).IsRequired().HasMaxLength(255);
            entity.Property(e => e.VoucherCode).IsRequired().HasMaxLength(255);
            entity.Property(e => e.ClaimedAt).HasDefaultValueSql("NOW()");
            entity.Property(e => e.IsRevealed).HasDefaultValue(false);
            
            entity.HasOne(e => e.VoucherReward)
                .WithMany()
                .HasForeignKey(e => e.VoucherRewardId)
                .OnDelete(DeleteBehavior.Cascade);
            
            entity.HasIndex(e => e.UserId).HasDatabaseName("idx_user_vouchers");
        });
    }
}
