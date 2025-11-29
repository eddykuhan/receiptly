namespace Receiptly.Domain.Models;

public class Item
{
    public Guid Id { get; set; }
    
    // Product information
    public string Name { get; set; } = string.Empty;
    public string? CanonicalName { get; set; }
    public string? Description { get; set; }
    public decimal Price { get; set; }
    public decimal? UnitPrice { get; set; }
    public int Quantity { get; set; }
    public decimal? TotalPrice { get; set; } // Price * Quantity
    
    // Additional details
    public string? Category { get; set; }
    public string? Sku { get; set; }
    public string? Barcode { get; set; }
    
    // OCR metadata
    public double? Confidence { get; set; } // OCR confidence for this item
    
    // Relationship
    public Guid ReceiptId { get; set; }
    public Receipt? Receipt { get; set; }
    
    // Audit
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }
}