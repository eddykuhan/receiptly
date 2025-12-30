using Pgvector;

namespace Receiptly.Domain.Models;

public class CanonicalItemEmbedding
{
    public Guid CanonicalItemId { get; set; }
    public Vector? Embedding { get; set; }
    public DateTime CreatedAt { get; set; }
    
    // Navigation property
    public CanonicalItem? CanonicalItem { get; set; }
}
