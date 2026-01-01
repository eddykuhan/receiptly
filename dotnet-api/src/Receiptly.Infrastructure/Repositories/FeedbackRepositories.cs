using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Receiptly.Core.Interfaces;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Data;

namespace Receiptly.Infrastructure.Repositories;

/// <summary>
/// Repository for user corrections using Entity Framework Core.
/// </summary>
public class UserCorrectionRepository : IUserCorrectionRepository
{
    private readonly ApplicationDbContext _context;

    public UserCorrectionRepository(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task<Guid> CreateAsync(UserCorrection correction, CancellationToken cancellationToken = default)
    {
        await _context.UserCorrections.AddAsync(correction, cancellationToken);
        await _context.SaveChangesAsync(cancellationToken);
        
        return correction.Id;
    }

    public async Task<UserCorrection?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return await _context.UserCorrections
            .AsNoTracking()
            .FirstOrDefaultAsync(c => c.Id == id, cancellationToken);
    }

    public async Task<List<UserCorrection>> GetByReceiptIdAsync(Guid receiptId, CancellationToken cancellationToken = default)
    {
        return await _context.UserCorrections
            .AsNoTracking()
            .Where(c => c.ReceiptId == receiptId)
            .OrderByDescending(c => c.CreatedAt)
            .ToListAsync(cancellationToken);
    }

    public async Task<List<UserCorrection>> GetByUserIdAsync(string userId, CancellationToken cancellationToken = default)
    {
        return await _context.UserCorrections
            .AsNoTracking()
            .Where(c => c.UserId == userId)
            .OrderByDescending(c => c.CreatedAt)
            .Take(100)
            .ToListAsync(cancellationToken);
    }

    public async Task<UserCorrection?> GetByReceiptAndFieldAsync(Guid receiptId, string fieldName, CancellationToken cancellationToken = default)
    {
        return await _context.UserCorrections
            .FirstOrDefaultAsync(c => c.ReceiptId == receiptId && c.FieldName == fieldName, cancellationToken);
    }

    public async Task UpdateAsync(UserCorrection correction, CancellationToken cancellationToken = default)
    {
        _context.UserCorrections.Update(correction);
        await _context.SaveChangesAsync(cancellationToken);
    }
}

/// <summary>
/// Repository for user debug sessions using Entity Framework Core.
/// </summary>
public class UserDebugSessionRepository : IUserDebugSessionRepository
{
    private readonly ApplicationDbContext _context;

    public UserDebugSessionRepository(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task CreateOrUpdateAsync(UserDebugSession session, CancellationToken cancellationToken = default)
    {
        var existing = await _context.UserDebugSessions
            .FirstOrDefaultAsync(s => s.UserId == session.UserId && s.SessionId == session.SessionId, cancellationToken);

        if (existing != null)
        {
            existing.ExpiresAt = session.ExpiresAt;
            existing.Reason = session.Reason;
            _context.UserDebugSessions.Update(existing);
        }
        else
        {
            await _context.UserDebugSessions.AddAsync(session, cancellationToken);
        }

        await _context.SaveChangesAsync(cancellationToken);
    }

    public async Task<UserDebugSession?> GetByUserIdAsync(string userId, CancellationToken cancellationToken = default)
    {
        var now = DateTime.UtcNow;
        
        return await _context.UserDebugSessions
            .AsNoTracking()
            .Where(s => s.UserId == userId && s.ExpiresAt > now)
            .OrderByDescending(s => s.StartedAt)
            .FirstOrDefaultAsync(cancellationToken);
    }
}