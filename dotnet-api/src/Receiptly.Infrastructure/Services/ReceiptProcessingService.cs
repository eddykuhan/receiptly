using Receiptly.Core.Services;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Services;
using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace Receiptly.Infrastructure.Services;

public class ReceiptProcessingService : IReceiptProcessingService
{
    private readonly S3StorageService _s3Storage;
    private readonly PythonOcrClient _ocrClient;
    private readonly ILogger<ReceiptProcessingService> _logger;

    public ReceiptProcessingService(
        S3StorageService s3Storage, 
        PythonOcrClient ocrClient,
        ILogger<ReceiptProcessingService> logger)
    {
        _s3Storage = s3Storage;
        _ocrClient = ocrClient;
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
    /// 7. Return Receipt entity with validation status
    /// </summary>
    public async Task<Receipt> ProcessReceiptAsync(
        string userId,
        Stream imageStream,
        string contentType,
        string filename)
    {
        var receiptId = Guid.NewGuid();
        _logger.LogInformation("Starting receipt processing. ReceiptId: {ReceiptId}, UserId: {UserId}, Filename: {Filename}", 
            receiptId, userId, filename);

        try
        {
            // Step 1: Upload image to S3 and get presigned URL
            _logger.LogInformation("Step 1/6: Uploading image to S3. ReceiptId: {ReceiptId}", receiptId);
            var imageUrl = await _s3Storage.UploadReceiptImageAsync(
                userId,
                receiptId,
                imageStream,
                contentType,
                filename);
            _logger.LogInformation("Image uploaded to S3. PresignedUrl generated. ReceiptId: {ReceiptId}", receiptId);

            // Step 2: Call Python OCR service with the image URL
            _logger.LogInformation("Step 2/6: Calling Python OCR service. ReceiptId: {ReceiptId}", receiptId);
            var ocrResult = await _ocrClient.AnalyzeReceiptAsync(imageUrl);
            _logger.LogInformation("OCR analysis completed. DocType: {DocType}, Confidence: {Confidence}, ReceiptId: {ReceiptId}", 
                ocrResult.Data.DocType, ocrResult.Data.Confidence, receiptId);

            // Step 3: Validate receipt
            _logger.LogInformation("Step 3/6: Validating receipt. ReceiptId: {ReceiptId}", receiptId);
            var validation = ocrResult.Validation;
            if (validation != null)
            {
                _logger.LogInformation("Validation: IsValid={IsValid}, Confidence={Confidence}, Message={Message}, ReceiptId: {ReceiptId}",
                    validation.IsValidReceipt, validation.Confidence, validation.Message, receiptId);
            }

            // Step 4: Save raw OCR response to S3
            _logger.LogInformation("Step 4/6: Saving raw OCR response to S3. ReceiptId: {ReceiptId}", receiptId);
            await _s3Storage.SaveRawResponseAsync(userId, receiptId, ocrResult.Data);

            // Step 5: Extract structured data from OCR response
            _logger.LogInformation("Step 5/6: Extracting structured data. ReceiptId: {ReceiptId}", receiptId);
            var receipt = ExtractReceiptData(receiptId, ocrResult.Data, validation);
            _logger.LogInformation("Data extracted. MerchantName: {MerchantName}, Items: {ItemCount}, Total: {Total}, Status: {Status}, ReceiptId: {ReceiptId}", 
                receipt.StoreName, receipt.Items.Count, receipt.TotalAmount, receipt.Status, receiptId);

            // Step 6: Save extracted data to S3
            _logger.LogInformation("Step 6/6: Saving extracted data to S3. ReceiptId: {ReceiptId}", receiptId);
            await _s3Storage.SaveExtractedDataAsync(userId, receiptId, receipt);

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
    private Receipt ExtractReceiptData(Guid receiptId, OcrResponse ocrResponse, OcrValidation? validation)
    {
        var receipt = new Receipt
        {
            Id = receiptId,
            CreatedAt = DateTime.UtcNow,
            Status = Receiptly.Domain.Enums.ReceiptStatus.PendingValidation
        };

        // Log all available fields for debugging
        _logger.LogInformation("Available OCR fields: {FieldNames}", string.Join(", ", ocrResponse.Fields.Keys));

        // Set validation information
        if (validation != null)
        {
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

        // Extract merchant name
        if (ocrResponse.Fields.TryGetValue("MerchantName", out var merchantName))
        {
            receipt.StoreName = merchantName.Value?.ToString() ?? string.Empty;
        }

        // Extract merchant address
        if (ocrResponse.Fields.TryGetValue("MerchantAddress", out var merchantAddress))
        {
            receipt.StoreAddress = merchantAddress.Value?.ToString() ?? string.Empty;
        }

        // Extract transaction date
        if (ocrResponse.Fields.TryGetValue("TransactionDate", out var transactionDate))
        {
            if (DateTime.TryParse(transactionDate.Value?.ToString(), out var parsedDate))
            {
                receipt.PurchaseDate = parsedDate;
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

        // Extract tax amount
        if (ocrResponse.Fields.TryGetValue("TotalTax", out var tax))
        {
            receipt.TaxAmount = tax.Value?.ToString();
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
