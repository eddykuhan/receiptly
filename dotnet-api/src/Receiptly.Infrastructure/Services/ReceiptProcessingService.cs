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
    /// 3. Save raw response to S3
    /// 4. Extract structured data
    /// 5. Save extracted data to S3
    /// 6. Return Receipt entity
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
            _logger.LogInformation("Step 1/5: Uploading image to S3. ReceiptId: {ReceiptId}", receiptId);
            var imageUrl = await _s3Storage.UploadReceiptImageAsync(
                userId,
                receiptId,
                imageStream,
                contentType,
                filename);
            _logger.LogInformation("Image uploaded to S3. PresignedUrl generated. ReceiptId: {ReceiptId}", receiptId);

            // Step 2: Call Python OCR service with the image URL
            _logger.LogInformation("Step 2/5: Calling Python OCR service. ReceiptId: {ReceiptId}", receiptId);
            var ocrResponse = await _ocrClient.AnalyzeReceiptAsync(imageUrl);
            _logger.LogInformation("OCR analysis completed. DocType: {DocType}, Confidence: {Confidence}, ReceiptId: {ReceiptId}", 
                ocrResponse.DocType, ocrResponse.Confidence, receiptId);

            // Step 3: Save raw OCR response to S3
            _logger.LogInformation("Step 3/5: Saving raw OCR response to S3. ReceiptId: {ReceiptId}", receiptId);
            await _s3Storage.SaveRawResponseAsync(userId, receiptId, ocrResponse);

            // Step 4: Extract structured data from OCR response
            _logger.LogInformation("Step 4/5: Extracting structured data. ReceiptId: {ReceiptId}", receiptId);
            var receipt = ExtractReceiptData(receiptId, ocrResponse);
            _logger.LogInformation("Data extracted. MerchantName: {MerchantName}, Items: {ItemCount}, Total: {Total}, ReceiptId: {ReceiptId}", 
                receipt.StoreName, receipt.Items.Count, receipt.TotalAmount, receiptId);

            // Step 5: Save extracted data to S3
            _logger.LogInformation("Step 5/5: Saving extracted data to S3. ReceiptId: {ReceiptId}", receiptId);
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
    private Receipt ExtractReceiptData(Guid receiptId, OcrResponse ocrResponse)
    {
        var receipt = new Receipt
        {
            Id = receiptId,
            CreatedAt = DateTime.UtcNow
        };

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
        if (ocrResponse.Fields.TryGetValue("Items", out var itemsField) && itemsField.ValueArray != null)
        {
            receipt.Items = ExtractItems(receiptId, itemsField.ValueArray);
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
            if (itemField.ValueObject == null) continue;

            var item = new Item
            {
                Id = Guid.NewGuid(),
                ReceiptId = receiptId,
                CreatedAt = DateTime.UtcNow
            };

            // Extract item description/name
            if (itemField.ValueObject.TryGetValue("Description", out var description))
            {
                item.Name = description.Value?.ToString() ?? string.Empty;
            }

            // Extract quantity
            if (itemField.ValueObject.TryGetValue("Quantity", out var quantity))
            {
                if (int.TryParse(quantity.Value?.ToString(), out var qty))
                {
                    item.Quantity = qty;
                }
                else
                {
                    item.Quantity = 1; // Default to 1 if not specified
                }
            }
            else
            {
                item.Quantity = 1;
            }

            // Extract price (try TotalPrice first, then Price)
            decimal price = 0;
            if (itemField.ValueObject.TryGetValue("TotalPrice", out var totalPrice))
            {
                decimal.TryParse(totalPrice.Value?.ToString(), out price);
            }
            else if (itemField.ValueObject.TryGetValue("Price", out var unitPrice))
            {
                decimal.TryParse(unitPrice.Value?.ToString(), out price);
            }

            item.Price = price;

            items.Add(item);
        }

        return items;
    }
}
