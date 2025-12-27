using Microsoft.AspNetCore.Mvc;
using AutoMapper;
using Receiptly.Core.Services;
using Receiptly.Core.Interfaces;
using Receiptly.Domain.Models;
using Receiptly.API.DTOs;
using Receiptly.Infrastructure.Services;
using System.Security.Claims;

namespace Receiptly.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ReceiptsController : ControllerBase
{
    private readonly IReceiptProcessingService _receiptProcessingService;
    private readonly IReceiptService _receiptService;
    private readonly FileValidationService _fileValidationService;
    private readonly IPointsService _pointsService;
    private readonly INotificationService _notificationService;
    private readonly IMapper _mapper;
    private readonly ILogger<ReceiptsController> _logger;

    public ReceiptsController(
        IReceiptProcessingService receiptProcessingService,
        IReceiptService receiptService,
        FileValidationService fileValidationService,
        IPointsService pointsService,
        INotificationService notificationService,
        IMapper mapper,
        ILogger<ReceiptsController> logger)
    {
        _receiptProcessingService = receiptProcessingService;
        _receiptService = receiptService;
        _fileValidationService = fileValidationService;
        _pointsService = pointsService;
        _notificationService = notificationService;
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

            // Get authenticated user ID from Clerk token or fall back to default
            var userId = GetAuthenticatedUserId();
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

            // Send push notification for receipt processed
            try
            {
                await _notificationService.SendReceiptProcessedNotificationAsync(
                    userId,
                    receipt.Id.ToString(),
                    receipt.StoreName,
                    receipt.TotalAmount,
                    cancellationToken);
            }
            catch (Exception notifEx)
            {
                _logger.LogWarning(notifEx, "Failed to send receipt processed notification");
                // Don't fail the request if notification fails
            }

            // Award points for receipt upload
            try
            {
                // Base points for receipt upload
                int pointsAwarded = 10;
                string pointsDescription = "Receipt uploaded";

                // Bonus for providing location data
                if (!string.IsNullOrEmpty(receipt.StoreAddress))
                {
                    pointsAwarded += 5;
                    pointsDescription += " + location bonus";
                }

                _logger.LogInformation("Attempting to award {Points} points to user {UserId}", pointsAwarded, userId);

                await _pointsService.AwardPointsAsync(
                    userId, 
                    pointsAwarded, 
                    "receipt_upload", 
                    pointsDescription,
                    receipt.Id,
                    cancellationToken);

                _logger.LogInformation("Successfully awarded {Points} points to user {UserId}", pointsAwarded, userId);

                // Check for new achievements (first_upload achievement will award 50 bonus points)
                var newAchievements = await _pointsService.CheckAndAwardAchievementsAsync(userId, cancellationToken);
                
                if (newAchievements.Any())
                {
                    _logger.LogInformation("User {UserId} unlocked {Count} achievements", userId, newAchievements.Count);
                }
            }
            catch (Exception ex)
            {
                // Log with full details
                _logger.LogError(ex, "POINTS ERROR - ReceiptId: {ReceiptId}, UserId: {UserId}, Message: {Message}, StackTrace: {StackTrace}", 
                    receipt.Id, userId, ex.Message, ex.StackTrace);
            }

            // Map to DTO
            var receiptDto = _mapper.Map<ReceiptDto>(receipt);
            return Ok(receiptDto);
        }
        catch (Receiptly.Domain.Exceptions.DuplicateReceiptException ex)
        {
            _logger.LogWarning("Duplicate receipt detected. ExistingReceiptId: {ExistingReceiptId}, ImageHash: {ImageHash}", 
                ex.ExistingReceiptId, ex.ImageHash);
            return Conflict(new 
            { 
                error = "Duplicate receipt",
                message = "A receipt with the same image has already been uploaded",
                existingReceiptId = ex.ExistingReceiptId,
                imageHash = ex.ImageHash
            });
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
    /// Get all receipts for the authenticated user
    /// </summary>
    [HttpGet]
    public async Task<ActionResult<List<ReceiptDto>>> GetUserReceipts(CancellationToken cancellationToken)
    {
        try
        {
            var userId = GetAuthenticatedUserId();
            _logger.LogInformation("Retrieving receipts for authenticated user: {UserId}", userId);
            var receipts = await _receiptService.GetReceiptsByUserIdAsync(userId, cancellationToken);
            _logger.LogInformation("Found {Count} receipts for user: {UserId}", receipts.Count, userId);
            
            // Map to DTOs
            var receiptDtos = _mapper.Map<List<ReceiptDto>>(receipts);
            return Ok(receiptDtos);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Request cancelled while retrieving receipts for authenticated user");
            return StatusCode(499, new { error = "Request cancelled" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving receipts for authenticated user");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    /// <summary>
    /// Get all receipts for a specific user (admin endpoint)
    /// </summary>
    [HttpGet("user/{userId}")]
    public async Task<ActionResult<List<ReceiptDto>>> GetUserReceiptsByUserId(string userId, CancellationToken cancellationToken)
    {
        try
        {
            _logger.LogInformation("Retrieving receipts for user: {UserId}", userId);
            var receipts = await _receiptService.GetReceiptsByUserIdAsync(userId, cancellationToken);
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
            var receipt = await _receiptService.GetReceiptByIdAsync(id, cancellationToken);
            
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
    /// Update a receipt
    /// </summary>
    [HttpPut("{id}")]
    public async Task<ActionResult<ReceiptDto>> UpdateReceipt(Guid id, [FromBody] ReceiptDto receiptDto, CancellationToken cancellationToken)
    {
        try
        {
            if (id != receiptDto.Id)
            {
                return BadRequest(new { error = "ID mismatch" });
            }

            _logger.LogInformation("Updating receipt: {ReceiptId}", id);
            
            // Verify existence and get the tracked entity
            var existingReceipt = await _receiptService.GetReceiptByIdAsync(id, cancellationToken);
            if (existingReceipt == null)
            {
                return NotFound(new { error = "Receipt not found" });
            }

            // Update the existing tracked entity with values from DTO
            // This prevents EF tracking conflicts
            existingReceipt.StoreName = receiptDto.StoreName;
            existingReceipt.StoreAddress = receiptDto.StoreAddress;
            existingReceipt.StorePhoneNumber = receiptDto.StorePhoneNumber;
            existingReceipt.TotalAmount = receiptDto.TotalAmount;
            existingReceipt.SubtotalAmount = receiptDto.SubtotalAmount;
            existingReceipt.TaxAmount = receiptDto.TaxAmount;
            existingReceipt.TipAmount = receiptDto.TipAmount;
            existingReceipt.TransactionId = receiptDto.TransactionId;
            existingReceipt.PurchaseDate = receiptDto.PurchaseDate;
            
            // Update items if provided
            if (receiptDto.Items != null)
            {
                existingReceipt.Items = _mapper.Map<List<Item>>(receiptDto.Items);
            }

            var result = await _receiptService.UpdateReceiptAsync(existingReceipt, cancellationToken);
            
            _logger.LogInformation("Receipt updated: {ReceiptId}", id);
            
            // Map back to DTO
            var resultDto = _mapper.Map<ReceiptDto>(result);
            return Ok(resultDto);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Request cancelled while updating receipt: {ReceiptId}", id);
            return StatusCode(499, new { error = "Request cancelled" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error updating receipt: {ReceiptId}", id);
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
            
            // Get receipt details before deletion to deduct points
            var receipt = await _receiptService.GetReceiptByIdAsync(id, cancellationToken);
            if (receipt == null)
            {
                return NotFound(new { error = "Receipt not found" });
            }
            
            var userId = GetAuthenticatedUserId();
            
            // Deduct points that were awarded for this receipt
            try
            {
                // Find the original point transaction for this receipt
                var transactions = await _pointsService.GetUserTransactionsAsync(userId, 1000, cancellationToken);
                var receiptTransaction = transactions.FirstOrDefault(t => t.ReferenceId == id && t.TransactionType == "receipt_upload");
                
                if (receiptTransaction != null && receiptTransaction.Points > 0)
                {
                    // Deduct the points that were awarded
                    var deducted = await _pointsService.DeductPointsAsync(
                        userId, 
                        receiptTransaction.Points, 
                        $"Receipt deleted: {receipt.StoreName}",
                        cancellationToken);
                    
                    if (deducted)
                    {
                        _logger.LogInformation("Deducted {Points} points from user {UserId} for deleted receipt", 
                            receiptTransaction.Points, userId);
                    }
                }
            }
            catch (Exception ex)
            {
                // Log but don't fail the deletion if point deduction fails
                _logger.LogError(ex, "Error deducting points for deleted receipt: {ReceiptId}", id);
            }
            
            await _receiptService.DeleteReceiptAsync(id, cancellationToken);
            
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

    /// <summary>
    /// Get the authenticated user ID from the current HTTP context
    /// </summary>
    private string GetAuthenticatedUserId()
    {
        // Log all claims for debugging
        var allClaims = User.Claims.Select(c => $"{c.Type}={c.Value}").ToList();
        _logger.LogInformation("All claims: {Claims}", string.Join(", ", allClaims));

        // Try to get from Clerk token first
        var clerkId = User.FindFirst("clerk_id")?.Value;
        _logger.LogInformation("clerk_id claim value: {ClerkId}", clerkId ?? "(not found)");
        if (!string.IsNullOrEmpty(clerkId))
            return clerkId;

        // Fall back to NameIdentifier claim
        var nameId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        _logger.LogInformation("NameIdentifier claim value: {NameId}", nameId ?? "(not found)");
        if (!string.IsNullOrEmpty(nameId))
            return nameId;

        // Fall back to default for development
        _logger.LogWarning("No authenticated user found, using default user ID");
        return "default-user";
    }
}