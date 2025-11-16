using Receiptly.Core.Services;
using Receiptly.Core.Interfaces;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Services;
using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace Receiptly.Infrastructure.Services;

public class ReceiptProcessingService : IReceiptProcessingService
{
    private readonly S3StorageService _s3Storage;
    private readonly PythonOcrClient _ocrClient;
    private readonly IReceiptRepository _receiptRepository;
    private readonly IImageHashService _imageHashService;
    private readonly ILogger<ReceiptProcessingService> _logger;

    public ReceiptProcessingService(
        S3StorageService s3Storage, 
        PythonOcrClient ocrClient,
        IReceiptRepository receiptRepository,
        IImageHashService imageHashService,
        ILogger<ReceiptProcessingService> logger)
    {
        _s3Storage = s3Storage;
        _ocrClient = ocrClient;
        _receiptRepository = receiptRepository;
        _imageHashService = imageHashService;
        _logger = logger;
    }

    /// <summary>
    /// Complete receipt processing workflow:
    /// 1. Compute image hash for duplicate detection
    /// 2. Check for existing receipt with same hash
    /// 3. Upload image to S3
    /// 4. Call Python OCR with presigned URL
    /// 5. Validate receipt confidence
    /// 6. Save raw response to S3
    /// 7. Extract structured data
    /// 8. Save extracted data to S3
    /// 9. Save receipt to PostgreSQL database with hash
    /// 10. Return Receipt entity with validation status
    /// </summary>
    public async Task<Receipt> ProcessReceiptAsync(
        string userId,
        Stream imageStream,
        string contentType,
        string filename,
        CancellationToken cancellationToken = default)
    {
        var receiptId = Guid.NewGuid();
        string? s3Key = null;
        string? imageUrl = null;
        
        _logger.LogInformation("Starting receipt processing. ReceiptId: {ReceiptId}, UserId: {UserId}, Filename: {Filename}", 
            receiptId, userId, filename);

        try
        {
            // Step 1: Compute image hash for duplicate detection
            _logger.LogInformation("Step 1/9: Computing image hash. ReceiptId: {ReceiptId}", receiptId);
            var imageHash = await _imageHashService.ComputeHashAsync(imageStream, cancellationToken);
            _logger.LogInformation("Image hash computed: {ImageHash}, ReceiptId: {ReceiptId}", imageHash, receiptId);
            
            // Step 2: Check for duplicate receipt
            _logger.LogInformation("Step 2/9: Checking for duplicate receipt. ReceiptId: {ReceiptId}", receiptId);
            var existingReceipt = await _receiptRepository.GetByImageHashAsync(userId, imageHash, cancellationToken);
            if (existingReceipt != null)
            {
                _logger.LogWarning("Duplicate receipt detected. ExistingReceiptId: {ExistingReceiptId}, ImageHash: {ImageHash}", 
                    existingReceipt.Id, imageHash);
                throw new Receiptly.Domain.Exceptions.DuplicateReceiptException(existingReceipt.Id, imageHash);
            }
            _logger.LogInformation("No duplicate found. Proceeding with processing. ReceiptId: {ReceiptId}", receiptId);

            // Check cancellation
            cancellationToken.ThrowIfCancellationRequested();

            // Step 3: Upload image to S3 and get presigned URL
            _logger.LogInformation("Step 3/9: Uploading image to S3. ReceiptId: {ReceiptId}", receiptId);
            imageUrl = await _s3Storage.UploadReceiptImageAsync(
                userId,
                receiptId,
                imageStream,
                contentType,
                filename);
            
            // Extract S3 key from URL for later use
            var uri = new Uri(imageUrl);
            s3Key = uri.LocalPath.TrimStart('/');
            
            _logger.LogInformation("Image uploaded to S3. PresignedUrl generated. ReceiptId: {ReceiptId}, S3Key: {S3Key}", 
                receiptId, s3Key);

            // Check cancellation
            cancellationToken.ThrowIfCancellationRequested();

            // Step 4: Call Python OCR service with the image URL
            _logger.LogInformation("Step 4/9: Calling Python OCR service. ReceiptId: {ReceiptId}", receiptId);
            OcrApiResponse ocrResult;
            
            try
            {
                ocrResult = await _ocrClient.AnalyzeReceiptAsync(imageUrl);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "OCR service failed. ReceiptId: {ReceiptId}", receiptId);
                throw new Receiptly.Domain.Exceptions.OcrProcessingException(
                    receiptId, 
                    "OCR service failed to process the receipt. The image may be unclear or not a valid receipt.", 
                    ex,
                    ex.Message);
            }
            
            _logger.LogInformation("OCR analysis completed. DocType: {DocType}, Confidence: {Confidence}, ReceiptId: {ReceiptId}", 
                ocrResult.Data.DocType, ocrResult.Data.Confidence, receiptId);

            // Check cancellation
            cancellationToken.ThrowIfCancellationRequested();

            // Step 5: Validate receipt
            _logger.LogInformation("Step 5/9: Validating receipt. ReceiptId: {ReceiptId}", receiptId);
            var validation = ocrResult.Validation;
            if (validation != null)
            {
                _logger.LogInformation("Validation: IsValid={IsValid}, Confidence={Confidence}, Message={Message}, ReceiptId: {ReceiptId}",
                    validation.IsValidReceipt, validation.Confidence, validation.Message, receiptId);
                
                // Check if receipt validation failed
                if (!validation.IsValidReceipt)
                {
                    var errorMessage = validation.Message ?? "Receipt validation failed";
                    _logger.LogWarning("Receipt is not valid. ReceiptId: {ReceiptId}, Reason: {Reason}", 
                        receiptId, errorMessage);
                    
                    throw new Receiptly.Domain.Exceptions.InvalidReceiptException(
                        receiptId,
                        validation.Confidence,
                        errorMessage);
                }
                
                // Check if confidence is too low (below 0.5)
                if (validation.Confidence < 0.5f)
                {
                    _logger.LogWarning("Receipt confidence too low. ReceiptId: {ReceiptId}, Confidence: {Confidence}", 
                        receiptId, validation.Confidence);
                    
                    throw new Receiptly.Domain.Exceptions.PoorImageQualityException(
                        receiptId,
                        $"Image quality is too poor for reliable OCR processing (confidence: {validation.Confidence:P0})");
                }
            }

            // Step 6: Save raw OCR response to S3
            _logger.LogInformation("Step 6/9: Saving raw OCR response to S3. ReceiptId: {ReceiptId}", receiptId);
            await _s3Storage.SaveRawResponseAsync(userId, receiptId, ocrResult.Data);

            // Check cancellation
            cancellationToken.ThrowIfCancellationRequested();

            // Step 7: Extract structured data from OCR response
            _logger.LogInformation("Step 7/9: Extracting structured data. ReceiptId: {ReceiptId}", receiptId);
            var receipt = ExtractReceiptData(receiptId, userId, imageUrl, filename, ocrResult.Data, validation);
            
            // Add image hash to receipt
            receipt.ImageHash = imageHash;
            
            _logger.LogInformation("Data extracted. MerchantName: {MerchantName}, Items: {ItemCount}, Total: {Total}, Status: {Status}, ReceiptId: {ReceiptId}", 
                receipt.StoreName, receipt.Items.Count, receipt.TotalAmount, receipt.Status, receiptId);

            // Step 8: Save extracted data to S3
            _logger.LogInformation("Step 8/9: Saving extracted data to S3. ReceiptId: {ReceiptId}", receiptId);
            await _s3Storage.SaveExtractedDataAsync(userId, receiptId, receipt);

            // Check cancellation
            cancellationToken.ThrowIfCancellationRequested();

            // Step 9: Save receipt to PostgreSQL database
            _logger.LogInformation("Step 9/9: Saving receipt to database. ReceiptId: {ReceiptId}", receiptId);
            receipt.ProcessedAt = DateTime.UtcNow;
            await _receiptRepository.CreateAsync(receipt, cancellationToken);
            _logger.LogInformation("Receipt saved to database. ReceiptId: {ReceiptId}", receiptId);

            _logger.LogInformation("Receipt processing completed successfully. ReceiptId: {ReceiptId}", receiptId);
            return receipt;
        }
        catch (Receiptly.Domain.Exceptions.InvalidReceiptException ex)
        {
            _logger.LogWarning(ex, "Invalid receipt detected. ReceiptId: {ReceiptId}, Confidence: {Confidence}", 
                ex.ReceiptId, ex.Confidence);
            
            // Move to failed folder if S3 upload was successful
            if (!string.IsNullOrEmpty(s3Key))
            {
                await _s3Storage.MoveToFailedFolderAsync(userId, receiptId, s3Key, $"Invalid receipt: {ex.Message}");
                await _s3Storage.SaveFailureDetailsAsync(userId, receiptId, $"Invalid receipt: {ex.Message}", null, ex);
            }
            
            throw new Exception($"The uploaded image is not a valid receipt. {ex.Message}");
        }
        catch (Receiptly.Domain.Exceptions.PoorImageQualityException ex)
        {
            _logger.LogWarning(ex, "Poor image quality. ReceiptId: {ReceiptId}", ex.ReceiptId);
            
            // Move to failed folder if S3 upload was successful
            if (!string.IsNullOrEmpty(s3Key))
            {
                await _s3Storage.MoveToFailedFolderAsync(userId, receiptId, s3Key, $"Poor quality: {ex.Message}");
                await _s3Storage.SaveFailureDetailsAsync(userId, receiptId, $"Poor quality: {ex.Message}", null, ex);
            }
            
            throw new Exception($"Image quality is too poor to read the receipt. Please take a clearer photo with good lighting.");
        }
        catch (Receiptly.Domain.Exceptions.OcrProcessingException ex)
        {
            _logger.LogError(ex, "OCR processing failed. ReceiptId: {ReceiptId}", ex.ReceiptId);
            
            // Move to failed folder if S3 upload was successful
            if (!string.IsNullOrEmpty(s3Key))
            {
                await _s3Storage.MoveToFailedFolderAsync(userId, receiptId, s3Key, $"OCR failed: {ex.Message}");
                await _s3Storage.SaveFailureDetailsAsync(userId, receiptId, $"OCR failed: {ex.Message}", ex.OcrResponse, ex);
            }
            
            throw new Exception($"Failed to process receipt. The image may not contain a valid receipt or is too unclear to read.");
        }
        catch (Receiptly.Domain.Exceptions.MissingRequiredFieldsException ex)
        {
            _logger.LogWarning(ex, "Missing required fields. ReceiptId: {ReceiptId}, Fields: {Fields}", 
                ex.ReceiptId, string.Join(", ", ex.MissingFields));
            
            // Move to failed folder if S3 upload was successful
            if (!string.IsNullOrEmpty(s3Key))
            {
                await _s3Storage.MoveToFailedFolderAsync(userId, receiptId, s3Key, $"Missing fields: {ex.Message}");
                await _s3Storage.SaveFailureDetailsAsync(userId, receiptId, $"Missing fields: {ex.Message}", null, ex);
            }
            
            throw new Exception($"Receipt is missing required information: {string.Join(", ", ex.MissingFields)}. Please upload a complete receipt.");
        }
        catch (Receiptly.Domain.Exceptions.DuplicateReceiptException)
        {
            // Don't move to failed folder for duplicates, just re-throw
            throw;
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Receipt processing cancelled. ReceiptId: {ReceiptId}", receiptId);
            
            // Clean up S3 file if upload was successful
            if (!string.IsNullOrEmpty(s3Key))
            {
                try
                {
                    await _s3Storage.DeleteReceiptAsync(userId, receiptId);
                }
                catch (Exception cleanupEx)
                {
                    _logger.LogError(cleanupEx, "Failed to cleanup S3 after cancellation. ReceiptId: {ReceiptId}", receiptId);
                }
            }
            
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unexpected error processing receipt. ReceiptId: {ReceiptId}, UserId: {UserId}", receiptId, userId);
            
            // Move to failed folder for unexpected errors if S3 upload was successful
            if (!string.IsNullOrEmpty(s3Key))
            {
                try
                {
                    await _s3Storage.MoveToFailedFolderAsync(userId, receiptId, s3Key, $"Unexpected error: {ex.Message}");
                    await _s3Storage.SaveFailureDetailsAsync(userId, receiptId, $"Unexpected error: {ex.Message}", null, ex);
                }
                catch (Exception moveEx)
                {
                    _logger.LogError(moveEx, "Failed to move receipt to failed folder. ReceiptId: {ReceiptId}", receiptId);
                }
            }
            
            throw new Exception($"An unexpected error occurred while processing your receipt. Please try again or contact support if the problem persists.");
        }
    }

    /// <summary>
    /// Extract structured receipt data from Azure Document Intelligence response
    /// </summary>
    private Receipt ExtractReceiptData(Guid receiptId, string userId, string imageUrl, string filename, OcrResponse ocrResponse, OcrValidation? validation)
    {
        var receipt = new Receipt
        {
            Id = receiptId,
            UserId = userId,
            ImageUrl = imageUrl,
            OriginalFileName = filename,
            S3Key = $"{userId}/receipts/{receiptId}/original",
            OcrProvider = "Azure Document Intelligence + Tesseract",
            OcrConfidence = ocrResponse.Confidence,
            CreatedAt = DateTime.UtcNow,
            Status = Receiptly.Domain.Enums.ReceiptStatus.PendingValidation
        };

        // Log all available fields for debugging
        _logger.LogInformation("Available OCR fields: {FieldNames}", string.Join(", ", ocrResponse.Fields.Keys));

        // Set validation information
        if (validation != null)
        {
            receipt.IsValidReceipt = validation.IsValidReceipt;
            receipt.ValidationConfidence = validation.Confidence;
            receipt.ValidationMessage = validation.Message;
            
            // Update status based on validation
            if (validation.IsValidReceipt)
            {
                receipt.Status = Receiptly.Domain.Enums.ReceiptStatus.Validated;
            }
            else
            {
                receipt.Status = Receiptly.Domain.Enums.ReceiptStatus.ValidationFailed;
            }
        }

        // Extract merchant name (from Tesseract override or fallback)
        if (ocrResponse.Fields.TryGetValue("MerchantName", out var merchantName))
        {
            receipt.StoreName = merchantName.Value?.ToString() ?? string.Empty;
            
            // Check if this requires manual review (fallback couldn't find store name)
            if (merchantName.RequiresManualReview == true)
            {
                receipt.Status = Receiptly.Domain.Enums.ReceiptStatus.PendingValidation;
                _logger.LogWarning("Store name could not be detected - marked for manual review. ReceiptId: {ReceiptId}, Source: {Source}", 
                    receipt.Id, merchantName.Source ?? "unknown");
            }
            
            // Log the source of merchant name for debugging
            if (!string.IsNullOrEmpty(merchantName.Source))
            {
                _logger.LogInformation("MerchantName extracted from: {Source}. ReceiptId: {ReceiptId}", 
                    merchantName.Source, receipt.Id);
            }
            
            // Log if we got "Unknown Store" placeholder
            if (receipt.StoreName == "Unknown Store")
            {
                _logger.LogWarning("Receipt has unknown store name - may require manual review. ReceiptId: {ReceiptId}", receipt.Id);
            }
        }
        else
        {
            // No merchant name at all - set empty string
            receipt.StoreName = string.Empty;
            _logger.LogWarning("No MerchantName field found in OCR response. ReceiptId: {ReceiptId}", receipt.Id);
        }

        // Extract merchant address (from Tesseract override)
        if (ocrResponse.Fields.TryGetValue("MerchantAddress", out var merchantAddress))
        {
            receipt.StoreAddress = merchantAddress.Value?.ToString() ?? string.Empty;
        }

        // Extract merchant phone number (from Tesseract override)
        if (ocrResponse.Fields.TryGetValue("MerchantPhoneNumber", out var merchantPhone))
        {
            receipt.StorePhoneNumber = merchantPhone.Value?.ToString() ?? string.Empty;
        }

        // Extract postal code (from Tesseract metadata)
        if (ocrResponse.Metadata != null && ocrResponse.Metadata.TryGetValue("postal_code", out var postalCode))
        {
            receipt.PostalCode = postalCode?.ToString() ?? string.Empty;
        }

        // Extract country (from Tesseract metadata)
        if (ocrResponse.Metadata != null && ocrResponse.Metadata.TryGetValue("country", out var country))
        {
            receipt.Country = country?.ToString() ?? string.Empty;
        }

        // Extract location confidence (from Tesseract metadata)
        if (ocrResponse.Metadata != null && ocrResponse.Metadata.TryGetValue("tesseract_confidence", out var tesseractConf))
        {
            if (float.TryParse(tesseractConf?.ToString(), out var confValue))
            {
                receipt.LocationConfidence = confValue;
            }
        }

        // Extract OCR strategy (from Tesseract metadata)
        if (ocrResponse.Metadata != null && ocrResponse.Metadata.TryGetValue("extraction_strategy", out var strategy))
        {
            receipt.OcrStrategy = strategy?.ToString() ?? string.Empty;
        }

        // Extract transaction date
        if (ocrResponse.Fields.TryGetValue("TransactionDate", out var transactionDate))
        {
            if (DateTime.TryParse(transactionDate.Value?.ToString(), out var parsedDate))
            {
                // Ensure the date is in UTC for PostgreSQL
                receipt.PurchaseDate = parsedDate.Kind == DateTimeKind.Utc 
                    ? parsedDate 
                    : DateTime.SpecifyKind(parsedDate, DateTimeKind.Utc);
            }
        }

        // Extract total amount
        if (ocrResponse.Fields.TryGetValue("Total", out var total))
        {
            if (decimal.TryParse(total.Value?.ToString(), out var totalAmount))
            {
                receipt.TotalAmount = totalAmount;
            }
        }

        // Extract subtotal amount
        if (ocrResponse.Fields.TryGetValue("Subtotal", out var subtotal))
        {
            if (decimal.TryParse(subtotal.Value?.ToString(), out var subtotalAmount))
            {
                receipt.SubtotalAmount = subtotalAmount;
            }
        }

        // Extract tax amount
        if (ocrResponse.Fields.TryGetValue("TotalTax", out var tax))
        {
            if (decimal.TryParse(tax.Value?.ToString(), out var taxAmount))
            {
                receipt.TaxAmount = taxAmount;
            }
        }

        // Extract tip amount
        if (ocrResponse.Fields.TryGetValue("Tip", out var tip))
        {
            if (decimal.TryParse(tip.Value?.ToString(), out var tipAmount))
            {
                receipt.TipAmount = tipAmount;
            }
        }

        // Extract receipt type
        if (ocrResponse.Fields.TryGetValue("ReceiptType", out var receiptType))
        {
            receipt.ReceiptType = receiptType.Value?.ToString() ?? string.Empty;
        }

        // Extract transaction ID
        if (ocrResponse.Fields.TryGetValue("TransactionId", out var transactionId))
        {
            receipt.TransactionId = transactionId.Value?.ToString() ?? string.Empty;
        }

        // Extract line items
        if (ocrResponse.Fields.TryGetValue("Items", out var itemsField))
        {
            _logger.LogInformation("Items field found. ValueType: {ValueType}, ValueArray count: {Count}", 
                itemsField.ValueType, 
                itemsField.ValueArray?.Count ?? 0);
            
            List<OcrField>? itemsList = null;
            
            // Check if items are in ValueArray (normal case)
            if (itemsField.ValueArray != null && itemsField.ValueArray.Count > 0)
            {
                itemsList = itemsField.ValueArray;
                _logger.LogInformation("Using ValueArray with {Count} items", itemsList.Count);
            }
            // If ValueArray is empty, try to deserialize from Value property
            else if (itemsField.Value != null)
            {
                _logger.LogInformation("ValueArray is empty, attempting to deserialize from Value property");
                try
                {
                    var jsonValue = JsonSerializer.Serialize(itemsField.Value);
                    itemsList = JsonSerializer.Deserialize<List<OcrField>>(jsonValue);
                    _logger.LogInformation("Successfully deserialized {Count} items from Value property", itemsList?.Count ?? 0);
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Failed to deserialize items from Value property");
                }
            }
            
            if (itemsList != null && itemsList.Count > 0)
            {
                receipt.Items = ExtractItems(receiptId, itemsList);
                _logger.LogInformation("Extracted {Count} items from receipt", receipt.Items.Count);
            }
            else
            {
                _logger.LogWarning("No items could be extracted from the receipt");
            }
        }
        else
        {
            _logger.LogWarning("Items field not found in OCR response");
        }

        return receipt;
    }

    /// <summary>
    /// Extract individual items from the receipt
    /// </summary>
    private List<Item> ExtractItems(Guid receiptId, List<OcrField> itemsArray)
    {
        var items = new List<Item>();

        foreach (var itemField in itemsArray)
        {
            try
            {
                var item = new Item
                {
                    Id = Guid.NewGuid(),
                    ReceiptId = receiptId,
                    CreatedAt = DateTime.UtcNow
                };

                // Azure returns items with value_type="dictionary" where the actual data is in the Value property
                Dictionary<string, OcrField>? itemData = null;

                // Check if Value is a dictionary (when deserialized from JSON, it might be JsonElement)
                if (itemField.ValueType == "dictionary" && itemField.Value != null)
                {
                    // The Value property contains the item dictionary
                    // We need to deserialize it properly
                    var jsonValue = JsonSerializer.Serialize(itemField.Value);
                    itemData = JsonSerializer.Deserialize<Dictionary<string, OcrField>>(jsonValue);
                }
                else if (itemField.ValueObject != null)
                {
                    // Fallback to ValueObject if it's populated
                    itemData = itemField.ValueObject;
                }

                if (itemData == null)
                {
                    _logger.LogWarning("Could not extract item data - both Value dictionary and ValueObject are null");
                    continue;
                }

                // Extract item description/name
                if (itemData.TryGetValue("Description", out var description))
                {
                    item.Name = description.Value?.ToString() ?? string.Empty;
                }

                // Extract quantity
                if (itemData.TryGetValue("Quantity", out var quantity))
                {
                    if (quantity.Value != null && float.TryParse(quantity.Value.ToString(), out var qty))
                    {
                        item.Quantity = (int)qty;
                    }
                    else
                    {
                        item.Quantity = 1;
                    }
                }
                else
                {
                    item.Quantity = 1;
                }

                // Extract price (try TotalPrice first, then Price)
                decimal price = 0;
                if (itemData.TryGetValue("TotalPrice", out var totalPrice) && totalPrice.Value != null)
                {
                    if (decimal.TryParse(totalPrice.Value.ToString(), out var tp))
                    {
                        price = tp;
                    }
                }
                else if (itemData.TryGetValue("Price", out var unitPrice) && unitPrice.Value != null)
                {
                    if (decimal.TryParse(unitPrice.Value.ToString(), out var up))
                    {
                        price = up;
                    }
                }

                item.Price = price;

                items.Add(item);
                _logger.LogInformation("Extracted item: {Name}, Qty: {Quantity}, Price: {Price}", 
                    item.Name, item.Quantity, item.Price);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error extracting item from receipt");
            }
        }

        return items;
    }
}
