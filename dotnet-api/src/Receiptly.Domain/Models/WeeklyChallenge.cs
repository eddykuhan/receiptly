namespace Receiptly.Domain.Models;

public class WeeklyChallenge
{
    public Guid Id { get; set; }
    public string ChallengeType { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string? Description { get; set; }
    public int PointsReward { get; set; }
    public int TargetCount { get; set; }
    public DateTime WeekStart { get; set; }
    public DateTime WeekEnd { get; set; }
    public bool IsActive { get; set; }
    public DateTime CreatedAt { get; set; }
}
