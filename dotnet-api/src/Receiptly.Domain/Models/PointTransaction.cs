namespace Receiptly.Domain.Models;

public class PointTransaction
{
    public Guid Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public int Points { get; set; }
    public string TransactionType { get; set; } = string.Empty;
    public string? Description { get; set; }
    public Guid? ReferenceId { get; set; }
    public DateTime EarnedAt { get; set; }
    public DateTime ExpiresAt { get; set; }
    public bool IsExpired { get; set; }
}
