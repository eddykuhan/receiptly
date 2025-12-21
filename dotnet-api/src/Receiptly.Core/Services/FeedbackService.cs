using System;
using System.Threading;
using System.Threading.Tasks;
using Receiptly.Core.Interfaces;
using Receiptly.Core.Models;
using Receiptly.Domain.Models;

namespace Receiptly.Core.Services;

/// <summary>
/// Service for handling user feedback (corrections and issue reports).
/// </summary>
public class FeedbackService : IFeedbackService
{
    private readonly IUserCorrectionRepository _correctionRepo;
    private readonly IIssueReportRepository _issueRepo;
    private readonly IUserDebugSessionRepository _debugSessionRepo;
    
    public FeedbackService(
        IUserCorrectionRepository correctionRepo,
        IIssueReportRepository issueRepo,
        IUserDebugSessionRepository debugSessionRepo)
    {
        _correctionRepo = correctionRepo;
        _issueRepo = issueRepo;
        _debugSessionRepo = debugSessionRepo;
    }
    
    public async Task<Guid> SubmitCorrectionAsync(
        string userId,
        SubmitCorrectionRequest request,
        CancellationToken cancellationToken = default)
    {
        // Check if correction already exists for this receipt and field
        var existingCorrection = await _correctionRepo.GetByReceiptAndFieldAsync(
            request.ReceiptId, 
            request.FieldName, 
            cancellationToken);

        if (existingCorrection != null)
        {
            // Update existing correction
            existingCorrection.IncorrectValue = request.IncorrectValue;
            existingCorrection.CorrectedValue = request.CorrectedValue;
            existingCorrection.Latitude = request.Latitude;
            existingCorrection.Longitude = request.Longitude;
            existingCorrection.CreatedAt = DateTime.UtcNow;  // Update timestamp
            
            await _correctionRepo.UpdateAsync(existingCorrection, cancellationToken);
            return existingCorrection.Id;
        }
        
        // Create new correction
        var correction = new UserCorrection
        {
            Id = Guid.NewGuid(),
            ReceiptId = request.ReceiptId,
            UserId = userId,
            FieldName = request.FieldName,
            IncorrectValue = request.IncorrectValue,
            CorrectedValue = request.CorrectedValue,
            Latitude = request.Latitude,
            Longitude = request.Longitude,
            CreatedAt = DateTime.UtcNow
        };
        
        var correctionId = await _correctionRepo.CreateAsync(correction, cancellationToken);
        
        return correctionId;
    }
    
    public async Task<Guid> ReportIssueAsync(
        string userId,
        ReportIssueRequest request,
        CancellationToken cancellationToken = default)
    {
        var issue = new IssueReport
        {
            Id = Guid.NewGuid(),
            ReceiptId = request.ReceiptId,
            UserId = userId,
            IssueType = request.IssueType,
            Description = request.Description,
            Severity = request.Severity,
            CreatedAt = DateTime.UtcNow
        };
        
        var issueId = await _issueRepo.CreateAsync(issue, cancellationToken);
        
        // Enable debug mode for medium/high severity issues
        if (request.Severity.Equals("Medium", StringComparison.OrdinalIgnoreCase) || 
            request.Severity.Equals("High", StringComparison.OrdinalIgnoreCase) ||
            request.Severity.Equals("Critical", StringComparison.OrdinalIgnoreCase))
        {
            await EnableDebugModeAsync(
                userId,
                requestCount: 5,
                reason: $"Issue reported: {request.IssueType}",
                cancellationToken
            );
        }
        
        return issueId;
    }
    
    public async Task EnableDebugModeAsync(
        string userId,
        int requestCount = 5,
        string? reason = null,
        CancellationToken cancellationToken = default)
    {
        var sessionId = Guid.NewGuid().ToString();
        var session = new UserDebugSession
        {
            Id = Guid.NewGuid(),
            UserId = userId,
            SessionId = sessionId,
            StartedAt = DateTime.UtcNow,
            ExpiresAt = DateTime.UtcNow.AddHours(24),  // 24 hour expiry
            Reason = reason
        };
        
        await _debugSessionRepo.CreateOrUpdateAsync(session, cancellationToken);
    }
    
    public async Task<bool> IsDebugModeEnabledAsync(
        string userId,
        CancellationToken cancellationToken = default)
    {
        var session = await _debugSessionRepo.GetByUserIdAsync(userId, cancellationToken);
        
        if (session == null)
            return false;
        
        // Check if expired
        if (session.ExpiresAt < DateTime.UtcNow)
            return false;
        
        return true;
    }
}
