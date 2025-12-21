using Receiptly.Domain.Models;

namespace Receiptly.Core.Interfaces;

/// <summary>
/// Service interface for receipt operations with automatic correction application
/// </summary>
public interface IReceiptService
{
    /// <summary>
    /// Get receipt by ID with user corrections applied
    /// </summary>
    Task<Receipt?> GetReceiptByIdAsync(Guid id, CancellationToken cancellationToken = default);

    /// <summary>
    /// Get all receipts for a user with user corrections applied
    /// </summary>
    Task<List<Receipt>> GetReceiptsByUserIdAsync(string userId, CancellationToken cancellationToken = default);

    /// <summary>
    /// Update an existing receipt
    /// </summary>
    Task<Receipt> UpdateReceiptAsync(Receipt receipt, CancellationToken cancellationToken = default);

    /// <summary>
    /// Delete a receipt
    /// </summary>
    Task DeleteReceiptAsync(Guid id, CancellationToken cancellationToken = default);
}
