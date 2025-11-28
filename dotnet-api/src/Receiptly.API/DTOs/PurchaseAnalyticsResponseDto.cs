using Receiptly.Domain.Enums;
namespace Receiptly.API.DTOs;

public class PurchaseAnalyticsResponseDto
{
    public IReadOnlyCollection<PurchaseAnalyticsItemDto> Items { get; init; } = Array.Empty<PurchaseAnalyticsItemDto>();
    public long TotalCount { get; init; }
    public int Page { get; init; }
    public int PageSize { get; init; }
    public int TotalPages { get; init; }
    public bool IncludeMetadata { get; init; }
}

public class PurchaseAnalyticsItemDto
{
    public Guid ItemId { get; init; }
    public Guid ReceiptId { get; init; }
    public string ItemName { get; init; } = string.Empty;
    public string? Description { get; init; }
    public string? CanonicalName { get; init; }
    public decimal UnitPrice { get; init; }
    public int Quantity { get; init; }
    public decimal? TotalPrice { get; init; }
    public DateTime PurchaseDate { get; init; }
    public string StoreName { get; init; } = string.Empty;
    public PurchaseAnalyticsMetadataDto? Metadata { get; init; }
}

public class PurchaseAnalyticsMetadataDto
{
    public string? StoreAddress { get; init; }
    public string? StorePhoneNumber { get; init; }
    public double? Latitude { get; init; }
    public double? Longitude { get; init; }
    public string? ReceiptType { get; init; }
    public string? TransactionId { get; init; }
    public string? PaymentMethod { get; init; }
    public ReceiptStatus Status { get; init; }
}

