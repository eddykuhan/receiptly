namespace Receiptly.Domain.Exceptions;

/// <summary>
/// Exception thrown when OCR processing fails to extract valid receipt data
/// </summary>
public class OcrProcessingException : Exception
{
    public Guid ReceiptId { get; }
    public string? OcrResponse { get; }
    
    public OcrProcessingException(Guid receiptId, string message, string? ocrResponse = null) 
        : base(message)
    {
        ReceiptId = receiptId;
        OcrResponse = ocrResponse;
    }
    
    public OcrProcessingException(Guid receiptId, string message, Exception innerException, string? ocrResponse = null) 
        : base(message, innerException)
    {
        ReceiptId = receiptId;
        OcrResponse = ocrResponse;
    }
}

/// <summary>
/// Exception thrown when receipt validation fails (not a valid receipt)
/// </summary>
public class InvalidReceiptException : Exception
{
    public Guid ReceiptId { get; }
    public float Confidence { get; }
    
    public InvalidReceiptException(Guid receiptId, float confidence, string message) 
        : base(message)
    {
        ReceiptId = receiptId;
        Confidence = confidence;
    }
}

/// <summary>
/// Exception thrown when receipt quality is too poor for OCR processing
/// </summary>
public class PoorImageQualityException : Exception
{
    public Guid ReceiptId { get; }
    
    public PoorImageQualityException(Guid receiptId, string message) 
        : base(message)
    {
        ReceiptId = receiptId;
    }
}

/// <summary>
/// Exception thrown when required receipt fields are missing
/// </summary>
public class MissingRequiredFieldsException : Exception
{
    public Guid ReceiptId { get; }
    public List<string> MissingFields { get; }
    
    public MissingRequiredFieldsException(Guid receiptId, List<string> missingFields) 
        : base($"Receipt is missing required fields: {string.Join(", ", missingFields)}")
    {
        ReceiptId = receiptId;
        MissingFields = missingFields;
    }
}
