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
    private readonly ILogger<PurchaseAnalyticsService> _logger;

    public PurchaseAnalyticsService(
        ApplicationDbContext context,
        ILogger<PurchaseAnalyticsService> logger)
    {
        _context = context;
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

        // Query gold layer directly (no joins needed, corrections already applied)
        var goldQuery = _context.PurchaseAnalyticsGold
            .AsNoTracking();

        if (query.StartDate.HasValue)
        {
            var startUtc = EnsureUtc(query.StartDate.Value);
            goldQuery = goldQuery.Where(g => g.PurchaseDate >= startUtc);
        }

        if (query.EndDate.HasValue)
        {
            var endUtc = EnsureUtc(query.EndDate.Value);
            goldQuery = goldQuery.Where(g => g.PurchaseDate <= endUtc);
        }

        if (!string.IsNullOrWhiteSpace(query.StoreName))
        {
            var storeFilter = $"%{query.StoreName.Trim()}%";
            goldQuery = goldQuery.Where(g => EF.Functions.ILike(g.StoreName, storeFilter));
        }

        if (!string.IsNullOrWhiteSpace(query.ProductName))
        {
            var productFilter = $"%{query.ProductName.Trim()}%";
            // Search by canonical name for better grouping of similar products
            goldQuery = goldQuery.Where(g => EF.Functions.ILike(g.CanonicalName ?? g.ItemName, productFilter));
        }

        if (query.MinLatitude.HasValue)
        {
            var minLat = query.MinLatitude.Value;
            goldQuery = goldQuery.Where(g => g.Latitude.HasValue && g.Latitude.Value >= minLat);
        }

        if (query.MaxLatitude.HasValue)
        {
            var maxLat = query.MaxLatitude.Value;
            goldQuery = goldQuery.Where(g => g.Latitude.HasValue && g.Latitude.Value <= maxLat);
        }

        if (query.MinLongitude.HasValue)
        {
            var minLng = query.MinLongitude.Value;
            goldQuery = goldQuery.Where(g => g.Longitude.HasValue && g.Longitude.Value >= minLng);
        }

        if (query.MaxLongitude.HasValue)
        {
            var maxLng = query.MaxLongitude.Value;
            goldQuery = goldQuery.Where(g => g.Longitude.HasValue && g.Longitude.Value <= maxLng);
        }

        // Filter to only items with location data for price map
        goldQuery = goldQuery.Where(g => g.Latitude.HasValue && g.Longitude.HasValue);

        var totalCount = await goldQuery.LongCountAsync(cancellationToken);
        var skip = (page - 1) * pageSize;

        var records = await goldQuery
            .OrderByDescending(g => g.PurchaseDate)
            .ThenBy(g => g.ItemName)
            .Skip(skip)
            .Take(pageSize)
            .ToListAsync(cancellationToken);

        // Map to PurchaseAnalyticsRecord (after materialization to avoid expression tree limitations)
        var mappedRecords = records.Select(g => new PurchaseAnalyticsRecord
        {
            ItemId = g.ItemId,
            ReceiptId = g.ReceiptId,
            ItemName = g.ItemName,
            Description = null, // Not stored in gold layer
            CanonicalName = g.CanonicalName,
            UnitPrice = g.UnitPrice,
            TotalPrice = g.TotalPrice,
            Quantity = g.Quantity,
            PurchaseDate = g.PurchaseDate,
            StoreName = g.StoreName,
            StoreAddress = g.StoreAddress,
            StorePhoneNumber = g.StorePhoneNumber,
            Latitude = g.Latitude,
            Longitude = g.Longitude,
            ReceiptType = g.ReceiptType,
            TransactionId = g.TransactionId,
            PaymentMethod = g.PaymentMethod,
            Status = Enum.TryParse<Receiptly.Domain.Enums.ReceiptStatus>(g.ReceiptStatus, out var status) 
                ? status 
                : Receiptly.Domain.Enums.ReceiptStatus.PendingValidation
        }).ToList();

        // No need to apply corrections - already in gold layer

        return new PurchaseAnalyticsResult
        {
            Items = mappedRecords,
            TotalCount = totalCount,
            Page = page,
            PageSize = pageSize
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

