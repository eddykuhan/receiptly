using Microsoft.EntityFrameworkCore;
using Receiptly.Core.Interfaces;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Data;

namespace Receiptly.Infrastructure.Repositories;

public class ReceiptRepository : IReceiptRepository
{
    private readonly ApplicationDbContext _context;

    public ReceiptRepository(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task<Receipt> CreateAsync(Receipt receipt, CancellationToken cancellationToken = default)
    {
        // Ensure all DateTime fields are UTC for PostgreSQL
        EnsureUtcDates(receipt);
        
        _context.Receipts.Add(receipt);
        await _context.SaveChangesAsync(cancellationToken);
        return receipt;
    }

    public async Task<Receipt?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return await _context.Receipts
            .Include(r => r.Items)
            .FirstOrDefaultAsync(r => r.Id == id, cancellationToken);
    }

    public async Task<List<Receipt>> GetByUserIdAsync(string userId, CancellationToken cancellationToken = default)
    {
        return await _context.Receipts
            .Include(r => r.Items)
            .Where(r => r.UserId == userId)
            .OrderByDescending(r => r.CreatedAt)
            .ToListAsync(cancellationToken);
    }

    public async Task<Receipt> UpdateAsync(Receipt receipt, CancellationToken cancellationToken = default)
    {
        receipt.UpdatedAt = DateTime.UtcNow;
        EnsureUtcDates(receipt);
        
        _context.Receipts.Update(receipt);
        await _context.SaveChangesAsync(cancellationToken);
        return receipt;
    }

    public async Task<bool> DeleteAsync(Guid id, CancellationToken cancellationToken = default)
    {
        var receipt = await _context.Receipts.FindAsync(new object[] { id }, cancellationToken);
        if (receipt == null)
        {
            return false;
        }

        _context.Receipts.Remove(receipt);
        await _context.SaveChangesAsync(cancellationToken);
        return true;
    }

    /// <summary>
    /// Ensures all DateTime fields are UTC to prevent PostgreSQL timestamp errors
    /// </summary>
    private void EnsureUtcDates(Receipt receipt)
    {
        // Convert PurchaseDate if it's not UTC
        if (receipt.PurchaseDate != default && receipt.PurchaseDate.Kind != DateTimeKind.Utc)
        {
            receipt.PurchaseDate = DateTime.SpecifyKind(receipt.PurchaseDate, DateTimeKind.Utc);
        }

        // Ensure CreatedAt is UTC
        if (receipt.CreatedAt.Kind != DateTimeKind.Utc)
        {
            receipt.CreatedAt = receipt.CreatedAt.Kind == DateTimeKind.Unspecified
                ? DateTime.SpecifyKind(receipt.CreatedAt, DateTimeKind.Utc)
                : receipt.CreatedAt.ToUniversalTime();
        }

        // Ensure UpdatedAt is UTC if set
        if (receipt.UpdatedAt.HasValue && receipt.UpdatedAt.Value.Kind != DateTimeKind.Utc)
        {
            receipt.UpdatedAt = receipt.UpdatedAt.Value.Kind == DateTimeKind.Unspecified
                ? DateTime.SpecifyKind(receipt.UpdatedAt.Value, DateTimeKind.Utc)
                : receipt.UpdatedAt.Value.ToUniversalTime();
        }

        // Ensure ProcessedAt is UTC if set
        if (receipt.ProcessedAt.HasValue && receipt.ProcessedAt.Value.Kind != DateTimeKind.Utc)
        {
            receipt.ProcessedAt = receipt.ProcessedAt.Value.Kind == DateTimeKind.Unspecified
                ? DateTime.SpecifyKind(receipt.ProcessedAt.Value, DateTimeKind.Utc)
                : receipt.ProcessedAt.Value.ToUniversalTime();
        }

        // Ensure all item dates are UTC
        foreach (var item in receipt.Items)
        {
            if (item.CreatedAt.Kind != DateTimeKind.Utc)
            {
                item.CreatedAt = item.CreatedAt.Kind == DateTimeKind.Unspecified
                    ? DateTime.SpecifyKind(item.CreatedAt, DateTimeKind.Utc)
                    : item.CreatedAt.ToUniversalTime();
            }

            if (item.UpdatedAt.HasValue && item.UpdatedAt.Value.Kind != DateTimeKind.Utc)
            {
                item.UpdatedAt = item.UpdatedAt.Value.Kind == DateTimeKind.Unspecified
                    ? DateTime.SpecifyKind(item.UpdatedAt.Value, DateTimeKind.Utc)
                    : item.UpdatedAt.Value.ToUniversalTime();
            }
        }
    }
}
