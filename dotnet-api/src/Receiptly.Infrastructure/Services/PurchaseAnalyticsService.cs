using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Receiptly.Core.Interfaces;
using Receiptly.Infrastructure.Data;

namespace Receiptly.Infrastructure.Services;

public class PurchaseAnalyticsService : IPurchaseAnalyticsService
{
    private const int DefaultPageSize = 50;
    private const int MaxPageSize = 500;

    private readonly ApplicationDbContext _context;
    private readonly ILogger<PurchaseAnalyticsService> _logger;

    public PurchaseAnalyticsService(ApplicationDbContext context, ILogger<PurchaseAnalyticsService> logger)
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
            itemsQuery = itemsQuery.Where(i => EF.Functions.ILike(i.Name, productFilter));
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

        return new PurchaseAnalyticsResult
        {
            Items = records,
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

