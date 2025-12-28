using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Receiptly.Core.Interfaces;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Data;

namespace Receiptly.Infrastructure.Services;

/// <summary>
/// Service for managing the gold layer (purchase_analytics_gold table).
/// Implements append-only pattern for price history and analytics.
/// </summary>
public class GoldLayerService : IGoldLayerService
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<GoldLayerService> _logger;

    public GoldLayerService(
        ApplicationDbContext context,
        ILogger<GoldLayerService> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task AppendItemsAsync(List<Item> items, Receipt receipt, CancellationToken cancellationToken = default)
    {
        if (items == null || !items.Any() || receipt == null)
        {
            _logger.LogWarning("AppendItemsAsync called with null or empty items/receipt");
            return;
        }

        try
        {
            var goldRecords = items.Select(item => new PurchaseAnalyticsGold
            {
                Id = Guid.NewGuid(),
                ItemId = item.Id,
                ReceiptId = receipt.Id,
                UserId = receipt.UserId,
                
                // Item details
                ItemName = item.Name,
                CanonicalName = item.CanonicalName,
                UnitPrice = item.UnitPrice ?? item.Price,
                TotalPrice = item.TotalPrice ?? (item.UnitPrice ?? item.Price) * item.Quantity,
                Quantity = item.Quantity,
                
                // Purchase context
                PurchaseDate = receipt.PurchaseDate,
                StoreName = receipt.StoreName,
                StoreAddress = receipt.StoreAddress,
                StorePhoneNumber = receipt.StorePhoneNumber,
                
                // Location data (critical for price map)
                Latitude = receipt.Latitude,
                Longitude = receipt.Longitude,
                LocationConfidence = receipt.LocationConfidence,
                
                // Receipt metadata
                ReceiptType = receipt.ReceiptType,
                TransactionId = receipt.TransactionId,
                PaymentMethod = receipt.PaymentMethod,
                ReceiptStatus = receipt.Status.ToString(),
                
                // Correction tracking
                IsCorrected = false,
                CorrectedAt = null,
                
                // Audit
                CreatedAt = DateTime.UtcNow
            }).ToList();

            await _context.PurchaseAnalyticsGold.AddRangeAsync(goldRecords, cancellationToken);
            await _context.SaveChangesAsync(cancellationToken);

            _logger.LogInformation(
                "Appended {Count} items to gold layer for receipt {ReceiptId}",
                goldRecords.Count,
                receipt.Id);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, 
                "Failed to append items to gold layer for receipt {ReceiptId}",
                receipt.Id);
            throw;
        }
    }

    public async Task UpdateCorrectionsAsync(
        Guid receiptId, 
        Dictionary<Guid, string> itemCorrections, 
        CancellationToken cancellationToken = default)
    {
        if (itemCorrections == null || !itemCorrections.Any())
        {
            _logger.LogWarning("UpdateCorrectionsAsync called with null or empty corrections");
            return;
        }

        try
        {
            var correctedAt = DateTime.UtcNow;
            
            foreach (var correction in itemCorrections)
            {
                var itemId = correction.Key;
                var correctedName = correction.Value;

                // Update gold records for this item using ExecuteUpdateAsync (efficient bulk update)
                var updatedCount = await _context.PurchaseAnalyticsGold
                    .Where(g => g.ItemId == itemId)
                    .ExecuteUpdateAsync(setters => setters
                        .SetProperty(g => g.CanonicalName, correctedName)
                        .SetProperty(g => g.IsCorrected, true)
                        .SetProperty(g => g.CorrectedAt, correctedAt),
                        cancellationToken);

                _logger.LogInformation(
                    "Updated {Count} gold records for item {ItemId} with corrected name: {CorrectedName}",
                    updatedCount,
                    itemId,
                    correctedName);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "Failed to update corrections in gold layer for receipt {ReceiptId}",
                receiptId);
            throw;
        }
    }

    public async Task UpdateReceiptFieldsAsync(
        Guid receiptId, 
        string? storeAddress = null,
        double? latitude = null, 
        double? longitude = null,
        CancellationToken cancellationToken = default)
    {
        try
        {
            // Build the query for all gold records from this receipt
            var query = _context.PurchaseAnalyticsGold
                .Where(g => g.ReceiptId == receiptId);

            // Build dynamic update based on provided parameters
            // We need to update only the fields that are provided (not null)
            var hasUpdates = false;

            if (storeAddress != null)
            {
                await query.ExecuteUpdateAsync(setters => setters
                    .SetProperty(g => g.StoreAddress, storeAddress),
                    cancellationToken);
                hasUpdates = true;
            }

            if (latitude.HasValue && longitude.HasValue)
            {
                await query.ExecuteUpdateAsync(setters => setters
                    .SetProperty(g => g.Latitude, latitude.Value)
                    .SetProperty(g => g.Longitude, longitude.Value),
                    cancellationToken);
                hasUpdates = true;
            }

            if (hasUpdates)
            {
                _logger.LogInformation(
                    "Updated gold layer receipt fields for receipt {ReceiptId}. StoreAddress: {StoreAddress}, Lat: {Latitude}, Lon: {Longitude}",
                    receiptId,
                    storeAddress ?? "(unchanged)",
                    latitude?.ToString() ?? "(unchanged)",
                    longitude?.ToString() ?? "(unchanged)");
            }
            else
            {
                _logger.LogWarning(
                    "UpdateReceiptFieldsAsync called for receipt {ReceiptId} but no fields were provided to update",
                    receiptId);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "Failed to update receipt fields in gold layer for receipt {ReceiptId}",
                receiptId);
            throw;
        }
    }
}
