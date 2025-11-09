namespace Receiptly.Domain.Models;

public class Receipt
{
    public Guid Id { get; set; }
    public string StoreName { get; set; } = string.Empty;
    public string StoreAddress { get; set; } = string.Empty;
    public DateTime PurchaseDate { get; set; }
    public decimal TotalAmount { get; set; }
    public string? TaxAmount { get; set; }
    public List<Item> Items { get; set; } = new();
    public string? ImageUrl { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }
    public double? Latitude { get; set; }
    public double? Longitude { get; set; }
}