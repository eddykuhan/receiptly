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
    private readonly ILogger<ReceiptProcessingService> _logger;

    public ReceiptProcessingService(
        S3StorageService s3Storage, 
        PythonOcrClient ocrClient,
        IReceiptRepository receiptRepository,
        ILogger<ReceiptProcessingService> logger)
    {
        _s3Storage = s3Storage;
        _ocrClient = ocrClient;
        _receiptRepository = receiptRepository;
        _logger = logger;
    }

    /// <summary>
    /// Complete receipt processing workflow:
    /// 1. Upload image to S3
    /// 2. Call Python OCR with presigned URL
    /// 3. Validate receipt confidence
    /// 4. Save raw response to S3
    /// 5. Extract structured data
    /// 6. Save extracted data to S3
    /// 7. Save receipt to PostgreSQL database
    /// 8. Return Receipt entity with validation status
    /// </summary>
    public async Task<Receipt> ProcessReceiptAsync(
        string userId,
        Stream imageStream,
        string contentType,
        string filename,
        CancellationToken cancellationToken = default)
    {
        var receiptId = Guid.NewGuid();
        _logger.LogInformation("Starting receipt processing. ReceiptId: {ReceiptId}, UserId: {UserId}, Filename: {Filename}", 
            receiptId, userId, filename);

        try
        {
            // Step 1: Upload image to S3 and get presigned URL
            _logger.LogInformation("Step 1/7: Uploading image to S3. ReceiptId: {ReceiptId}", receiptId);
            var imageUrl = await _s3Storage.UploadReceiptImageAsync(
                userId,
                receiptId,
                imageStream,
                contentType,
                filename);
            _logger.LogInformation("Image uploaded to S3. PresignedUrl generated. ReceiptId: {ReceiptId}", receiptId);

            // Check cancellation
            cancellationToken.ThrowIfCancellationRequested();

            // Step 2: Call Python OCR service with the image URL
            _logger.LogInformation("Step 2/7: Calling Python OCR service. ReceiptId: {ReceiptId}", receiptId);
            var ocrResult = await _ocrClient.AnalyzeReceiptAsync(imageUrl);
            _logger.LogInformation("OCR analysis completed. DocType: {DocType}, Confidence: {Confidence}, ReceiptId: {ReceiptId}", 
                ocrResult.Data.DocType, ocrResult.Data.Confidence, receiptId);

            // Check cancellation
            cancellationToken.ThrowIfCancellationRequested();

            // Step 3: Validate receipt
            _logger.LogInformation("Step 3/7: Validating receipt. ReceiptId: {ReceiptId}", receiptId);
            var validation = ocrResult.Validation;
            if (validation != null)
            {
                _logger.LogInformation("Validation: IsValid={IsValid}, Confidence={Confidence}, Message={Message}, ReceiptId: {ReceiptId}",
                    validation.IsValidReceipt, validation.Confidence, validation.Message, receiptId);
            }

            // Step 4: Save raw OCR response to S3
            _logger.LogInformation("Step 4/7: Saving raw OCR response to S3. ReceiptId: {ReceiptId}", receiptId);
            await _s3Storage.SaveRawResponseAsync(userId, receiptId, ocrResult.Data);

            // Check cancellation
            cancellationToken.ThrowIfCancellationRequested();

            // Step 5: Extract structured data from OCR response
            _logger.LogInformation("Step 5/7: Extracting structured data. ReceiptId: {ReceiptId}", receiptId);
            var receipt = ExtractReceiptData(receiptId, userId, imageUrl, filename, ocrResult.Data, validation);
            _logger.LogInformation("Data extracted. MerchantName: {MerchantName}, Items: {ItemCount}, Total: {Total}, Status: {Status}, ReceiptId: {ReceiptId}", 
                receipt.StoreName, receipt.Items.Count, receipt.TotalAmount, receipt.Status, receiptId);

            // Step 6: Save extracted data to S3
            _logger.LogInformation("Step 6/7: Saving extracted data to S3. ReceiptId: {ReceiptId}", receiptId);
            await _s3Storage.SaveExtractedDataAsync(userId, receiptId, receipt);

            // Check cancellation
            cancellationToken.ThrowIfCancellationRequested();

            // Step 7: Save receipt to PostgreSQL database
            _logger.LogInformation("Step 7/7: Saving receipt to database. ReceiptId: {ReceiptId}", receiptId);
            receipt.ProcessedAt = DateTime.UtcNow;
            await _receiptRepository.CreateAsync(receipt, cancellationToken);
            _logger.LogInformation("Receipt saved to database. ReceiptId: {ReceiptId}", receiptId);

            _logger.LogInformation("Receipt processing completed successfully. ReceiptId: {ReceiptId}", receiptId);
            return receipt;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to process receipt. ReceiptId: {ReceiptId}, UserId: {UserId}", receiptId, userId);
            throw new Exception($"Failed to process receipt: {ex.Message}", ex);
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

        // Extract merchant name (from Tesseract override)
        if (ocrResponse.Fields.TryGetValue("MerchantName", out var merchantName))
        {
            receipt.StoreName = merchantName.Value?.ToString() ?? string.Empty;
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
