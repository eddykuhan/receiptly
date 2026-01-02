using Receiptly.Domain.Models;

namespace Receiptly.Core.Interfaces;

/// <summary>
/// Service for querying the PurchaseAnalyticsGold table for price comparisons
/// </summary>
public interface IGoldLayerQueryService
{
    /// <summary>
    /// Get the cheapest store for a specific item
    /// </summary>
    /// <param name="itemName">Item name or canonical name (fuzzy match)</param>
    /// <param name="days">Number of days to look back (default 30)</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Store with cheapest average price</returns>
    Task<CheapestStoreResult?> GetCheapestStoreForItemAsync(
        string itemName, 
        int days = 30, 
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Get price comparison across all stores for an item
    /// </summary>
    /// <param name="itemName">Item name or canonical name</param>
    /// <param name="days">Number of days to look back</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>List of stores with prices sorted by price</returns>
    Task<List<StorePriceComparison>> GetPriceComparisonAsync(
        string itemName, 
        int days = 30, 
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Optimize a grocery list by finding cheapest store for each item
    /// </summary>
    /// <param name="itemNames">List of item names</param>
    /// <param name="days">Number of days to look back</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Optimization results with per-item recommendations and totals</returns>
    Task<GroceryListOptimization> OptimizeGroceryListAsync(
        List<string> itemNames, 
        int days = 30, 
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Search for items matching keywords (for fuzzy search)
    /// </summary>
    Task<List<string>> FindMatchingItemsAsync(
        string keyword, 
        int limit = 20, 
        CancellationToken cancellationToken = default);
}

/// <summary>
/// Result for cheapest store query
/// </summary>
public class CheapestStoreResult
{
    public string ItemName { get; set; } = string.Empty;
    public string StoreName { get; set; } = string.Empty;
    public decimal AveragePrice { get; set; }
    public DateTime LastSeenDate { get; set; }
    public int SampleCount { get; set; } // How many purchases this is based on
}

/// <summary>
/// Store price comparison entry
/// </summary>
public class StorePriceComparison
{
    public string ItemName { get; set; } = string.Empty; // Canonical item name
    public string StoreName { get; set; } = string.Empty;
    public decimal AveragePrice { get; set; }
    public decimal MinPrice { get; set; }
    public decimal MaxPrice { get; set; }
    public DateTime LastSeenDate { get; set; }
    public int SampleCount { get; set; }
}

/// <summary>
/// Grocery list optimization result
/// </summary>
public class GroceryListOptimization
{
    public List<OptimizedItem> Items { get; set; } = new();
    public decimal TotalCost { get; set; }
    public decimal PotentialSavings { get; set; }
    public string RecommendedStrategy { get; set; } = string.Empty;
}

/// <summary>
/// Per-item optimization recommendation
/// </summary>
public class OptimizedItem
{
    public string ItemName { get; set; } = string.Empty;
    public string CheapestStore { get; set; } = string.Empty;
    public decimal CheapestPrice { get; set; }
    public decimal AveragePrice { get; set; }
    public decimal Savings { get; set; }
    public bool DataAvailable { get; set; } = true;
}
