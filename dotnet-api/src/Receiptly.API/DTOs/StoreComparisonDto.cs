namespace Receiptly.API.DTOs;

public class StoreComparisonResponseDto
{
    public List<StoreStatsDto> Stores { get; set; } = new();
    public DateTime StartDate { get; set; }
    public DateTime EndDate { get; set; }
    public int TotalPurchases { get; set; }
    public decimal TotalSpent { get; set; }
}

public class StoreStatsDto
{
    public string StoreName { get; set; } = string.Empty;
    public int PurchaseCount { get; set; }
    public decimal TotalSpent { get; set; }
    public decimal AverageTransactionValue { get; set; }
    public decimal PriceIndex { get; set; } // Percentage above/below market average
    public int UniqueItemsCount { get; set; }
    public decimal? Latitude { get; set; }
    public decimal? Longitude { get; set; }
    public List<string> TopItems { get; set; } = new();
}
