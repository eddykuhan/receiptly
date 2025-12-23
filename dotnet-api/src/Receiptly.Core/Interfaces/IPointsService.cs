using Receiptly.Domain.Models;

namespace Receiptly.Core.Interfaces;

public interface IPointsService
{
    Task<UserPoints> GetUserPointsAsync(string userId, CancellationToken cancellationToken = default);
    Task<List<PointTransaction>> GetUserTransactionsAsync(string userId, int limit = 50, CancellationToken cancellationToken = default);
    Task<int> AwardPointsAsync(string userId, int points, string transactionType, string description, Guid? referenceId = null, CancellationToken cancellationToken = default);
    Task<bool> DeductPointsAsync(string userId, int points, string reason, CancellationToken cancellationToken = default);
    Task<List<UserAchievement>> GetUserAchievementsAsync(string userId, CancellationToken cancellationToken = default);
    Task<List<UserAchievement>> CheckAndAwardAchievementsAsync(string userId, CancellationToken cancellationToken = default);
    
    // Weekly Challenges
    Task<List<WeeklyChallenge>> GetActiveWeeklyChallengesAsync(CancellationToken cancellationToken = default);
    Task<List<UserWeeklyProgress>> GetUserWeeklyProgressAsync(string userId, CancellationToken cancellationToken = default);
    Task<UserWeeklyProgress> UpdateUserWeeklyProgressAsync(string userId, Guid challengeId, int progressValue, CancellationToken cancellationToken = default);
}
