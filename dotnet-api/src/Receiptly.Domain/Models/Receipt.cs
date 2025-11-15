namespace Receiptly.Domain.Models;

using Receiptly.Domain.Enums;

public class Receipt
{
    public Guid Id { get; set; }
    
    // User information
    public string UserId { get; set; } = string.Empty;
    
    // Store information (from Tesseract OCR)
    public string StoreName { get; set; } = string.Empty;
    public string StoreAddress { get; set; } = string.Empty;
    public string? StorePhoneNumber { get; set; }
    public string? PostalCode { get; set; }
    public string? Country { get; set; }
    
    // Receipt details (from Azure Document Intelligence)
    public DateTime PurchaseDate { get; set; }
    public decimal TotalAmount { get; set; }
    public decimal? SubtotalAmount { get; set; }
    public decimal? TaxAmount { get; set; }
    public decimal? TipAmount { get; set; }
    public string? ReceiptType { get; set; } // e.g., "receipt.retailMeal"
    public string? TransactionId { get; set; }
    public string? PaymentMethod { get; set; }
    
    // Items
    public List<Item> Items { get; set; } = new();
    
    // Image and storage
    public string? ImageUrl { get; set; }
    public string? S3Key { get; set; } // AWS S3 object key
    public string? OriginalFileName { get; set; }
    public string? ImageHash { get; set; } // SHA256 hash for duplicate detection
    
    // Location data
    public double? Latitude { get; set; }
    public double? Longitude { get; set; }
    
    // OCR Processing metadata
    public string? OcrProvider { get; set; } // "Azure", "Tesseract", "Hybrid"
    public double? OcrConfidence { get; set; } // Azure confidence score
    public double? LocationConfidence { get; set; } // Tesseract location confidence
    public string? OcrStrategy { get; set; } // Tesseract preprocessing strategy used
    
    // Validation fields
    public ReceiptStatus Status { get; set; } = ReceiptStatus.PendingValidation;
    public double? ValidationConfidence { get; set; }
    public string? ValidationMessage { get; set; }
    public bool IsValidReceipt { get; set; }
    
    // Audit fields
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }
    public DateTime? ProcessedAt { get; set; } // When OCR processing completed
}