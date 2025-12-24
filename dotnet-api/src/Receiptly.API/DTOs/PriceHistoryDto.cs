namespace Receiptly.API.DTOs;

public class PriceHistoryResponseDto
{
    public string CanonicalName { get; set; } = string.Empty;
    public List<PriceHistoryPointDto> PricePoints { get; set; } = new();
    public PriceStatisticsDto Statistics { get; set; } = new();
}

public class PriceHistoryPointDto
{
    public DateTime PurchaseDate { get; set; }
    public decimal UnitPrice { get; set; }
    public string StoreName { get; set; } = string.Empty;
    public Guid ItemId { get; set; }
}

public class PriceStatisticsDto
{
    public decimal MinPrice { get; set; }
    public decimal MaxPrice { get; set; }
    public decimal AveragePrice { get; set; }
    public decimal CurrentPrice { get; set; }
    public string CheapestStore { get; set; } = string.Empty;
    public string MostExpensiveStore { get; set; } = string.Empty;
}
