namespace Receiptly.Domain.Exceptions;

/// <summary>
/// Exception thrown when a duplicate receipt is detected based on image hash
/// </summary>
public class DuplicateReceiptException : Exception
{
    /// <summary>
    /// The ID of the existing receipt with the same image hash
    /// </summary>
    public Guid ExistingReceiptId { get; }
    
    /// <summary>
    /// The image hash that was duplicated
    /// </summary>
    public string ImageHash { get; }
    
    public DuplicateReceiptException(Guid existingReceiptId, string imageHash)
        : base($"A receipt with the same image already exists. Existing receipt ID: {existingReceiptId}")
    {
        ExistingReceiptId = existingReceiptId;
        ImageHash = imageHash;
    }
    
    public DuplicateReceiptException(Guid existingReceiptId, string imageHash, string message)
        : base(message)
    {
        ExistingReceiptId = existingReceiptId;
        ImageHash = imageHash;
    }
    
    public DuplicateReceiptException(Guid existingReceiptId, string imageHash, string message, Exception innerException)
        : base(message, innerException)
    {
        ExistingReceiptId = existingReceiptId;
        ImageHash = imageHash;
    }
}
