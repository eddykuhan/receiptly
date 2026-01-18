using System;

namespace Receiptly.Core.Models;

/// <summary>
/// Request model for submitting a user correction to OCR results.
/// </summary>
public class SubmitCorrectionRequest
{
    /// <summary>
    /// Receipt ID being corrected.
    /// </summary>
    public Guid ReceiptId { get; set; }
    
    /// <summary>
    /// Field name being corrected (e.g., "StoreName", "TotalAmount", "Items[0].Name").
    /// </summary>
    public string FieldName { get; set; } = string.Empty;
    
    /// <summary>
    /// Incorrect value extracted by OCR (for comparison).
    /// </summary>
    public string? IncorrectValue { get; set; }
    
    /// <summary>
    /// Corrected value provided by user.
    /// </summary>
    public string CorrectedValue { get; set; } = string.Empty;
    
    /// <summary>
    /// Latitude of corrected store location (optional, for address corrections).
    /// </summary>
    public double? Latitude { get; set; }
    
    /// <summary>
    /// Longitude of corrected store location (optional, for address corrections).
    /// </summary>
    public double? Longitude { get; set; }
}
