using Microsoft.AspNetCore.Mvc;
using AutoMapper;
using Receiptly.Core.Services;
using Receiptly.Core.Interfaces;
using Receiptly.Domain.Models;
using Receiptly.API.DTOs;
using Receiptly.Infrastructure.Services;

namespace Receiptly.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ReceiptsController : ControllerBase
{
    private readonly IReceiptProcessingService _receiptProcessingService;
    private readonly IReceiptRepository _receiptRepository;
    private readonly FileValidationService _fileValidationService;
    private readonly IMapper _mapper;
    private readonly ILogger<ReceiptsController> _logger;

    public ReceiptsController(
        IReceiptProcessingService receiptProcessingService,
        IReceiptRepository receiptRepository,
        FileValidationService fileValidationService,
        IMapper mapper,
        ILogger<ReceiptsController> logger)
    {
        _receiptProcessingService = receiptProcessingService;
        _receiptRepository = receiptRepository;
        _fileValidationService = fileValidationService;
        _mapper = mapper;
        _logger = logger;
    }

    /// <summary>
    /// Upload and process a receipt image
    /// Flow: Validate file → Upload to S3 → Python OCR → Validate receipt → Save raw data → Extract structured data → Save to S3 → Save to PostgreSQL
    /// </summary>
    [HttpPost("upload")]
    public async Task<ActionResult<ReceiptDto>> UploadReceipt(IFormFile file, CancellationToken cancellationToken)
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
                file.FileName,
                cancellationToken);

            _logger.LogInformation("Receipt processed successfully. ReceiptId: {ReceiptId}, StoreName: {StoreName}, Total: {Total}", 
                receipt.Id, receipt.StoreName, receipt.TotalAmount);

            // Map to DTO
            var receiptDto = _mapper.Map<ReceiptDto>(receipt);
            return Ok(receiptDto);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Receipt upload cancelled. FileName: {FileName}", file?.FileName);
            return StatusCode(499, new { error = "Request cancelled" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing receipt upload. FileName: {FileName}", file?.FileName);
            return StatusCode(500, new { error = ex.Message });
        }
    }

    /// <summary>
    /// Get all receipts for a user
    /// </summary>
    [HttpGet("user/{userId}")]
    public async Task<ActionResult<List<ReceiptDto>>> GetUserReceipts(string userId, CancellationToken cancellationToken)
    {
        try
        {
            _logger.LogInformation("Retrieving receipts for user: {UserId}", userId);
            var receipts = await _receiptRepository.GetByUserIdAsync(userId, cancellationToken);
            _logger.LogInformation("Found {Count} receipts for user: {UserId}", receipts.Count, userId);
            
            // Map to DTOs
            var receiptDtos = _mapper.Map<List<ReceiptDto>>(receipts);
            return Ok(receiptDtos);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Request cancelled while retrieving receipts for user: {UserId}", userId);
            return StatusCode(499, new { error = "Request cancelled" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving receipts for user: {UserId}", userId);
            return StatusCode(500, new { error = ex.Message });
        }
    }

    /// <summary>
    /// Get a specific receipt by ID
    /// </summary>
    [HttpGet("{id}")]
    public async Task<ActionResult<ReceiptDto>> GetReceipt(Guid id, CancellationToken cancellationToken)
    {
        try
        {
            _logger.LogInformation("Retrieving receipt: {ReceiptId}", id);
            var receipt = await _receiptRepository.GetByIdAsync(id, cancellationToken);
            
            if (receipt == null)
            {
                _logger.LogWarning("Receipt not found: {ReceiptId}", id);
                return NotFound(new { error = "Receipt not found" });
            }

            _logger.LogInformation("Receipt retrieved: {ReceiptId}", id);
            
            // Map to DTO
            var receiptDto = _mapper.Map<ReceiptDto>(receipt);
            return Ok(receiptDto);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Request cancelled while retrieving receipt: {ReceiptId}", id);
            return StatusCode(499, new { error = "Request cancelled" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving receipt: {ReceiptId}", id);
            return StatusCode(500, new { error = ex.Message });
        }
    }

    /// <summary>
    /// Delete a receipt
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<ActionResult> DeleteReceipt(Guid id, CancellationToken cancellationToken)
    {
        try
        {
            _logger.LogInformation("Deleting receipt: {ReceiptId}", id);
            var deleted = await _receiptRepository.DeleteAsync(id, cancellationToken);
            
            if (!deleted)
            {
                _logger.LogWarning("Receipt not found for deletion: {ReceiptId}", id);
                return NotFound(new { error = "Receipt not found" });
            }

            _logger.LogInformation("Receipt deleted: {ReceiptId}", id);
            return NoContent();
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Request cancelled while deleting receipt: {ReceiptId}", id);
            return StatusCode(499, new { error = "Request cancelled" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error deleting receipt: {ReceiptId}", id);
            return StatusCode(500, new { error = ex.Message });
        }
    }
}