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

        // Query gold layer and propagate pricing zone records to physical stores
        // We need to handle two cases: 
        // 1. Records with PricingZoneId (propagated to all stores in that zone)
        // 2. Records without PricingZoneId (Standalone/User receipts)

        var queryable = from gold in _context.PurchaseAnalyticsGold.AsNoTracking()
                        
                        // Left join with stores if PricingZoneId is present
                        from store in _context.Stores.AsNoTracking()
                            .Where(s => gold.PricingZoneId != null && s.PricingZoneId == gold.PricingZoneId)
                            .DefaultIfEmpty()
                        
                        select new
                        {
                            Gold = gold,
                            Store = store
                        };

        // Filter based on query parameters
        if (query.StartDate.HasValue)
        {
            var startUtc = EnsureUtc(query.StartDate.Value);
            queryable = queryable.Where(q => q.Gold.PurchaseDate >= startUtc);
        }

        if (query.EndDate.HasValue)
        {
            var endUtc = EnsureUtc(query.EndDate.Value);
            queryable = queryable.Where(q => q.Gold.PurchaseDate <= endUtc);
        }

        if (query.CanonicalItemId.HasValue)
        {
            queryable = queryable.Where(q => q.Gold.CanonicalItemId == query.CanonicalItemId.Value);
        }
        else if (!string.IsNullOrWhiteSpace(query.ProductName))
        {
            var productFilter = $"%{query.ProductName.Trim()}%";
            queryable = queryable.Where(q => EF.Functions.ILike(q.Gold.CanonicalName ?? q.Gold.ItemName, productFilter));
        }

        if (!string.IsNullOrWhiteSpace(query.StoreName))
        {
            var storeFilter = $"%{query.StoreName.Trim()}%";
            queryable = queryable.Where(q => 
                EF.Functions.ILike(q.Store != null ? q.Store.Name : q.Gold.StoreName, storeFilter));
        }

        if (!string.IsNullOrWhiteSpace(query.Category))
        {
            queryable = queryable.Where(q => q.Gold.Category == query.Category);
        }

        // Location filtering logic
        if (query.MinLatitude.HasValue) queryable = queryable.Where(q => (q.Store != null ? q.Store.Latitude : q.Gold.Latitude) >= query.MinLatitude.Value);
        if (query.MaxLatitude.HasValue) queryable = queryable.Where(q => (q.Store != null ? q.Store.Latitude : q.Gold.Latitude) <= query.MaxLatitude.Value);
        if (query.MinLongitude.HasValue) queryable = queryable.Where(q => (q.Store != null ? q.Store.Longitude : q.Gold.Longitude) >= query.MinLongitude.Value);
        if (query.MaxLongitude.HasValue) queryable = queryable.Where(q => (q.Store != null ? q.Store.Longitude : q.Gold.Longitude) <= query.MaxLongitude.Value);

        // No location filter needed here - scraped data joins to stores via PricingZoneId,
        // user receipts have lat/lng in gold record. Both cases are handled by the join.

        var totalCount = await queryable.LongCountAsync(cancellationToken);
        var skip = (page - 1) * pageSize;

        // Apply distance-based sorting if user coordinates are provided
        IQueryable<dynamic> orderedQuery;
        if (query.UserLatitude.HasValue && query.UserLongitude.HasValue)
        {
            var userLat = query.UserLatitude.Value;
            var userLng = query.UserLongitude.Value;
            
            orderedQuery = queryable
                .OrderBy(q => Math.Abs((q.Store != null ? q.Store.Latitude : (q.Gold.Latitude ?? 0)) - userLat) + 
                              Math.Abs((q.Store != null ? q.Store.Longitude : (q.Gold.Longitude ?? 0)) - userLng))
                .ThenByDescending(q => q.Gold.PurchaseDate);
        }
        else
        {
            orderedQuery = queryable
                .OrderByDescending(q => q.Gold.PurchaseDate)
                .ThenBy(q => q.Gold.ItemName);
        }

        var results = await orderedQuery
            .Skip(skip)
            .Take(pageSize)
            .ToListAsync(cancellationToken);

        var mappedRecords = results.Select(r => new PurchaseAnalyticsRecord
        {
            ItemId = r.Gold.ItemId,
            ReceiptId = r.Gold.ReceiptId,
            ItemName = r.Gold.ItemName,
            CanonicalName = r.Gold.CanonicalName,
            UnitPrice = r.Gold.UnitPrice,
            TotalPrice = r.Gold.TotalPrice,
            Quantity = r.Gold.Quantity,
            PurchaseDate = r.Gold.PurchaseDate,
            // Prioritize store-specific data
            StoreName = r.Store != null ? r.Store.Name : r.Gold.StoreName,
            StoreAddress = r.Store != null ? r.Store.Address ?? r.Gold.StoreAddress : r.Gold.StoreAddress,
            Latitude = r.Store != null ? r.Store.Latitude : r.Gold.Latitude,
            Longitude = r.Store != null ? r.Store.Longitude : r.Gold.Longitude,
            Category = r.Gold.Category,
            StorePhoneNumber = r.Gold.StorePhoneNumber,
            ReceiptType = r.Gold.ReceiptType,
            TransactionId = r.Gold.TransactionId,
            PaymentMethod = r.Gold.PaymentMethod,
            Status = Enum.TryParse<Receiptly.Domain.Enums.ReceiptStatus>((string)r.Gold.ReceiptStatus, out Receiptly.Domain.Enums.ReceiptStatus status) 
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

    public async Task<List<SuggestionResult>> GetSuggestionsAsync(
        string query,
        double? userLat = null,
        double? userLng = null,
        double? radiusKm = null,
        int limit = 10,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(query))
        {
            return new List<SuggestionResult>();
        }

        var trimmedQuery = query.Trim();
        var normalizedQuery = $"%{trimmedQuery}%";
        var recentPurchaseCutoff = DateTime.UtcNow.AddDays(-30);

        // Build base query with multi-field search (Name, Brand, Category)
        var canonicalQuery = _context.CanonicalItems
            .AsNoTracking()
            .Where(c => 
                EF.Functions.ILike(c.Name, normalizedQuery) ||
                EF.Functions.ILike(c.Brand ?? "", normalizedQuery) ||
                EF.Functions.ILike(c.Category ?? "", normalizedQuery));

        // If location provided, filter to items available in nearby stores
        if (userLat.HasValue && userLng.HasValue && radiusKm.HasValue)
        {
            var latDelta = radiusKm.Value / 111.0;
            var lngDelta = radiusKm.Value / (111.0 * Math.Cos(userLat.Value * (Math.PI / 180.0)));
            var minLat = userLat.Value - latDelta;
            var maxLat = userLat.Value + latDelta;
            var minLng = userLng.Value - lngDelta;
            var maxLng = userLng.Value + lngDelta;

            canonicalQuery = canonicalQuery.Where(c => 
                _context.PurchaseAnalyticsGold.Any(g => 
                    g.CanonicalItemId == c.Id &&
                    ((g.Latitude.HasValue && g.Longitude.HasValue &&
                      g.Latitude >= minLat && g.Latitude <= maxLat &&
                      g.Longitude >= minLng && g.Longitude <= maxLng) ||
                     (g.PricingZoneId != null && 
                      _context.Stores.Any(s => 
                          s.PricingZoneId == g.PricingZoneId &&
                          s.Latitude >= minLat && s.Latitude <= maxLat &&
                          s.Longitude >= minLng && s.Longitude <= maxLng)))));
        }

        // Join with purchase analytics for popularity scoring
        var results = await canonicalQuery
            .GroupJoin(
                _context.PurchaseAnalyticsGold,
                c => c.Id,
                g => g.CanonicalItemId,
                (c, purchases) => new
                {
                    Item = c,
                    TotalPurchases = purchases.Count(),
                    RecentPurchases = purchases.Count(p => p.PurchaseDate >= recentPurchaseCutoff),
                    LowestPrice = purchases.Min(p => (decimal?)p.UnitPrice),
                    LowestPriceStore = purchases
                        .Where(p => p.UnitPrice == purchases.Min(x => x.UnitPrice))
                        .Select(p => p.StoreName)
                        .FirstOrDefault()
                })
            .ToListAsync(cancellationToken);

        // Calculate scores and apply fuzzy matching bonus
        var scoredResults = results.Select(r =>
        {
            var score = 0m;
            
            // Exact match bonus (case-insensitive)
            if (r.Item.Name.Equals(trimmedQuery, StringComparison.OrdinalIgnoreCase))
                score += 100;
            else if (r.Item.Name.StartsWith(trimmedQuery, StringComparison.OrdinalIgnoreCase))
                score += 50;
            else if (r.Item.Brand != null && r.Item.Brand.Equals(trimmedQuery, StringComparison.OrdinalIgnoreCase))
                score += 40;
            
            // Popularity scoring: Recent purchases weighted higher
            score += r.RecentPurchases * 5;  // Recent activity bonus
            score += r.TotalPurchases * 1;   // Historical popularity
            
            // Brand match bonus
            if (r.Item.Brand != null && r.Item.Brand.Contains(trimmedQuery, StringComparison.OrdinalIgnoreCase))
                score += 10;

            return new SuggestionResult
            {
                Id = r.Item.Id,
                Name = r.Item.Name,
                Brand = r.Item.Brand,
                Category = r.Item.Category,
                Score = score,
                PurchaseCount = r.TotalPurchases,
                LowestPrice = r.LowestPrice,
                LowestPriceStore = r.LowestPriceStore
            };
        })
        .OrderByDescending(r => r.Score)
        .ThenBy(r => r.Name)
        .Take(limit)
        .ToList();

        return scoredResults;
    }

    public async Task<List<string>> GetCategoriesAsync(CancellationToken cancellationToken = default)
    {
        return await _context.PurchaseAnalyticsGold
            .AsNoTracking()
            .Where(g => g.Category != null)
            .Select(g => g.Category!)
            .Distinct()
            .OrderBy(c => c)
            .ToListAsync(cancellationToken);
    }

    public async Task<List<StoreStats>> GetNearbyStoresAsync(
        double lat,
        double lng,
        double radiusKm,
        CancellationToken cancellationToken = default)
    {
        // Calculate bounding box
        var latDelta = radiusKm / 111.0;
        var minLat = lat - latDelta;
        var maxLat = lat + latDelta;
        var lngDelta = radiusKm / (111.0 * Math.Cos(lat * (Math.PI / 180.0)));
        var minLng = lng - lngDelta;
        var maxLng = lng + lngDelta;

        var stores = await _context.PurchaseAnalyticsGold
            .AsNoTracking()
            .Where(g => g.Latitude.HasValue && g.Longitude.HasValue &&
                        g.Latitude >= minLat && g.Latitude <= maxLat &&
                        g.Longitude >= minLng && g.Longitude <= maxLng)
            .Select(g => new { g.StoreName, g.StoreAddress, g.Latitude, g.Longitude })
            .Distinct()
            .ToListAsync(cancellationToken);

        return stores.Select(s => new StoreStats
        {
            StoreName = s.StoreName,
            Latitude = s.Latitude,
            Longitude = s.Longitude
            // Address isn't in StoreStats but we could add it if needed. 
            // For now, StoreStats only has StoreName, PurchaseCount, etc.
            // Let's stick to what StoreStats has.
        })
        .GroupBy(s => s.StoreName) // Ensure unique store names for the dropdown
        .Select(g => g.First())
        .OrderBy(s => s.StoreName)
        .ToList();
    }
}

