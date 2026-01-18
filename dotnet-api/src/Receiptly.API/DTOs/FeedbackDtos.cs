using System;
using System.ComponentModel.DataAnnotations;

namespace Receiptly.API.DTOs;

/// <summary>
/// Request to submit a correction to OCR results.
/// </summary>
public class SubmitCorrectionDto
{
    [Required]
    public Guid ReceiptId { get; set; }
    
    [Required]
    [StringLength(100)]
    public string FieldName { get; set; } = string.Empty;  // "StoreName", "TotalAmount", "Items[0].Name"
    
    [StringLength(1000)]
    public string? IncorrectValue { get; set; }  // What OCR extracted
    
    [Required]
    [StringLength(1000)]
    public string CorrectedValue { get; set; } = string.Empty;  // What user corrected to
    
    public double? Latitude { get; set; }  // Latitude for address corrections
    
    public double? Longitude { get; set; }  // Longitude for address corrections
}

/// <summary>
/// Response from feedback submission.
/// </summary>
public class FeedbackResponseDto
{
    public bool Success { get; set; }
    public string Message { get; set; } = string.Empty;
    public Guid? CorrectionId { get; set; }
}

/// <summary>
/// Receipt validation information from Python OCR service.
/// </summary>
public class ReceiptValidationDto
{
    public bool IsValidReceipt { get; set; }
    public string ConfidenceLevel { get; set; } = string.Empty;  // high, medium, low, very_low
    public double OverallConfidence { get; set; }
    public double MerchantConfidence { get; set; }
    public double ItemsConfidence { get; set; }
    public double TotalConfidence { get; set; }
    
    public List<ValidationIssueDto> Issues { get; set; } = new();
    public List<string> Warnings { get; set; } = new();
    public bool RequiresManualReview { get; set; }
    
    public string DocType { get; set; } = string.Empty;
    public int ProcessingTimeMs { get; set; }
    public List<string> SourcesUsed { get; set; } = new();
    
    public string ConfidenceMessage { get; set; } = string.Empty;
    public string? NextSteps { get; set; }
}

/// <summary>
/// Individual validation issue.
/// </summary>
public class ValidationIssueDto
{
    public string Field { get; set; } = string.Empty;
    public string IssueType { get; set; } = string.Empty;  // low_confidence, missing, suspicious
    public string Severity { get; set; } = string.Empty;  // warning, error
    public string Message { get; set; } = string.Empty;
    public double? Confidence { get; set; }
    public string? SuggestedAction { get; set; }
}
