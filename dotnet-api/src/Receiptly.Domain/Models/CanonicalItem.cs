namespace Receiptly.Domain.Models;

public class CanonicalItem
{
    public Guid Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Category { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    
    // Amazon-style structured attributes
    public bool IsMaster { get; set; } = false;
    public string? SourceType { get; set; } // 'scraped', 'receipt', 'manual'
    public decimal Confidence { get; set; } = 1.0m;
    public Guid? MasterItemId { get; set; }
    
    // Extracted attributes for better matching
    public string? Brand { get; set; }
    public string? Size { get; set; } // e.g., "2L", "500ml"
    public decimal? SizeNormalized { get; set; } // e.g., 2.0
    public string? SizeUnit { get; set; } // e.g., "L", "kg"
    public int PackCount { get; set; } = 1;
    public string? Variant { get; set; } // e.g., "Full Cream", "Low Fat"
    public string[]? NameTokens { get; set; } // Array of key tokens
    
    // Navigation properties
    public CanonicalItem? MasterItem { get; set; }
    public ICollection<CanonicalItem> ChildItems { get; set; } = new List<CanonicalItem>();
    public ICollection<CanonicalItemAlias> Aliases { get; set; } = new List<CanonicalItemAlias>();
}
