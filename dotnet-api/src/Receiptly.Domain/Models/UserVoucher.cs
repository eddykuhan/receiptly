namespace Receiptly.Domain.Models;

public class UserVoucher
{
    public Guid Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public Guid VoucherRewardId { get; set; }
    public string VoucherCode { get; set; } = string.Empty;
    public int PointsSpent { get; set; }
    public DateTime ClaimedAt { get; set; }
    public DateTime? RevealedAt { get; set; }
    public DateTime? RevealExpiresAt { get; set; }
    public bool IsRevealed { get; set; }
    
    // Navigation property
    public VoucherReward? VoucherReward { get; set; }
}
