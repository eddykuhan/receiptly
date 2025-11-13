namespace Receiptly.Domain.Enums;

/// <summary>
/// Represents the processing status of a receipt
/// </summary>
public enum ReceiptStatus
{
    /// <summary>
    /// Receipt uploaded but not yet validated
    /// </summary>
    PendingValidation = 0,
    
    /// <summary>
    /// Receipt validated successfully
    /// </summary>
    Validated = 1,
    
    /// <summary>
    /// Receipt validation failed (not a receipt, low confidence, etc.)
    /// </summary>
    ValidationFailed = 2,
    
    /// <summary>
    /// Receipt is being processed
    /// </summary>
    Processing = 3,
    
    /// <summary>
    /// Receipt processed successfully
    /// </summary>
    Processed = 4,
    
    /// <summary>
    /// Processing failed
    /// </summary>
    ProcessingFailed = 5
}
