namespace Receiptly.Domain.Models;

/// <summary>
/// Append-only gold layer for price history and analytics.
/// Preserves item purchase data with location and time for price trend analysis.
/// Never deleted - provides historical price comparison across stores and time periods.
/// </summary>
public class PurchaseAnalyticsGold
{
    public Guid Id { get; set; }
    
    // Source references (preserved even if original receipt/item deleted)
    public Guid ItemId { get; set; }
    public Guid ReceiptId { get; set; }
    public string UserId { get; set; } = string.Empty;
    
    // Item details (denormalized from Items table)
    public string ItemName { get; set; } = string.Empty;
    public string? CanonicalName { get; set; }
    public decimal UnitPrice { get; set; }
    public decimal TotalPrice { get; set; }
    public int Quantity { get; set; }
    
    // Purchase context (denormalized from Receipts table)
    public DateTime PurchaseDate { get; set; }
    public string StoreName { get; set; } = string.Empty;
    public string StoreAddress { get; set; } = string.Empty;
    public string? StorePhoneNumber { get; set; }
    
    // Location data (critical for price map and geographic analysis)
    public double? Latitude { get; set; }
    public double? Longitude { get; set; }
    public double? LocationConfidence { get; set; }
    
    // Receipt metadata
    public string? ReceiptType { get; set; }
    public string? TransactionId { get; set; }
    public string? PaymentMethod { get; set; }
    public string? ReceiptStatus { get; set; }
    
    // Correction tracking
    public bool IsCorrected { get; set; }
    public DateTime? CorrectedAt { get; set; }
    
    // Audit (append-only, no UpdatedAt)
    public DateTime CreatedAt { get; set; }
}
