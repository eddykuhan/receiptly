using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Receiptly.Domain.Models;

namespace Receiptly.Core.Interfaces;

/// <summary>
/// Repository for user corrections.
/// </summary>
public interface IUserCorrectionRepository
{
    Task<Guid> CreateAsync(UserCorrection correction, CancellationToken cancellationToken = default);
    Task<UserCorrection?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<List<UserCorrection>> GetByUserIdAsync(string userId, CancellationToken cancellationToken = default);
    Task<List<UserCorrection>> GetByReceiptIdAsync(Guid receiptId, CancellationToken cancellationToken = default);
    Task<UserCorrection?> GetByReceiptAndFieldAsync(Guid receiptId, string fieldName, CancellationToken cancellationToken = default);
    Task UpdateAsync(UserCorrection correction, CancellationToken cancellationToken = default);
}

/// <summary>
/// Repository for user debug sessions.
/// </summary>
public interface IUserDebugSessionRepository
{
    Task CreateOrUpdateAsync(UserDebugSession session, CancellationToken cancellationToken = default);
    Task<UserDebugSession?> GetByUserIdAsync(string userId, CancellationToken cancellationToken = default);
}
