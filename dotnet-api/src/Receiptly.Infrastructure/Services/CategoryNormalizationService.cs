using Microsoft.Extensions.Logging;

namespace Receiptly.Infrastructure.Services;

/// <summary>
/// Service for normalizing product category names to ensure consistency across different data sources.
/// Handles case variations, spelling differences, whitespace issues, and encoding problems.
/// </summary>
public class CategoryNormalizationService
{
    private readonly ILogger<CategoryNormalizationService> _logger;

    // Standard category mapping for known variations
    private static readonly Dictionary<string, string> CategoryAliases = new(StringComparer.OrdinalIgnoreCase)
    {
        // Spelling variations (British vs American)
        {"yogurt", "Yogurt"},
        {"yoghurt", "Yogurt"},
        
        // Case variations (common patterns from different retailers)
        {"beverages", "Beverages"},
        {"chilled and frozen", "Chilled and Frozen"},
        {"food essentials", "Food Essentials"},
        {"fresh market", "Fresh Market"},
        {"household products", "Household Products"},
        {"snacks", "Snacks"},
        
        // Whitespace issues (trailing spaces from OCR)
        {"uht milk ", "UHT Milk"},
        {"adult milk ", "Adult Milk"},
        
        // Encoding issues (UTF-8 problems)
        {"ros ÿwine", "Rosé Wine"},
        {"rosé wine", "Rosé Wine"},
        
        // Common retailer variations
        {"biscuits & crackers", "Biscuits & Crackers"},
        {"biscuits and cookies", "Biscuits & Cookies"},
        {"health & beauty", "Health & Beauty"},
        {"health and beauty", "Health & Beauty"},
        {"meat & poultry", "Meat & Poultry"},
        {"dairy & eggs", "Dairy & Eggs"},
        
        // Uncategorized/Unknown variations
        {"uncategorized", "Unknown"},
        {"others", "Unknown"},
        {"", "Unknown"},
        
        // All products (generic category)
        {"all products", "All Products"},
    };

    public CategoryNormalizationService(ILogger<CategoryNormalizationService> logger)
    {
        _logger = logger;
    }

    /// <summary>
    /// Normalize a category name to its canonical form.
    /// </summary>
    /// <param name="category">Raw category name from OCR or data source</param>
    /// <returns>Normalized category name</returns>
    public string Normalize(string? category)
    {
        if (string.IsNullOrWhiteSpace(category))
            return "Unknown";

        // Step 1: Trim whitespace
        var normalized = category.Trim();

        // Step 2: Check against known aliases (case-insensitive)
        var lowerKey = normalized.ToLowerInvariant();
        if (CategoryAliases.TryGetValue(lowerKey, out var canonical))
        {
            if (canonical != normalized)
            {
                _logger.LogDebug("Normalized category '{Original}' to '{Canonical}'", category, canonical);
            }
            return canonical;
        }

        // Step 3: Apply title case for unknown categories
        var titleCased = ToTitleCase(normalized);
        
        if (titleCased != normalized)
        {
            _logger.LogDebug("Applied title case to category '{Original}' -> '{TitleCased}'", category, titleCased);
        }

        return titleCased;
    }

    /// <summary>
    /// Normalize a collection of categories and return unique normalized values.
    /// </summary>
    /// <param name="categories">Collection of raw category names</param>
    /// <returns>Distinct normalized category names</returns>
    public List<string> NormalizeAndDeduplicate(IEnumerable<string?> categories)
    {
        return categories
            .Select(Normalize)
            .Distinct()
            .OrderBy(c => c)
            .ToList();
    }

    /// <summary>
    /// Convert a string to title case (e.g., "food essentials" -> "Food Essentials").
    /// Handles special cases like acronyms (UHT, MSG) and ampersands.
    /// </summary>
    private string ToTitleCase(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return text;

        // Split by spaces and common separators
        var words = text.Split(new[] { ' ', '-', '/', '&' }, StringSplitOptions.RemoveEmptyEntries);
        var titleCased = new List<string>();

        foreach (var word in words)
        {
            // Preserve all-uppercase acronyms (UHT, MSG, etc.)
            if (word.Length <= 4 && word.All(char.IsUpper))
            {
                titleCased.Add(word);
            }
            // Preserve words with mixed case (e.g., "iOS", "JavaScript")
            else if (word.Any(char.IsUpper) && word.Any(char.IsLower))
            {
                titleCased.Add(word);
            }
            // Apply title case to lowercase words
            else if (word.Length > 0)
            {
                titleCased.Add(char.ToUpper(word[0]) + word.Substring(1).ToLower());
            }
        }

        // Reconstruct with appropriate separators
        var result = string.Join(" ", titleCased);
        
        // Restore ampersands if present
        if (text.Contains('&'))
        {
            result = result.Replace(" & ", " & ");
        }

        return result;
    }

    /// <summary>
    /// Get all known canonical category names.
    /// Useful for validation and UI dropdowns.
    /// </summary>
    public List<string> GetKnownCategories()
    {
        return CategoryAliases.Values
            .Distinct()
            .OrderBy(c => c)
            .ToList();
    }

    /// <summary>
    /// Check if a category name has known variations.
    /// </summary>
    public bool HasKnownVariations(string category)
    {
        var normalized = Normalize(category);
        return CategoryAliases.Values.Count(v => v == normalized) > 1;
    }
}
