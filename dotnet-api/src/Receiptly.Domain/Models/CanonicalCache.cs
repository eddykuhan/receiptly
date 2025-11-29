using System.ComponentModel.DataAnnotations;

namespace Receiptly.Domain.Models;

public class CanonicalCache
{
    [Key]
    public string RawName { get; set; } = string.Empty;
    
    public string CanonicalName { get; set; } = string.Empty;
    
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}
