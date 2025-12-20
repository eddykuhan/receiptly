using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Receiptly.API.DTOs;
using Receiptly.Core.Interfaces;
using Receiptly.Core.Models;
using System.Security.Claims;

namespace Receiptly.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class FeedbackController : ControllerBase
{
    private readonly IFeedbackService _feedbackService;
    private readonly ILogger<FeedbackController> _logger;
    
    public FeedbackController(
        IFeedbackService feedbackService,
        ILogger<FeedbackController> logger)
    {
        _feedbackService = feedbackService;
        _logger = logger;
    }
    
    /// <summary>
    /// Submit a correction to OCR results.
    /// </summary>
    [HttpPost("correction")]
    [ProducesResponseType(typeof(FeedbackResponseDto), 200)]
    [ProducesResponseType(400)]
    [ProducesResponseType(401)]
    [ProducesResponseType(500)]
    public async Task<ActionResult<FeedbackResponseDto>> SubmitCorrection(
        [FromBody] SubmitCorrectionDto dto,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var userId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value 
                ?? User.FindFirst("sub")?.Value
                ?? throw new UnauthorizedAccessException("User ID not found in claims");
            
            // Map DTO to request model
            var request = new SubmitCorrectionRequest
            {
                ReceiptId = dto.ReceiptId,
                FieldName = dto.FieldName,
                IncorrectValue = dto.IncorrectValue,
                CorrectedValue = dto.CorrectedValue
            };
            
            var correctionId = await _feedbackService.SubmitCorrectionAsync(
                userId,
                request,
                cancellationToken
            );
            
            _logger.LogInformation(
                "User {UserId} submitted correction {CorrectionId} for receipt {ReceiptId}",
                userId,
                correctionId,
                dto.ReceiptId
            );
            
            return Ok(new FeedbackResponseDto
            {
                Success = true,
                Message = "Thank you! Your correction helps improve our accuracy.",
                CorrectionId = correctionId
            });
        }
        catch (UnauthorizedAccessException ex)
        {
            _logger.LogWarning(ex, "Unauthorized correction submission attempt");
            return Unauthorized(new FeedbackResponseDto
            {
                Success = false,
                Message = "Authentication required"
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to submit correction for receipt {ReceiptId}", dto.ReceiptId);
            return StatusCode(500, new FeedbackResponseDto
            {
                Success = false,
                Message = "Failed to save correction. Please try again."
            });
        }
    }
    
    /// <summary>
    /// Report an issue with OCR processing.
    /// </summary>
    [HttpPost("issue")]
    [ProducesResponseType(typeof(FeedbackResponseDto), 200)]
    [ProducesResponseType(400)]
    [ProducesResponseType(401)]
    [ProducesResponseType(500)]
    public async Task<ActionResult<FeedbackResponseDto>> ReportIssue(
        [FromBody] ReportIssueDto dto,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var userId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value 
                ?? User.FindFirst("sub")?.Value
                ?? throw new UnauthorizedAccessException("User ID not found in claims");
            
            // Map DTO to request model
            var request = new ReportIssueRequest
            {
                ReceiptId = dto.ReceiptId,
                IssueType = dto.IssueType,
                Severity = dto.Severity,
                Description = dto.Description
            };
            
            var issueId = await _feedbackService.ReportIssueAsync(
                userId,
                request,
                cancellationToken
            );
            
            _logger.LogWarning(
                "User {UserId} reported {Severity} issue {IssueId} for receipt {ReceiptId}: {IssueType}",
                userId,
                dto.Severity,
                issueId,
                dto.ReceiptId,
                dto.IssueType
            );
            
            var message = dto.Severity == "high" || dto.Severity == "medium"
                ? "Issue reported. Debug mode enabled for your next uploads."
                : "Issue reported. Our team will investigate.";
            
            return Ok(new FeedbackResponseDto
            {
                Success = true,
                Message = message,
                CorrectionId = issueId
            });
        }
        catch (UnauthorizedAccessException ex)
        {
            _logger.LogWarning(ex, "Unauthorized issue report attempt");
            return Unauthorized(new FeedbackResponseDto
            {
                Success = false,
                Message = "Authentication required"
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to report issue for receipt {ReceiptId}", dto.ReceiptId);
            return StatusCode(500, new FeedbackResponseDto
            {
                Success = false,
                Message = "Failed to report issue. Please try again."
            });
        }
    }
    
    /// <summary>
    /// Get correction history for the current user.
    /// </summary>
    [HttpGet("corrections")]
    [ProducesResponseType(200)]
    [ProducesResponseType(401)]
    public async Task<ActionResult> GetMyCorrections(
        CancellationToken cancellationToken = default)
    {
        try
        {
            var userId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value 
                ?? User.FindFirst("sub")?.Value
                ?? throw new UnauthorizedAccessException();
            
            // TODO: Implement GetCorrectionsByUserIdAsync in service
            return Ok(new { message = "Feature coming soon" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to retrieve corrections");
            return StatusCode(500);
        }
    }
}
