using Receiptly.Domain.Models;

namespace Receiptly.Core.Interfaces;

/// <summary>
/// Service interface for applying user corrections to receipts
/// </summary>
public interface IReceiptCorrectionService
{
    /// <summary>
    /// Apply user corrections to a single receipt
    /// </summary>
    Task ApplyCorrectionsAsync(Receipt receipt, CancellationToken cancellationToken = default);

    /// <summary>
    /// Apply user corrections to multiple receipts
    /// </summary>
    Task ApplyCorrectionsAsync(List<Receipt> receipts, CancellationToken cancellationToken = default);
}
