using Receiptly.Domain.Enums;

namespace Receiptly.Core.Interfaces;

public interface IPurchaseAnalyticsService
{
    Task<PurchaseAnalyticsResult> GetPurchasesAsync(
        PurchaseAnalyticsQuery query,
        CancellationToken cancellationToken = default);
}

public class PurchaseAnalyticsQuery
{
    public int Page { get; init; } = 1;
    public int PageSize { get; init; } = 50;
    public DateTime? StartDate { get; init; }
    public DateTime? EndDate { get; init; }
    public string? StoreName { get; init; }
    public string? ProductName { get; init; }
    public double? MinLatitude { get; init; }
    public double? MaxLatitude { get; init; }
    public double? MinLongitude { get; init; }
    public double? MaxLongitude { get; init; }
    public bool IncludeMetadata { get; init; }
}

public class PurchaseAnalyticsResult
{
    public IReadOnlyList<PurchaseAnalyticsRecord> Items { get; init; } = Array.Empty<PurchaseAnalyticsRecord>();
    public long TotalCount { get; init; }
    public int Page { get; init; }
    public int PageSize { get; init; }
}

public class PurchaseAnalyticsRecord
{
    public Guid ItemId { get; init; }
    public Guid ReceiptId { get; init; }
    public string ItemName { get; init; } = string.Empty;
    public string? Description { get; init; }
    public string? CanonicalName { get; init; }
    public decimal UnitPrice { get; init; }
    public decimal? TotalPrice { get; init; }
    public int Quantity { get; init; }
    public DateTime PurchaseDate { get; init; }
    public string StoreName { get; init; } = string.Empty;
    public string? StoreAddress { get; init; }
    public string? StorePhoneNumber { get; init; }
    public double? Latitude { get; init; }
    public double? Longitude { get; init; }
    public ReceiptStatus Status { get; init; }
    public string? ReceiptType { get; init; }
    public string? TransactionId { get; init; }
    public string? PaymentMethod { get; init; }
}

