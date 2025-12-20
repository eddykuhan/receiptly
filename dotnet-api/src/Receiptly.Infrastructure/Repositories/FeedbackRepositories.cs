using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Dapper;
using Receiptly.Core.Interfaces;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Data;

namespace Receiptly.Infrastructure.Repositories;

/// <summary>
/// Repository for user corrections using Dapper for lightweight data access.
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
        const string sql = @"
            INSERT INTO user_corrections (id, receipt_id, user_id, field_name, incorrect_value, corrected_value, created_at)
            VALUES (@Id, @ReceiptId, @UserId, @FieldName, @IncorrectValue, @CorrectedValue, @CreatedAt)";

        var connection = _context.Database.GetDbConnection();
        await connection.ExecuteAsync(sql, correction);
        
        return correction.Id;
    }

    public async Task<UserCorrection?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        const string sql = "SELECT * FROM user_corrections WHERE id = @Id";
        
        var connection = _context.Database.GetDbConnection();
        return await connection.QueryFirstOrDefaultAsync<UserCorrection>(sql, new { Id = id });
    }

    public async Task<List<UserCorrection>> GetByReceiptIdAsync(Guid receiptId, CancellationToken cancellationToken = default)
    {
        const string sql = "SELECT * FROM user_corrections WHERE receipt_id = @ReceiptId ORDER BY created_at DESC";
        
        var connection = _context.Database.GetDbConnection();
        var result = await connection.QueryAsync<UserCorrection>(sql, new { ReceiptId = receiptId });
        return result.ToList();
    }

    public async Task<List<UserCorrection>> GetByUserIdAsync(string userId, CancellationToken cancellationToken = default)
    {
        const string sql = "SELECT * FROM user_corrections WHERE user_id = @UserId ORDER BY created_at DESC LIMIT 100";
        
        var connection = _context.Database.GetDbConnection();
        var result = await connection.QueryAsync<UserCorrection>(sql, new { UserId = userId });
        return result.ToList();
    }
}

/// <summary>
/// Repository for issue reports using Dapper.
/// </summary>
public class IssueReportRepository : IIssueReportRepository
{
    private readonly ApplicationDbContext _context;

    public IssueReportRepository(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task<Guid> CreateAsync(IssueReport issue, CancellationToken cancellationToken = default)
    {
        const string sql = @"
            INSERT INTO issue_reports (id, receipt_id, user_id, issue_type, description, severity, created_at)
            VALUES (@Id, @ReceiptId, @UserId, @IssueType, @Description, @Severity, @CreatedAt)";

        var connection = _context.Database.GetDbConnection();
        await connection.ExecuteAsync(sql, issue);
        
        return issue.Id;
    }

    public async Task<IssueReport?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        const string sql = "SELECT * FROM issue_reports WHERE id = @Id";
        
        var connection = _context.Database.GetDbConnection();
        return await connection.QueryFirstOrDefaultAsync<IssueReport>(sql, new { Id = id });
    }

    public async Task<List<IssueReport>> GetByReceiptIdAsync(Guid receiptId, CancellationToken cancellationToken = default)
    {
        const string sql = "SELECT * FROM issue_reports WHERE receipt_id = @ReceiptId ORDER BY created_at DESC";
        
        var connection = _context.Database.GetDbConnection();
        var result = await connection.QueryAsync<IssueReport>(sql, new { ReceiptId = receiptId });
        return result.ToList();
    }

    public async Task<List<IssueReport>> GetByUserIdAsync(string userId, CancellationToken cancellationToken = default)
    {
        const string sql = "SELECT * FROM issue_reports WHERE user_id = @UserId ORDER BY created_at DESC LIMIT 100";
        
        var connection = _context.Database.GetDbConnection();
        var result = await connection.QueryAsync<IssueReport>(sql, new { UserId = userId });
        return result.ToList();
    }
}

/// <summary>
/// Repository for user debug sessions using Dapper.
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
        const string sql = @"
            INSERT INTO user_debug_sessions (id, user_id, session_id, started_at, expires_at, reason)
            VALUES (@Id, @UserId, @SessionId, @StartedAt, @ExpiresAt, @Reason)
            ON CONFLICT (user_id, session_id)
            DO UPDATE SET expires_at = EXCLUDED.expires_at, reason = EXCLUDED.reason";

        var connection = _context.Database.GetDbConnection();
        await connection.ExecuteAsync(sql, session);
    }

    public async Task<UserDebugSession?> GetByUserIdAsync(string userId, CancellationToken cancellationToken = default)
    {
        const string sql = @"
            SELECT * FROM user_debug_sessions 
            WHERE user_id = @UserId AND expires_at > @Now
            ORDER BY started_at DESC 
            LIMIT 1";

        var connection = _context.Database.GetDbConnection();
        return await connection.QueryFirstOrDefaultAsync<UserDebugSession>(sql, new 
        { 
            UserId = userId, 
            Now = DateTime.UtcNow 
        });
    }
}
