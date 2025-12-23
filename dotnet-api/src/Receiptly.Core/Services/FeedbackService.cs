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
    private readonly IReceiptRepository _receiptRepo;
    
    public FeedbackService(
        IUserCorrectionRepository correctionRepo,
        IIssueReportRepository issueRepo,
        IUserDebugSessionRepository debugSessionRepo,
        IReceiptRepository receiptRepo)
    {
        _correctionRepo = correctionRepo;
        _issueRepo = issueRepo;
        _debugSessionRepo = debugSessionRepo;
        _receiptRepo = receiptRepo;
    }
    
    public async Task<Guid> SubmitCorrectionAsync(
        string userId,
        SubmitCorrectionRequest request,
        CancellationToken cancellationToken = default)
    {
        // Get the receipt to update
        var receipt = await _receiptRepo.GetByIdAsync(request.ReceiptId, cancellationToken);
        if (receipt == null)
        {
            throw new InvalidOperationException($"Receipt {request.ReceiptId} not found");
        }

        // Update the receipt based on the field being corrected
        await ApplyCorrectionToReceipt(receipt, request, cancellationToken);

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

    private async Task ApplyCorrectionToReceipt(
        Receipt receipt,
        SubmitCorrectionRequest request,
        CancellationToken cancellationToken)
    {
        var fieldName = request.FieldName;
        var correctedValue = request.CorrectedValue;

        switch (fieldName)
        {
            case "StoreName":
                receipt.StoreName = correctedValue;
                break;

            case "TotalAmount":
                if (decimal.TryParse(correctedValue, out var totalAmount))
                {
                    receipt.TotalAmount = totalAmount;
                }
                break;

            case "PurchaseDate":
                if (DateTime.TryParse(correctedValue, out var purchaseDate))
                {
                    receipt.PurchaseDate = purchaseDate;
                }
                break;

            case "StoreAddress":
                receipt.StoreAddress = correctedValue;
                if (request.Latitude.HasValue)
                    receipt.Latitude = request.Latitude;
                if (request.Longitude.HasValue)
                    receipt.Longitude = request.Longitude;
                break;

            default:
                // Handle item corrections: "Items[0].Name" or "Items[0].Price"
                if (fieldName.StartsWith("Items["))
                {
                    var match = System.Text.RegularExpressions.Regex.Match(
                        fieldName, 
                        @"Items\[(\d+)\]\.(Name|Price)");
                    
                    if (match.Success)
                    {
                        var index = int.Parse(match.Groups[1].Value);
                        var field = match.Groups[2].Value;

                        if (index >= 0 && index < receipt.Items.Count)
                        {
                            if (field == "Name")
                            {
                                receipt.Items[index].Name = correctedValue;
                            }
                            else if (field == "Price" && decimal.TryParse(correctedValue, out var price))
                            {
                                receipt.Items[index].Price = price;
                            }
                        }
                    }
                }
                break;
        }

        // Update the receipt in the database
        receipt.UpdatedAt = DateTime.UtcNow;
        await _receiptRepo.UpdateAsync(receipt, cancellationToken);
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
