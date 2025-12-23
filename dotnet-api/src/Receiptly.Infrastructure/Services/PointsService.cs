using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Receiptly.Core.Interfaces;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Data;

namespace Receiptly.Infrastructure.Services;

public class PointsService : IPointsService
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<PointsService> _logger;

    public PointsService(ApplicationDbContext context, ILogger<PointsService> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task<UserPoints> GetUserPointsAsync(string userId, CancellationToken cancellationToken = default)
    {
        var userPoints = await _context.UserPoints
            .FirstOrDefaultAsync(up => up.UserId == userId, cancellationToken);

        if (userPoints == null)
        {
            // Create new user points record
            userPoints = new UserPoints
            {
                UserId = userId,
                TotalPoints = 0,
                AvailablePoints = 0,
                LifetimePoints = 0,
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow
            };
            
            _context.UserPoints.Add(userPoints);
            await _context.SaveChangesAsync(cancellationToken);
        }

        return userPoints;
    }

    public async Task<List<PointTransaction>> GetUserTransactionsAsync(string userId, int limit = 50, CancellationToken cancellationToken = default)
    {
        return await _context.PointTransactions
            .Where(pt => pt.UserId == userId)
            .OrderByDescending(pt => pt.EarnedAt)
            .Take(limit)
            .ToListAsync(cancellationToken);
    }

    public async Task<int> AwardPointsAsync(
        string userId, 
        int points, 
        string transactionType, 
        string description, 
        Guid? referenceId = null, 
        CancellationToken cancellationToken = default)
    {
        var strategy = _context.Database.CreateExecutionStrategy();
        
        return await strategy.ExecuteAsync(async () =>
        {
            using var transaction = await _context.Database.BeginTransactionAsync(cancellationToken);
            
            try
            {
                // Get or create user points
                var userPoints = await GetUserPointsAsync(userId, cancellationToken);
                
                // Create point transaction
                var pointTransaction = new PointTransaction
                {
                    UserId = userId,
                    Points = points,
                    TransactionType = transactionType,
                    Description = description,
                    ReferenceId = referenceId,
                    EarnedAt = DateTime.UtcNow,
                    ExpiresAt = DateTime.UtcNow.AddYears(1), // 1 year expiry
                    IsExpired = false
                };
                
                _context.PointTransactions.Add(pointTransaction);
                
                // Update user points
                userPoints.TotalPoints += points;
                userPoints.AvailablePoints += points;
                userPoints.LifetimePoints += points;
                userPoints.UpdatedAt = DateTime.UtcNow;
                
                _context.UserPoints.Update(userPoints);
                
                await _context.SaveChangesAsync(cancellationToken);
                await transaction.CommitAsync(cancellationToken);
                
                _logger.LogInformation("Awarded {Points} points to user {UserId} for {TransactionType}", 
                    points, userId, transactionType);
                
                return userPoints.AvailablePoints;
            }
            catch (Exception ex)
            {
                await transaction.RollbackAsync(cancellationToken);
                _logger.LogError(ex, "Failed to award points to user {UserId}", userId);
                throw;
            }
        });
    }

    public async Task<bool> DeductPointsAsync(string userId, int points, string reason, CancellationToken cancellationToken = default)
    {
        var strategy = _context.Database.CreateExecutionStrategy();
        
        return await strategy.ExecuteAsync(async () =>
        {
            using var transaction = await _context.Database.BeginTransactionAsync(cancellationToken);
            
            try
            {
                var userPoints = await GetUserPointsAsync(userId, cancellationToken);
                
                if (userPoints.AvailablePoints < points)
                {
                    _logger.LogWarning("Insufficient points for user {UserId}. Available: {Available}, Required: {Required}", 
                        userId, userPoints.AvailablePoints, points);
                    return false;
                }
                
                // Create deduction transaction
                var pointTransaction = new PointTransaction
                {
                    UserId = userId,
                    Points = -points,
                    TransactionType = "deduction",
                    Description = reason,
                    EarnedAt = DateTime.UtcNow,
                    ExpiresAt = DateTime.UtcNow, // Deductions don't expire
                    IsExpired = false
                };
                
                _context.PointTransactions.Add(pointTransaction);
                
                // Update user points
                userPoints.AvailablePoints -= points;
                userPoints.TotalPoints -= points;
                userPoints.UpdatedAt = DateTime.UtcNow;
                
                _context.UserPoints.Update(userPoints);
                
                await _context.SaveChangesAsync(cancellationToken);
                await transaction.CommitAsync(cancellationToken);
                
                _logger.LogInformation("Deducted {Points} points from user {UserId} for {Reason}", 
                    points, userId, reason);
                
                return true;
            }
            catch (Exception ex)
            {
                await transaction.RollbackAsync(cancellationToken);
                _logger.LogError(ex, "Failed to deduct points from user {UserId}", userId);
                throw;
            }
        });
    }

    public async Task<List<UserAchievement>> GetUserAchievementsAsync(string userId, CancellationToken cancellationToken = default)
    {
        return await _context.UserAchievements
            .Where(ua => ua.UserId == userId)
            .OrderByDescending(ua => ua.UnlockedAt)
            .ToListAsync(cancellationToken);
    }

    public async Task<List<UserAchievement>> CheckAndAwardAchievementsAsync(string userId, CancellationToken cancellationToken = default)
    {
        var newAchievements = new List<UserAchievement>();
        
        // Get existing achievements
        var existingAchievements = await GetUserAchievementsAsync(userId, cancellationToken);
        var existingTypes = existingAchievements.Select(a => a.AchievementType).ToHashSet();
        
        // Check first upload achievement
        if (!existingTypes.Contains("first_upload"))
        {
            var receiptsCount = await _context.Receipts
                .Where(r => r.UserId == userId)
                .CountAsync(cancellationToken);
            
            if (receiptsCount >= 1)
            {
                var achievement = await AwardAchievementAsync(userId, "first_upload", 50, "Uploaded your first receipt!", cancellationToken);
                newAchievements.Add(achievement);
            }
        }
        
        // Check five stores achievement
        if (!existingTypes.Contains("five_stores"))
        {
            var uniqueStoresCount = await _context.Receipts
                .Where(r => r.UserId == userId)
                .Select(r => r.StoreName)
                .Distinct()
                .CountAsync(cancellationToken);
            
            if (uniqueStoresCount >= 5)
            {
                var achievement = await AwardAchievementAsync(userId, "five_stores", 100, "Shopped at 5 different stores!", cancellationToken);
                newAchievements.Add(achievement);
            }
        }
        
        // Check three cities achievement
        if (!existingTypes.Contains("three_cities"))
        {
            var uniqueCitiesCount = await _context.Receipts
                .Where(r => r.UserId == userId && r.StoreAddress != null)
                .Select(r => r.StoreAddress)
                .Distinct()
                .CountAsync(cancellationToken);
            
            if (uniqueCitiesCount >= 3)
            {
                var achievement = await AwardAchievementAsync(userId, "three_cities", 150, "Explored 3 different locations!", cancellationToken);
                newAchievements.Add(achievement);
            }
        }
        
        // Check seven day streak (needs more complex logic - placeholder for now)
        // This would require tracking consecutive days of receipt uploads
        
        return newAchievements;
    }

    private async Task<UserAchievement> AwardAchievementAsync(
        string userId, 
        string achievementType, 
        int points, 
        string description,
        CancellationToken cancellationToken)
    {
        var achievement = new UserAchievement
        {
            UserId = userId,
            AchievementType = achievementType,
            PointsAwarded = points,
            UnlockedAt = DateTime.UtcNow
        };
        
        _context.UserAchievements.Add(achievement);
        await _context.SaveChangesAsync(cancellationToken);
        
        // Award the points
        await AwardPointsAsync(userId, points, "achievement", description, achievement.Id, cancellationToken);
        
        _logger.LogInformation("User {UserId} unlocked achievement {AchievementType} for {Points} points", 
            userId, achievementType, points);
        
        return achievement;
    }

    /// <summary>
    /// Get all active weekly challenges (current week)
    /// </summary>
    public async Task<List<WeeklyChallenge>> GetActiveWeeklyChallengesAsync(CancellationToken cancellationToken = default)
    {
        var now = DateTime.UtcNow;

        return await _context.WeeklyChallenges
            .Where(wc => wc.WeekStart <= now && wc.WeekEnd >= now && wc.IsActive)
            .OrderBy(wc => wc.CreatedAt)
            .ToListAsync(cancellationToken);
    }

    /// <summary>
    /// Get user's progress on weekly challenges
    /// </summary>
    public async Task<List<UserWeeklyProgress>> GetUserWeeklyProgressAsync(string userId, CancellationToken cancellationToken = default)
    {
        return await _context.UserWeeklyProgress
            .Where(uwp => uwp.UserId == userId)
            .OrderByDescending(uwp => uwp.WeekStart)
            .ToListAsync(cancellationToken);
    }

    /// <summary>
    /// Update user's progress on a weekly challenge
    /// </summary>
    public async Task<UserWeeklyProgress> UpdateUserWeeklyProgressAsync(string userId, Guid challengeId, int progressValue, CancellationToken cancellationToken = default)
    {
        var challenge = await _context.WeeklyChallenges.FindAsync(new object[] { challengeId }, cancellationToken: cancellationToken);
        if (challenge == null)
        {
            throw new InvalidOperationException($"Challenge {challengeId} not found");
        }

        var progress = await _context.UserWeeklyProgress
            .FirstOrDefaultAsync(uwp => uwp.UserId == userId && uwp.ChallengeId == challengeId, cancellationToken);

        if (progress == null)
        {
            progress = new UserWeeklyProgress
            {
                UserId = userId,
                ChallengeId = challengeId,
                CurrentCount = progressValue,
                TargetCount = challenge.TargetCount,
                IsCompleted = progressValue >= challenge.TargetCount,
                WeekStart = challenge.WeekStart
            };
            _context.UserWeeklyProgress.Add(progress);
        }
        else
        {
            progress.CurrentCount = progressValue;
            progress.IsCompleted = progressValue >= challenge.TargetCount;
            _context.UserWeeklyProgress.Update(progress);
        }

        await _context.SaveChangesAsync(cancellationToken);

        // Award bonus points if challenge just completed
        if (progress.IsCompleted && progress.CompletedAt == null)
        {
            await AwardPointsAsync(userId, challenge.PointsReward, "challenge_completion", $"Completed: {challenge.Title}", challengeId, cancellationToken);
            progress.CompletedAt = DateTime.UtcNow;
            _context.UserWeeklyProgress.Update(progress);
            await _context.SaveChangesAsync(cancellationToken);
        }

        return progress;
    }
}
