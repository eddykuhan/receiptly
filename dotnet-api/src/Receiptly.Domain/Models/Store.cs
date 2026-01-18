using System.ComponentModel.DataAnnotations;

namespace Receiptly.Domain.Models;

/// <summary>
/// Represents a physical store location mapped to a pricing zone.
/// Used to display pins on the Price Map and link them to scraped national/regional prices.
/// </summary>
public class Store
{
    public Guid Id { get; set; }
    
    [Required]
    public string Name { get; set; } = string.Empty;
    
    public string? RetailChain { get; set; } // e.g., "Jaya Grocer", "MYDIN"
    
    /// <summary>
    /// ID used to link this store to a price list in PurchaseAnalyticsGold.
    /// E.g., "MYDIN_NATIONAL", "JG_PENANG".
    /// </summary>
    [Required]
    public string PricingZoneId { get; set; } = string.Empty;
    
    public string? Address { get; set; }
    
    [Required]
    public double Latitude { get; set; }
    
    [Required]
    public double Longitude { get; set; }
    
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
}
