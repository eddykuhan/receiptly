using System;
using System.Threading;
using System.Threading.Tasks;
using Receiptly.Core.Models;

namespace Receiptly.Core.Interfaces;

/// <summary>
/// Service for handling user feedback (corrections and issue reports).
/// </summary>
public interface IFeedbackService
{
    /// <summary>
    /// Submit a user correction to OCR results.
    /// </summary>
    Task<Guid> SubmitCorrectionAsync(
        string userId,
        SubmitCorrectionRequest request,
        CancellationToken cancellationToken = default);
    
    /// <summary>
    /// Report an issue with OCR processing.
    /// </summary>
    Task<Guid> ReportIssueAsync(
        string userId,
        ReportIssueRequest request,
        CancellationToken cancellationToken = default);
    
    /// <summary>
    /// Enable debug mode for a specific user.
    /// </summary>
    Task EnableDebugModeAsync(
        string userId,
        int requestCount = 5,
        string? reason = null,
        CancellationToken cancellationToken = default);
    
    /// <summary>
    /// Check if debug mode is enabled for a user.
    /// </summary>
    Task<bool> IsDebugModeEnabledAsync(
        string userId,
        CancellationToken cancellationToken = default);
}
