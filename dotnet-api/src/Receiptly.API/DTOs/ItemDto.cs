namespace Receiptly.API.DTOs;

/// <summary>
/// Data Transfer Object for receipt line items
/// </summary>
public class ItemDto
{
    public Guid Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public decimal Price { get; set; }
    public decimal? UnitPrice { get; set; }
    public int Quantity { get; set; }
    public decimal? TotalPrice { get; set; }
    public string? Category { get; set; }
    public string? Sku { get; set; }
    public string? Barcode { get; set; }
    public double? Confidence { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }
}
