namespace Receiptly.Domain.Models;

public class CanonicalItemAlias
{
    public Guid Id { get; set; }
    public Guid CanonicalItemId { get; set; }
    public string Alias { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
    
    // Navigation property
    public CanonicalItem? CanonicalItem { get; set; }
}
