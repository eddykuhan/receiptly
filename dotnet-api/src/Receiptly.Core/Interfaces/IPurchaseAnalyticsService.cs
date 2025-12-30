using Receiptly.Domain.Enums;

namespace Receiptly.Core.Interfaces;

public interface IPurchaseAnalyticsService
{
    Task<PurchaseAnalyticsResult> GetPurchasesAsync(
        PurchaseAnalyticsQuery query,
        CancellationToken cancellationToken = default);

    Task<PriceHistoryResult> GetPriceHistoryAsync(
        string userId,
        string canonicalName,
        int days,
        CancellationToken cancellationToken = default);

    Task<SavingsReportResult> GetSavingsReportAsync(
        string userId,
        int days,
        CancellationToken cancellationToken = default);

    Task<StoreComparisonResult> GetStoreComparisonAsync(
        string userId,
        int days,
        CancellationToken cancellationToken = default);

    Task<List<SuggestionResult>> GetSuggestionsAsync(
        string query,
        double? userLat = null,
        double? userLng = null,
        double? radiusKm = null,
        int limit = 10,
        CancellationToken cancellationToken = default);

    Task<List<string>> GetCategoriesAsync(CancellationToken cancellationToken = default);

    Task<List<StoreStats>> GetNearbyStoresAsync(
        double lat,
        double lng,
        double radiusKm,
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
    public Guid? CanonicalItemId { get; init; }
    public string? Category { get; init; }
    public double? UserLatitude { get; init; }
    public double? UserLongitude { get; init; }
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
    public Guid? ReceiptId { get; init; }
    public string ItemName { get; init; } = string.Empty;
    public string? Description { get; init; }
    public string? CanonicalName { get; init; }
    public decimal UnitPrice { get; init; }
    public decimal? TotalPrice { get; init; }
    public int Quantity { get; init; }
    public DateTime PurchaseDate { get; init; }
    public string StoreName { get; init; } = string.Empty;
    public string? Category { get; init; }
    public string? StoreAddress { get; init; }
    public string? StorePhoneNumber { get; init; }
    public double? Latitude { get; init; }
    public double? Longitude { get; init; }
    public ReceiptStatus Status { get; init; }
    public string? ReceiptType { get; init; }
    public string? TransactionId { get; init; }
    public string? PaymentMethod { get; init; }
}

// Price History Models
public class PriceHistoryResult
{
    public string CanonicalName { get; init; } = string.Empty;
    public List<PriceHistoryPoint> PricePoints { get; init; } = new();
    public PriceStatistics Statistics { get; init; } = new();
}

public class PriceHistoryPoint
{
    public DateTime PurchaseDate { get; init; }
    public decimal UnitPrice { get; init; }
    public string StoreName { get; init; } = string.Empty;
    public Guid ItemId { get; init; }
}

public class PriceStatistics
{
    public decimal MinPrice { get; init; }
    public decimal MaxPrice { get; init; }
    public decimal AveragePrice { get; init; }
    public decimal CurrentPrice { get; init; }
    public string CheapestStore { get; init; } = string.Empty;
    public string MostExpensiveStore { get; init; } = string.Empty;
}

// Savings Report Models
public class SavingsReportResult
{
    public decimal TotalSpent { get; init; }
    public decimal PotentialSavings { get; init; }
    public decimal SavingsPercentage { get; init; }
    public List<SavingsOpportunity> Opportunities { get; init; } = new();
    public DateTime StartDate { get; init; }
    public DateTime EndDate { get; init; }
}

public class SavingsOpportunity
{
    public string CanonicalName { get; init; } = string.Empty;
    public string PurchasedAt { get; init; } = string.Empty;
    public decimal PaidPrice { get; init; }
    public string CheaperAt { get; init; } = string.Empty;
    public decimal CheaperPrice { get; init; }
    public decimal PotentialSaving { get; init; }
    public int Quantity { get; init; }
    public DateTime PurchaseDate { get; init; }
}

// Store Comparison Models
public class StoreComparisonResult
{
    public List<StoreStats> Stores { get; init; } = new();
    public DateTime StartDate { get; init; }
    public DateTime EndDate { get; init; }
    public int TotalPurchases { get; init; }
    public decimal TotalSpent { get; init; }
}

public class StoreStats
{
    public string StoreName { get; init; } = string.Empty;
    public int PurchaseCount { get; init; }
    public decimal TotalSpent { get; init; }
    public decimal AverageTransactionValue { get; init; }
    public decimal PriceIndex { get; init; }
    public int UniqueItemsCount { get; init; }
    public double? Latitude { get; init; }
    public double? Longitude { get; init; }
    public List<string> TopItems { get; init; } = new();
}

public class SuggestionResult
{
    public Guid Id { get; init; }
    public string Name { get; init; } = string.Empty;
}

