using System;
using System.Collections.Generic;

namespace Receiptly.Domain.Models;

/// <summary>
/// User correction to OCR results for ML training and accuracy improvement.
/// </summary>
public class UserCorrection
{
    public Guid Id { get; set; }
    public Guid ReceiptId { get; set; }
    public string UserId { get; set; } = string.Empty;
    
    // Field-level correction
    public string FieldName { get; set; } = string.Empty;  // "StoreName", "TotalAmount", "Items[0].Name"
    public string? IncorrectValue { get; set; }  // What OCR extracted
    public string CorrectedValue { get; set; } = string.Empty;  // What user corrected to
    
    // Location data (for store address corrections)
    public double? Latitude { get; set; }
    public double? Longitude { get; set; }
    
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    // Navigation properties
    public Receipt? Receipt { get; set; }
}

/// <summary>
/// User-reported issue with OCR processing.
/// </summary>
public class IssueReport
{
    public Guid Id { get; set; }
    public Guid ReceiptId { get; set; }
    public string UserId { get; set; } = string.Empty;
    
    public string IssueType { get; set; } = string.Empty;  // wrong_merchant, wrong_total, etc.
    public string? Description { get; set; }
    public string Severity { get; set; } = "Medium";  // Low, Medium, High, Critical
    
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    // Navigation properties
    public Receipt? Receipt { get; set; }
}

/// <summary>
/// Temporary debug mode activation for specific users.
/// </summary>
public class UserDebugSession
{
    public Guid Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public string SessionId { get; set; } = string.Empty;
    public DateTime StartedAt { get; set; } = DateTime.UtcNow;
    public DateTime ExpiresAt { get; set; }
    public string? Reason { get; set; }
}
