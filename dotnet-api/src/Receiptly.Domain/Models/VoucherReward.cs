namespace Receiptly.Domain.Models;

public class VoucherReward
{
    public Guid Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string? Description { get; set; }
    public int PointsRequired { get; set; }
    public string VoucherType { get; set; } = string.Empty;
    public decimal ValueRm { get; set; }
    public string? IconUrl { get; set; }
    public bool IsActive { get; set; }
    public int DisplayOrder { get; set; }
}
