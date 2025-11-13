using Microsoft.AspNetCore.Mvc;
using Receiptly.Core.Services;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Services;

namespace Receiptly.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ReceiptsController : ControllerBase
{
    private readonly IReceiptProcessingService _receiptProcessingService;
    private readonly FileValidationService _fileValidationService;
    private readonly ILogger<ReceiptsController> _logger;

    public ReceiptsController(
        IReceiptProcessingService receiptProcessingService,
        FileValidationService fileValidationService,
        ILogger<ReceiptsController> logger)
    {
        _receiptProcessingService = receiptProcessingService;
        _fileValidationService = fileValidationService;
        _logger = logger;
    }

    /// <summary>
    /// Upload and process a receipt image
    /// Flow: Validate file → Upload to S3 → Python OCR → Validate receipt → Save raw data → Extract structured data → Save to S3
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

            // Comprehensive file validation
            _logger.LogInformation("Validating file format and content");
            var validationResult = await _fileValidationService.ValidateReceiptFileAsync(file);
            
            if (!validationResult.IsValid)
            {
                _logger.LogWarning("File validation failed: {ErrorMessage}", validationResult.ErrorMessage);
                return BadRequest(new 
                { 
                    error = "File validation failed",
                    message = validationResult.ErrorMessage,
                    detectedType = validationResult.DetectedFileType
                });
            }

            _logger.LogInformation("File validation passed. Type: {FileType}, Size: {Size} bytes", 
                validationResult.DetectedFileType, validationResult.FileSize);

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