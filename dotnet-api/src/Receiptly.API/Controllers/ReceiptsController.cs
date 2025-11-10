using Microsoft.AspNetCore.Mvc;
using Receiptly.Core.Services;
using Receiptly.Domain.Models;

namespace Receiptly.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ReceiptsController : ControllerBase
{
    private readonly IReceiptProcessingService _receiptProcessingService;
    private readonly ILogger<ReceiptsController> _logger;

    public ReceiptsController(
        IReceiptProcessingService receiptProcessingService,
        ILogger<ReceiptsController> logger)
    {
        _receiptProcessingService = receiptProcessingService;
        _logger = logger;
    }

    /// <summary>
    /// Upload and process a receipt image
    /// Flow: Upload to S3 → Python OCR → Save raw data → Extract structured data → Save to DB
    /// </summary>
    [HttpPost("upload")]
    public async Task<ActionResult<Receipt>> UploadReceipt(IFormFile file)
    {
        try
        {
            _logger.LogInformation("Receipt upload started. Filename: {FileName}, ContentType: {ContentType}, Size: {Size} bytes", 
                file?.FileName, file?.ContentType, file?.Length);

            // Validate file
            if (file == null || file.Length == 0)
            {
                _logger.LogWarning("Upload failed: No file provided");
                return BadRequest("No file uploaded");
            }

            var allowedTypes = new[] { "image/jpeg", "image/png", "image/tiff", "application/pdf" };
            if (!allowedTypes.Contains(file.ContentType))
            {
                _logger.LogWarning("Upload failed: Invalid file type {ContentType}", file.ContentType);
                return BadRequest($"File type not supported. Allowed types: {string.Join(", ", allowedTypes)}");
            }

            if (file.Length > 4 * 1024 * 1024) // 4MB limit
            {
                _logger.LogWarning("Upload failed: File too large ({Size} bytes)", file.Length);
                return BadRequest("File size too large. Maximum size is 4MB.");
            }

            // Use a default user ID for now (since authentication is removed)
            var userId = "default-user";
            _logger.LogInformation("Processing receipt for user: {UserId}", userId);

            // Process receipt through the orchestration service
            using var stream = file.OpenReadStream();
            _logger.LogInformation("Starting receipt processing workflow");
            
            var receipt = await _receiptProcessingService.ProcessReceiptAsync(
                userId,
                stream,
                file.ContentType,
                file.FileName);

            _logger.LogInformation("Receipt processed successfully. ReceiptId: {ReceiptId}, StoreName: {StoreName}, Total: {Total}", 
                receipt.Id, receipt.StoreName, receipt.TotalAmount);

            // Return the processed receipt directly (no database save)
            return Ok(receipt);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing receipt upload. FileName: {FileName}", file?.FileName);
            return StatusCode(500, new { error = ex.Message });
        }
    }
}