namespace Receiptly.API.DTOs;

/// <summary>
/// Query parameters accepted by the analytics purchases endpoint.
/// </summary>
public class PurchaseAnalyticsRequest
{
    private const int DefaultPageSize = 50;

    public int Page { get; set; } = 1;

    private int _pageSize = DefaultPageSize;
    public int PageSize
    {
        get => _pageSize;
        set => _pageSize = value <= 0 ? DefaultPageSize : value;
    }

    public DateTime? StartDate { get; set; }
    public DateTime? EndDate { get; set; }
    public string? StoreName { get; set; }
    public string? ProductName { get; set; }
    public string? Category { get; set; }
    public double? MinLat { get; set; }
    public double? MaxLat { get; set; }
    public double? MinLng { get; set; }
    public double? MaxLng { get; set; }
    public bool IncludeMetadata { get; set; }
}

