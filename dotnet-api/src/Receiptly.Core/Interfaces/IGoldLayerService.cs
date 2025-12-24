using Receiptly.Domain.Models;

namespace Receiptly.Core.Interfaces;

/// <summary>
/// Service for managing the gold layer (purchase_analytics_gold table).
/// Provides append-only price history for analytics and price map features.
/// </summary>
public interface IGoldLayerService
{
    /// <summary>
    /// Append new items to the gold layer from a newly created receipt.
    /// Called during receipt upload to capture price snapshot.
    /// </summary>
    Task AppendItemsAsync(List<Item> items, Receipt receipt, CancellationToken cancellationToken = default);
    
    /// <summary>
    /// Update canonical names in gold layer when user corrections are applied.
    /// Updates in-place: sets CanonicalName, IsCorrected = true, CorrectedAt.
    /// </summary>
    Task UpdateCorrectionsAsync(Guid receiptId, Dictionary<Guid, string> itemCorrections, CancellationToken cancellationToken = default);
}
