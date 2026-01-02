using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Pgvector;
using Pgvector.EntityFrameworkCore;
using Receiptly.Core.Interfaces;
using Receiptly.Infrastructure.Data;

namespace Receiptly.Infrastructure.Services;

public class GoldLayerQueryService : IGoldLayerQueryService
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<GoldLayerQueryService> _logger;
    private readonly LlmServiceClient _llmClient;

    public GoldLayerQueryService(
        ApplicationDbContext context,
        ILogger<GoldLayerQueryService> logger,
        LlmServiceClient llmClient)
    {
        _context = context;
        _logger = logger;
        _llmClient = llmClient;
    }

    public async Task<CheapestStoreResult?> GetCheapestStoreForItemAsync(
        string itemName, 
        int days = 30, 
        CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("[GetCheapestStoreForItemAsync] Starting search for item: {ItemName}, days: {Days}", itemName, days);
        
        var cutoffDate = DateTime.UtcNow.AddDays(-days);
        _logger.LogDebug("[GetCheapestStoreForItemAsync] Using cutoff date: {CutoffDate}", cutoffDate);

        // Get similar canonical items using semantic search
        var similarCanonicalIds = await FindSimilarCanonicalItemsAsync(itemName, limit: 10, cancellationToken);
        _logger.LogInformation("[GetCheapestStoreForItemAsync] Found {Count} similar canonical items for '{ItemName}'", similarCanonicalIds.Count, itemName);
        
        if (!similarCanonicalIds.Any())
        {
            _logger.LogWarning("[GetCheapestStoreForItemAsync] No similar canonical items found for: {ItemName}", itemName);
            return null;
        }

        _logger.LogDebug("[GetCheapestStoreForItemAsync] Querying PurchaseAnalyticsGold for similar items: {Ids}", string.Join(", ", similarCanonicalIds));
        
        var result = await _context.PurchaseAnalyticsGold
            .Where(p => p.PurchaseDate >= cutoffDate)
            .Where(p => p.CanonicalItemId != null && similarCanonicalIds.Contains(p.CanonicalItemId.Value))
            .GroupBy(p => p.StoreName)
            .Select(g => new
            {
                StoreName = g.Key,
                AveragePrice = g.Average(p => p.UnitPrice),
                LastSeenDate = g.Max(p => p.PurchaseDate),
                SampleCount = g.Count(),
                ItemName = g.First().CanonicalName ?? g.First().ItemName ?? itemName
            })
            .OrderBy(g => g.AveragePrice)
            .FirstOrDefaultAsync(cancellationToken);

        if (result == null)
        {
            _logger.LogWarning("[GetCheapestStoreForItemAsync] No price data found for item: {ItemName}", itemName);
            return null;
        }

        _logger.LogInformation("[GetCheapestStoreForItemAsync] Found cheapest store for '{ItemName}': {Store} at RM {Price:F2} (avg from {Samples} samples, last seen {Date})", 
            result.ItemName, result.StoreName, result.AveragePrice, result.SampleCount, result.LastSeenDate);

        return new CheapestStoreResult
        {
            ItemName = result.ItemName,
            StoreName = result.StoreName ?? "Unknown Store",
            AveragePrice = result.AveragePrice,
            LastSeenDate = result.LastSeenDate,
            SampleCount = result.SampleCount
        };
    }

    public async Task<List<StorePriceComparison>> GetPriceComparisonAsync(
        string itemName, 
        int days = 30, 
        CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("[GetPriceComparisonAsync] Starting price comparison for item: {ItemName}, days: {Days}", itemName, days);
        
        var cutoffDate = DateTime.UtcNow.AddDays(-days);
        _logger.LogDebug("[GetPriceComparisonAsync] Using cutoff date: {CutoffDate}", cutoffDate);

        // Get similar canonical items using semantic search
        var similarCanonicalIds = await FindSimilarCanonicalItemsAsync(itemName, limit: 10, cancellationToken);
        _logger.LogInformation("[GetPriceComparisonAsync] Found {Count} similar canonical items for '{ItemName}'", similarCanonicalIds.Count, itemName);
        
        if (!similarCanonicalIds.Any())
        {
            _logger.LogWarning("[GetPriceComparisonAsync] No similar canonical items found for: {ItemName}", itemName);
            return new List<StorePriceComparison>();
        }

        _logger.LogDebug("[GetPriceComparisonAsync] Querying PurchaseAnalyticsGold for price comparisons: {Ids}", string.Join(", ", similarCanonicalIds));
        
        var comparisons = await _context.PurchaseAnalyticsGold
            .Where(p => p.PurchaseDate >= cutoffDate)
            .Where(p => p.CanonicalItemId != null && similarCanonicalIds.Contains(p.CanonicalItemId.Value))
            .GroupBy(p => p.StoreName)
            .Select(g => new StorePriceComparison
            {
                ItemName = g.First().CanonicalName ?? g.First().ItemName ?? itemName,
                StoreName = g.Key ?? "Unknown Store",
                AveragePrice = g.Average(p => p.UnitPrice),
                MinPrice = g.Min(p => p.UnitPrice),
                MaxPrice = g.Max(p => p.UnitPrice),
                LastSeenDate = g.Max(p => p.PurchaseDate),
                SampleCount = g.Count()
            })
            .OrderBy(c => c.AveragePrice)
            .ToListAsync(cancellationToken);

        _logger.LogInformation("[GetPriceComparisonAsync] Found {Count} store price comparisons for '{ItemName}'", comparisons.Count, itemName);
        
        foreach (var comp in comparisons.Take(3)) // Log top 3 results
        {
            _logger.LogDebug("[GetPriceComparisonAsync] {Store}: RM {Avg:F2} (min: {Min:F2}, max: {Max:F2}, {Samples} samples)", 
                comp.StoreName, comp.AveragePrice, comp.MinPrice, comp.MaxPrice, comp.SampleCount);
        }

        return comparisons;
    }

    public async Task<GroceryListOptimization> OptimizeGroceryListAsync(
        List<string> itemNames, 
        int days = 30, 
        CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("[OptimizeGroceryListAsync] Starting optimization for {Count} items, days: {Days}", itemNames.Count, days);
        
        var optimizedItems = new List<OptimizedItem>();
        decimal totalCost = 0;
        decimal totalAverage = 0;

        foreach (var itemName in itemNames)
        {
            _logger.LogDebug("[OptimizeGroceryListAsync] Processing item: {ItemName}", itemName);
            
            var cheapest = await GetCheapestStoreForItemAsync(itemName, days, cancellationToken);
            var comparisons = await GetPriceComparisonAsync(itemName, days, cancellationToken);

            if (cheapest != null && comparisons.Any())
            {
                var avgPrice = comparisons.Average(c => c.AveragePrice);
                var savings = avgPrice - cheapest.AveragePrice;

                optimizedItems.Add(new OptimizedItem
                {
                    ItemName = cheapest.ItemName,
                    CheapestStore = cheapest.StoreName,
                    CheapestPrice = cheapest.AveragePrice,
                    AveragePrice = avgPrice,
                    Savings = savings,
                    DataAvailable = true
                });

                totalCost += cheapest.AveragePrice;
                totalAverage += avgPrice;
                
                _logger.LogDebug("[OptimizeGroceryListAsync] '{ItemName}' - Cheapest: {Store} RM {Price:F2}, Avg: RM {Avg:F2}, Savings: RM {Savings:F2}", 
                    cheapest.ItemName, cheapest.StoreName, cheapest.AveragePrice, avgPrice, savings);
            }
            else
            {
                optimizedItems.Add(new OptimizedItem
                {
                    ItemName = itemName,
                    CheapestStore = "Data not available",
                    CheapestPrice = 0,
                    AveragePrice = 0,
                    Savings = 0,
                    DataAvailable = false
                });
                
                _logger.LogWarning("[OptimizeGroceryListAsync] No data available for item: {ItemName}", itemName);
            }
        }

        var potentialSavings = totalAverage - totalCost;

        // Determine recommendation strategy
        var storeFrequency = optimizedItems
            .Where(i => i.DataAvailable)
            .GroupBy(i => i.CheapestStore)
            .OrderByDescending(g => g.Count())
            .ToList();

        var recommendedStrategy = storeFrequency.Any()
            ? $"Buy {storeFrequency[0].Count()} items at {storeFrequency[0].Key}"
            : "Insufficient data for recommendations";

        _logger.LogInformation("[OptimizeGroceryListAsync] Optimization complete - Total cost: RM {TotalCost:F2}, Potential savings: RM {Savings:F2}, Strategy: {Strategy}", 
            totalCost, potentialSavings, recommendedStrategy);

        return new GroceryListOptimization
        {
            Items = optimizedItems,
            TotalCost = totalCost,
            PotentialSavings = potentialSavings,
            RecommendedStrategy = recommendedStrategy
        };
    }

    public async Task<List<string>> FindMatchingItemsAsync(
        string keyword, 
        int limit = 20, 
        CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("[FindMatchingItemsAsync] Finding matching items for keyword: '{Keyword}', limit: {Limit}", keyword, limit);
        
        var similarCanonicalIds = await FindSimilarCanonicalItemsAsync(keyword, limit, cancellationToken);
        _logger.LogDebug("[FindMatchingItemsAsync] Found {Count} similar canonical IDs for '{Keyword}'", similarCanonicalIds.Count, keyword);
        
        var items = await _context.CanonicalItems
            .Where(c => similarCanonicalIds.Contains(c.Id))
            .Select(c => c.Name)
            .Distinct()
            .Take(limit)
            .ToListAsync(cancellationToken);

        _logger.LogInformation("[FindMatchingItemsAsync] Found {Count} matching items for '{Keyword}'", items.Count, keyword);
        
        if (items.Any())
        {
            _logger.LogDebug("[FindMatchingItemsAsync] Top matches: {Items}", string.Join(", ", items.Take(5)));
        }

        return items;
    }

    private async Task<List<Guid>> FindSimilarCanonicalItemsAsync(
        string searchText,
        int limit = 10,
        CancellationToken cancellationToken = default)
    {
        const double minSimilarityThreshold = 0.80; // 80% similarity minimum
        const double maxDistanceThreshold = 1 - minSimilarityThreshold; // 0.30 max distance
        
        try
        {
            _logger.LogDebug("[FindSimilarCanonicalItemsAsync] Generating embedding for: '{SearchText}'", searchText);
            
            // Generate embedding for search text
            var embedding = await GenerateEmbeddingAsync(searchText, cancellationToken);
            
            if (embedding == null || embedding.Length == 0)
            {
                _logger.LogWarning("[FindSimilarCanonicalItemsAsync] Failed to generate embedding for: {SearchText}", searchText);
                return new List<Guid>();
            }

            _logger.LogDebug("[FindSimilarCanonicalItemsAsync] Generated embedding with {Dimension} dimensions", embedding.Length);
            
            var vector = new Vector(embedding);
            _logger.LogDebug("[FindSimilarCanonicalItemsAsync] Created vector, querying for similar items (limit: {Limit}, min similarity: {MinSimilarity}%)", 
                limit, minSimilarityThreshold * 100);

            // Find similar items using cosine distance (pgvector)
            // Get items with similarity scores and names for debugging
            var similarItemsWithScores = await _context.CanonicalItemEmbeddings
                .Select(e => new
                {
                    e.CanonicalItemId,
                    Distance = e.Embedding!.CosineDistance(vector),
                    ItemName = e.CanonicalItem!.Name
                })
                .Where(e => e.Distance <= maxDistanceThreshold) // Filter by similarity threshold
                .OrderBy(e => e.Distance)
                .ToListAsync(cancellationToken);

            // Deduplicate by CanonicalItemId (keep best match for each unique item)
            var deduplicatedItems = similarItemsWithScores
                .GroupBy(x => x.CanonicalItemId)
                .Select(g => g.OrderBy(x => x.Distance).First())
                .OrderBy(x => x.Distance)
                .Take(limit)
                .ToList();

            _logger.LogInformation("[FindSimilarCanonicalItemsAsync] Found {Total} matches, {Filtered} after filtering (>{Threshold}% similarity), {Final} after deduplication", 
                similarItemsWithScores.Count, 
                similarItemsWithScores.Count, 
                minSimilarityThreshold * 100,
                deduplicatedItems.Count);
            
            // Log each match with similarity score (lower distance = more similar)
            foreach (var item in deduplicatedItems)
            {
                var similarityPercent = (1 - item.Distance) * 100; // Convert distance to similarity percentage
                _logger.LogInformation("[FindSimilarCanonicalItemsAsync] Match: '{ItemName}' (similarity: {Similarity:F2}%, distance: {Distance:F4})", 
                    item.ItemName, similarityPercent, item.Distance);
            }
            
            var similarItems = deduplicatedItems.Select(x => x.CanonicalItemId).ToList();
            return similarItems;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[FindSimilarCanonicalItemsAsync] Error finding similar items for: {SearchText}", searchText);
            return new List<Guid>();
        }
    }

    private async Task<float[]?> GenerateEmbeddingAsync(string text, CancellationToken cancellationToken)
    {
        return await _llmClient.GenerateEmbeddingAsync(text, cancellationToken);
    }
}
