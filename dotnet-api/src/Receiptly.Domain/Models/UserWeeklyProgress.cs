namespace Receiptly.Domain.Models;

public class UserWeeklyProgress
{
    public Guid Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public Guid ChallengeId { get; set; }
    public int CurrentCount { get; set; }
    public int TargetCount { get; set; }
    public bool IsCompleted { get; set; }
    public DateTime? CompletedAt { get; set; }
    public DateTime WeekStart { get; set; }
    
    // Navigation property
    public WeeklyChallenge? Challenge { get; set; }
}
