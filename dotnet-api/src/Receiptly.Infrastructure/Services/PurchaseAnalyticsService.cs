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

    public async Task<PriceHistoryResult> GetPriceHistoryAsync(
        string userId,
        string canonicalName,
        int days,
        CancellationToken cancellationToken = default)
    {
        var cutoffDate = DateTime.UtcNow.AddDays(-days);

        // Query all users' data from gold layer for comprehensive price comparison
        var pricePoints = await _context.PurchaseAnalyticsGold
            .AsNoTracking()
            .Where(g => g.CanonicalName == canonicalName 
                && g.PurchaseDate >= cutoffDate)
            .OrderBy(g => g.PurchaseDate)
            .Select(g => new PriceHistoryPoint
            {
                PurchaseDate = g.PurchaseDate,
                UnitPrice = g.UnitPrice,
                StoreName = g.StoreName,
                ItemId = g.ItemId
            })
            .ToListAsync(cancellationToken);

        if (!pricePoints.Any())
        {
            return new PriceHistoryResult
            {
                CanonicalName = canonicalName,
                PricePoints = new List<PriceHistoryPoint>(),
                Statistics = new PriceStatistics()
            };
        }

        var minPrice = pricePoints.Min(p => p.UnitPrice);
        var maxPrice = pricePoints.Max(p => p.UnitPrice);
        var avgPrice = pricePoints.Average(p => p.UnitPrice);
        var currentPrice = pricePoints.Last().UnitPrice;
        var cheapestStore = pricePoints.First(p => p.UnitPrice == minPrice).StoreName;
        var mostExpensiveStore = pricePoints.First(p => p.UnitPrice == maxPrice).StoreName;

        return new PriceHistoryResult
        {
            CanonicalName = canonicalName,
            PricePoints = pricePoints,
            Statistics = new PriceStatistics
            {
                MinPrice = minPrice,
                MaxPrice = maxPrice,
                AveragePrice = avgPrice,
                CurrentPrice = currentPrice,
                CheapestStore = cheapestStore,
                MostExpensiveStore = mostExpensiveStore
            }
        };
    }

    public async Task<SavingsReportResult> GetSavingsReportAsync(
        string userId,
        int days,
        CancellationToken cancellationToken = default)
    {
        var startDate = DateTime.UtcNow.AddDays(-days);
        var endDate = DateTime.UtcNow;

        // Get user's purchases in the period
        var userPurchases = await _context.PurchaseAnalyticsGold
            .AsNoTracking()
            .Where(g => g.UserId == userId 
                && g.PurchaseDate >= startDate 
                && g.PurchaseDate <= endDate)
            .ToListAsync(cancellationToken);

        if (!userPurchases.Any())
        {
            return new SavingsReportResult
            {
                TotalSpent = 0,
                PotentialSavings = 0,
                SavingsPercentage = 0,
                Opportunities = new List<SavingsOpportunity>(),
                StartDate = startDate,
                EndDate = endDate
            };
        }

        var totalSpent = userPurchases.Sum(p => p.TotalPrice);

        // Find cheaper alternatives (within the same time period from all users)
        var opportunities = new List<SavingsOpportunity>();

        foreach (var purchase in userPurchases)
        {
            if (string.IsNullOrEmpty(purchase.CanonicalName)) continue;

            // Find cheapest price for this item from other stores
            var cheapestAlternative = await _context.PurchaseAnalyticsGold
                .AsNoTracking()
                .Where(g => g.CanonicalName == purchase.CanonicalName 
                    && g.StoreName != purchase.StoreName
                    && g.PurchaseDate >= startDate 
                    && g.PurchaseDate <= endDate)
                .OrderBy(g => g.UnitPrice)
                .FirstOrDefaultAsync(cancellationToken);

            if (cheapestAlternative != null && cheapestAlternative.UnitPrice < purchase.UnitPrice)
            {
                var saving = (purchase.UnitPrice - cheapestAlternative.UnitPrice) * purchase.Quantity;
                if (saving > 0.01m) // Only show meaningful savings
                {
                    opportunities.Add(new SavingsOpportunity
                    {
                        CanonicalName = purchase.CanonicalName,
                        PurchasedAt = purchase.StoreName,
                        PaidPrice = purchase.UnitPrice,
                        CheaperAt = cheapestAlternative.StoreName,
                        CheaperPrice = cheapestAlternative.UnitPrice,
                        PotentialSaving = saving,
                        Quantity = purchase.Quantity,
                        PurchaseDate = purchase.PurchaseDate
                    });
                }
            }
        }

        var potentialSavings = opportunities.Sum(o => o.PotentialSaving);
        var savingsPercentage = totalSpent > 0 ? (potentialSavings / totalSpent) * 100 : 0;

        return new SavingsReportResult
        {
            TotalSpent = totalSpent,
            PotentialSavings = potentialSavings,
            SavingsPercentage = savingsPercentage,
            Opportunities = opportunities.OrderByDescending(o => o.PotentialSaving).ToList(),
            StartDate = startDate,
            EndDate = endDate
        };
    }

    public async Task<StoreComparisonResult> GetStoreComparisonAsync(
        string userId,
        int days,
        CancellationToken cancellationToken = default)
    {
        var startDate = DateTime.UtcNow.AddDays(-days);
        var endDate = DateTime.UtcNow;

        var userPurchases = await _context.PurchaseAnalyticsGold
            .AsNoTracking()
            .Where(g => g.UserId == userId 
                && g.PurchaseDate >= startDate 
                && g.PurchaseDate <= endDate)
            .ToListAsync(cancellationToken);

        if (!userPurchases.Any())
        {
            return new StoreComparisonResult
            {
                Stores = new List<StoreStats>(),
                StartDate = startDate,
                EndDate = endDate,
                TotalPurchases = 0,
                TotalSpent = 0
            };
        }

        var totalSpent = userPurchases.Sum(p => p.TotalPrice);
        var totalPurchases = userPurchases.Count;

        // Calculate average price per item across all stores
        var itemAveragePrices = userPurchases
            .Where(p => !string.IsNullOrEmpty(p.CanonicalName))
            .GroupBy(p => p.CanonicalName)
            .ToDictionary(
                g => g.Key!,
                g => g.Average(p => p.UnitPrice)
            );

        var storeGroups = userPurchases.GroupBy(p => p.StoreName);
        var stores = new List<StoreStats>();

        foreach (var storeGroup in storeGroups)
        {
            var storePurchases = storeGroup.ToList();
            var storeTotal = storePurchases.Sum(p => p.TotalPrice);
            var purchaseCount = storePurchases.Count;

            // Calculate price index (how this store compares to market average)
            var priceIndex = 0m;
            var comparableItems = storePurchases
                .Where(p => !string.IsNullOrEmpty(p.CanonicalName) && itemAveragePrices.ContainsKey(p.CanonicalName!))
                .ToList();

            if (comparableItems.Any())
            {
                var storePriceVsAverage = comparableItems
                    .Select(p => (p.UnitPrice / itemAveragePrices[p.CanonicalName!] - 1) * 100)
                    .Average();
                priceIndex = storePriceVsAverage;
            }

            // Get top items by frequency and total spent
            var topItems = storePurchases
                .GroupBy(p => p.CanonicalName ?? p.ItemName)
                .OrderByDescending(g => g.Sum(p => p.TotalPrice))
                .Take(5)
                .Select(g => g.Key)
                .ToList();

            var firstPurchase = storePurchases.First();

            stores.Add(new StoreStats
            {
                StoreName = storeGroup.Key,
                PurchaseCount = purchaseCount,
                TotalSpent = storeTotal,
                AverageTransactionValue = storeTotal / purchaseCount,
                PriceIndex = priceIndex,
                UniqueItemsCount = storePurchases.Select(p => p.CanonicalName ?? p.ItemName).Distinct().Count(),
                Latitude = firstPurchase.Latitude,
                Longitude = firstPurchase.Longitude,
                TopItems = topItems
            });
        }

        return new StoreComparisonResult
        {
            Stores = stores.OrderByDescending(s => s.TotalSpent).ToList(),
            StartDate = startDate,
            EndDate = endDate,
            TotalPurchases = totalPurchases,
            TotalSpent = totalSpent
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

