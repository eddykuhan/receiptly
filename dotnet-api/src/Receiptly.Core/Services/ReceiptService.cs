using Receiptly.Core.Interfaces;
using Receiptly.Domain.Models;

namespace Receiptly.Core.Services;

/// <summary>
/// Service for receipt operations with automatic correction application
/// </summary>
public class ReceiptService : IReceiptService
{
    private readonly IReceiptRepository _receiptRepository;
    private readonly IReceiptCorrectionService _correctionService;

    public ReceiptService(
        IReceiptRepository receiptRepository,
        IReceiptCorrectionService correctionService)
    {
        _receiptRepository = receiptRepository;
        _correctionService = correctionService;
    }

    public async Task<Receipt?> GetReceiptByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        var receipt = await _receiptRepository.GetByIdAsync(id, cancellationToken);

        if (receipt == null)
        {
            return null;
        }

        // Apply user corrections
        await _correctionService.ApplyCorrectionsAsync(receipt, cancellationToken);

        return receipt;
    }

    public async Task<List<Receipt>> GetReceiptsByUserIdAsync(string userId, CancellationToken cancellationToken = default)
    {
        var receipts = await _receiptRepository.GetByUserIdAsync(userId, cancellationToken);

        if (receipts == null || !receipts.Any())
        {
            return receipts ?? new List<Receipt>();
        }

        // Apply user corrections to all receipts
        await _correctionService.ApplyCorrectionsAsync(receipts, cancellationToken);

        return receipts;
    }

    public async Task<Receipt> UpdateReceiptAsync(Receipt receipt, CancellationToken cancellationToken = default)
    {
        var updatedReceipt = await _receiptRepository.UpdateAsync(receipt, cancellationToken);

        // Apply corrections to the updated receipt
        await _correctionService.ApplyCorrectionsAsync(updatedReceipt, cancellationToken);

        return updatedReceipt;
    }

    public async Task DeleteReceiptAsync(Guid id, CancellationToken cancellationToken = default)
    {
        await _receiptRepository.DeleteAsync(id, cancellationToken);
    }
}
