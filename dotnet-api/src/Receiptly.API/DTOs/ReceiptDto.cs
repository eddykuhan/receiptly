using Receiptly.Domain.Enums;

namespace Receiptly.API.DTOs;

/// <summary>
/// Data Transfer Object for receipt data returned to API clients
/// Excludes internal database fields and circular references
/// </summary>
public class ReceiptDto
{
    public Guid Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    
    // Store information
    public string StoreName { get; set; } = string.Empty;
    public string StoreAddress { get; set; } = string.Empty;
    public string? StorePhoneNumber { get; set; }
    public string? PostalCode { get; set; }
    public string? Country { get; set; }
    
    // Receipt details
    public DateTime PurchaseDate { get; set; }
    public decimal TotalAmount { get; set; }
    public decimal? SubtotalAmount { get; set; }
    public decimal? TaxAmount { get; set; }
    public decimal? TipAmount { get; set; }
    public string? ReceiptType { get; set; }
    public string? TransactionId { get; set; }
    public string? PaymentMethod { get; set; }
    
    // Items (no circular reference - Receipt property excluded from ItemDto)
    public List<ItemDto> Items { get; set; } = new();
    
    // Image and storage
    public string? ImageUrl { get; set; }
    public string? OriginalFileName { get; set; }
    public string? ImageHash { get; set; } // SHA256 hash for duplicate detection
    
    // Location data
    public double? Latitude { get; set; }
    public double? Longitude { get; set; }
    
    // OCR metadata
    public string? OcrProvider { get; set; }
    public double? OcrConfidence { get; set; }
    public double? LocationConfidence { get; set; }
    public string? OcrStrategy { get; set; }
    
    // Validation fields
    public ReceiptStatus Status { get; set; }
    public double? ValidationConfidence { get; set; }
    public string? ValidationMessage { get; set; }
    public bool IsValidReceipt { get; set; }
    
    // Audit fields
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }
    public DateTime? ProcessedAt { get; set; }
}
