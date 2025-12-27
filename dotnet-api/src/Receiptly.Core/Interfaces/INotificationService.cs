namespace Receiptly.Core.Interfaces;

public interface INotificationService
{
    Task SendReceiptProcessedNotificationAsync(string userId, string receiptId, string storeName, decimal totalAmount, CancellationToken cancellationToken = default);
    Task SendPriceDropAlertAsync(string userId, string productName, decimal oldPrice, decimal newPrice, string storeName, CancellationToken cancellationToken = default);
    Task SendPointsEarnedNotificationAsync(string userId, int pointsEarned, int totalPoints, CancellationToken cancellationToken = default);
    Task SendTargetedNotificationAsync(string title, string message, Dictionary<string, string> targetTags, string? url = null, CancellationToken cancellationToken = default);
}
