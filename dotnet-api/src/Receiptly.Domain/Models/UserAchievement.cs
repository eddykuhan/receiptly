namespace Receiptly.Domain.Models;

public class UserAchievement
{
    public Guid Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public string AchievementType { get; set; } = string.Empty;
    public int PointsAwarded { get; set; }
    public DateTime UnlockedAt { get; set; }
}
