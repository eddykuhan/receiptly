namespace Receiptly.Domain.Models;

public class CanonicalItemAlias
{
    public Guid Id { get; set; }
    public Guid CanonicalItemId { get; set; }
    public string Alias { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
    
    // Amazon-style tracking fields
    public string? Source { get; set; } // 'receipt', 'scraper_variant', 'manual'
    public decimal? MatchConfidence { get; set; }
    public string? MatchMethod { get; set; } // 'exact', 'fuzzy', 'embedding', 'manual'
    public int UsageCount { get; set; } = 1;
    public DateTime? LastSeenAt { get; set; }
    
    // Navigation property
    public CanonicalItem? CanonicalItem { get; set; }
}
