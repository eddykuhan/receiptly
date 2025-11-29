using Receiptly.Domain.Models;

namespace Receiptly.Core.Interfaces;

public interface IReceiptRepository
{
    Task<Receipt> CreateAsync(Receipt receipt, CancellationToken cancellationToken = default);
    Task<Receipt?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<List<Receipt>> GetByUserIdAsync(string userId, CancellationToken cancellationToken = default);
    Task<Receipt?> GetByImageHashAsync(string userId, string imageHash, CancellationToken cancellationToken = default);
    Task<Receipt> UpdateAsync(Receipt receipt, CancellationToken cancellationToken = default);
    Task<bool> DeleteAsync(Guid id, CancellationToken cancellationToken = default);
}
