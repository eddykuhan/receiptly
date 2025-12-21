using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Receiptly.Core.Interfaces;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Data;

namespace Receiptly.Infrastructure.Services;

public class PurchaseAnalyticsService : IPurchaseAnalyticsService
{
    private const int DefaultPageSize = 50;
    private const int MaxPageSize = 500;

    private readonly ApplicationDbContext _context;
    private readonly IReceiptCorrectionService _correctionService;
    private readonly ILogger<PurchaseAnalyticsService> _logger;

    public PurchaseAnalyticsService(
        ApplicationDbContext context,
        IReceiptCorrectionService correctionService,
        ILogger<PurchaseAnalyticsService> logger)
    {
        _context = context;
        _correctionService = correctionService;
        _logger = logger;
    }

    public async Task<PurchaseAnalyticsResult> GetPurchasesAsync(
        PurchaseAnalyticsQuery query,
        CancellationToken cancellationToken = default)
    {
        var page = query.Page <= 0 ? 1 : query.Page;
        var pageSize = query.PageSize <= 0 ? DefaultPageSize : Math.Min(query.PageSize, MaxPageSize);

        _logger.LogInformation(
            "Executing purchase analytics query. Page: {Page}, PageSize: {PageSize}, Store: {Store}, Start: {Start}, End: {End}",
            page,
            pageSize,
            query.StoreName,
            query.StartDate,
            query.EndDate);

        var itemsQuery = _context.Items
            .AsNoTracking()
            .Include(i => i.Receipt)
            .Where(i => i.Receipt != null);

        if (query.StartDate.HasValue)
        {
            var startUtc = EnsureUtc(query.StartDate.Value);
            itemsQuery = itemsQuery.Where(i => i.Receipt!.PurchaseDate >= startUtc);
        }

        if (query.EndDate.HasValue)
        {
            var endUtc = EnsureUtc(query.EndDate.Value);
            itemsQuery = itemsQuery.Where(i => i.Receipt!.PurchaseDate <= endUtc);
        }

        if (!string.IsNullOrWhiteSpace(query.StoreName))
        {
            var storeFilter = $"%{query.StoreName.Trim()}%";
            itemsQuery = itemsQuery.Where(i => EF.Functions.ILike(i.Receipt!.StoreName, storeFilter));
        }

        if (!string.IsNullOrWhiteSpace(query.ProductName))
        {
            var productFilter = $"%{query.ProductName.Trim()}%";
            // Search by canonical name for better grouping of similar products
            itemsQuery = itemsQuery.Where(i => EF.Functions.ILike(i.CanonicalName ?? i.Name, productFilter));
        }

        if (query.MinLatitude.HasValue)
        {
            var minLat = query.MinLatitude.Value;
            itemsQuery = itemsQuery.Where(i => i.Receipt!.Latitude.HasValue && i.Receipt.Latitude.Value >= minLat);
        }

        if (query.MaxLatitude.HasValue)
        {
            var maxLat = query.MaxLatitude.Value;
            itemsQuery = itemsQuery.Where(i => i.Receipt!.Latitude.HasValue && i.Receipt.Latitude.Value <= maxLat);
        }

        if (query.MinLongitude.HasValue)
        {
            var minLng = query.MinLongitude.Value;
            itemsQuery = itemsQuery.Where(i => i.Receipt!.Longitude.HasValue && i.Receipt.Longitude.Value >= minLng);
        }

        if (query.MaxLongitude.HasValue)
        {
            var maxLng = query.MaxLongitude.Value;
            itemsQuery = itemsQuery.Where(i => i.Receipt!.Longitude.HasValue && i.Receipt.Longitude.Value <= maxLng);
        }

        var totalCount = await itemsQuery.LongCountAsync(cancellationToken);
        var skip = (page - 1) * pageSize;

        var records = await itemsQuery
            .OrderByDescending(i => i.Receipt!.PurchaseDate)
            .ThenBy(i => i.Name)
            .Skip(skip)
            .Take(pageSize)
            .Select(i => new PurchaseAnalyticsRecord
            {
                ItemId = i.Id,
                ReceiptId = i.ReceiptId,
                ItemName = i.Name,
                Description = i.Description,
                CanonicalName = i.CanonicalName,
                UnitPrice = i.UnitPrice ?? i.Price,
                TotalPrice = i.TotalPrice ?? ((i.UnitPrice ?? i.Price) * i.Quantity),
                Quantity = i.Quantity,
                PurchaseDate = i.Receipt!.PurchaseDate,
                StoreName = i.Receipt.StoreName,
                StoreAddress = i.Receipt.StoreAddress,
                StorePhoneNumber = i.Receipt.StorePhoneNumber,
                Latitude = i.Receipt.Latitude,
                Longitude = i.Receipt.Longitude,
                ReceiptType = i.Receipt.ReceiptType,
                TransactionId = i.Receipt.TransactionId,
                PaymentMethod = i.Receipt.PaymentMethod,
                Status = i.Receipt.Status
            })
            .ToListAsync(cancellationToken);

        // Apply user corrections to the records
        await ApplyCorrectionsToRecordsAsync(records, cancellationToken);

        return new PurchaseAnalyticsResult
        {
            Items = records,
            TotalCount = totalCount,
            Page = page,
            PageSize = pageSize
        };
    }

    /// <summary>
    /// Apply user corrections to analytics records by using ReceiptCorrectionService
    /// and mapping corrected values back to immutable records
    /// </summary>
    private async Task ApplyCorrectionsToRecordsAsync(
        List<PurchaseAnalyticsRecord> records,
        CancellationToken cancellationToken)
    {
        try
        {
            // Get unique receipt IDs
            var receiptIds = records.Select(r => r.ReceiptId).Distinct().ToList();

            if (!receiptIds.Any())
            {
                _logger.LogInformation("No receipt IDs found in analytics records");
                return;
            }

            _logger.LogInformation("Applying corrections to {Count} analytics records from {ReceiptCount} receipts",
                records.Count, receiptIds.Count);

            // Fetch receipts that might have corrections
            var receipts = await _context.Receipts
                .AsNoTracking()
                .Where(r => receiptIds.Contains(r.Id))
                .ToListAsync(cancellationToken);

            _logger.LogInformation("Fetched {ReceiptCount} receipts for correction processing", receipts.Count);

            // Apply corrections using the reusable ReceiptCorrectionService
            await _correctionService.ApplyCorrectionsAsync(receipts, cancellationToken);

            _logger.LogInformation("Corrections applied to receipts");

            // Map corrected receipt values back to analytics records
            var receiptLookup = receipts.ToDictionary(r => r.Id);

            int updatedCount = 0;
            for (int i = 0; i < records.Count; i++)
            {
                if (receiptLookup.TryGetValue(records[i].ReceiptId, out var correctedReceipt))
                {
                    var originalStore = records[i].StoreName;
                    var originalAddress = records[i].StoreAddress;
                    
                    records[i] = MapCorrectedReceiptToRecord(records[i], correctedReceipt);
                    
                    // Log if values changed
                    if (originalStore != records[i].StoreName || originalAddress != records[i].StoreAddress)
                    {
                        _logger.LogInformation(
                            "Updated record {RecordId}: StoreName '{OldStore}' -> '{NewStore}', Address '{OldAddr}' -> '{NewAddr}'",
                            records[i].ItemId, originalStore, records[i].StoreName, 
                            originalAddress, records[i].StoreAddress);
                        updatedCount++;
                    }
                }
            }

            _logger.LogInformation("Applied corrections to {UpdatedCount} out of {TotalCount} records", updatedCount, records.Count);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error applying corrections to analytics records");
            // Don't throw - return original records if correction fails
        }
    }

    /// <summary>
    /// Map corrected receipt values to a new analytics record
    /// </summary>
    private static PurchaseAnalyticsRecord MapCorrectedReceiptToRecord(
        PurchaseAnalyticsRecord originalRecord,
        Receipt correctedReceipt)
    {
        return new PurchaseAnalyticsRecord
        {
            ItemId = originalRecord.ItemId,
            ReceiptId = originalRecord.ReceiptId,
            ItemName = originalRecord.ItemName,
            Description = originalRecord.Description,
            CanonicalName = originalRecord.CanonicalName,
            UnitPrice = originalRecord.UnitPrice,
            TotalPrice = originalRecord.TotalPrice,
            Quantity = originalRecord.Quantity,
            PurchaseDate = originalRecord.PurchaseDate,
            StoreName = correctedReceipt.StoreName,  // Use corrected value
            StoreAddress = correctedReceipt.StoreAddress,  // Use corrected value
            StorePhoneNumber = correctedReceipt.StorePhoneNumber,
            Latitude = correctedReceipt.Latitude,  // Use corrected value (may include lat from address correction)
            Longitude = correctedReceipt.Longitude,  // Use corrected value (may include long from address correction)
            ReceiptType = correctedReceipt.ReceiptType,
            TransactionId = correctedReceipt.TransactionId,
            PaymentMethod = correctedReceipt.PaymentMethod,
            Status = correctedReceipt.Status
        };
    }

    private static DateTime EnsureUtc(DateTime dateTime)
    {
        if (dateTime.Kind == DateTimeKind.Utc)
        {
            return dateTime;
        }

        return dateTime.Kind == DateTimeKind.Unspecified
            ? DateTime.SpecifyKind(dateTime, DateTimeKind.Utc)
            : dateTime.ToUniversalTime();
    }
}

