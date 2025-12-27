using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using OneSignalApi.Api;
using OneSignalApi.Client;
using OneSignalApi.Model;
using Receiptly.Core.Interfaces;
using ApiConfiguration = OneSignalApi.Client.Configuration;

namespace Receiptly.Infrastructure.Services;

public class OneSignalNotificationService : INotificationService
{
    private readonly string _appId;
    private readonly string _restApiKey;
    private readonly ILogger<OneSignalNotificationService> _logger;
    private readonly DefaultApi _oneSignalClient;

    public OneSignalNotificationService(
        Microsoft.Extensions.Configuration.IConfiguration configuration,
        ILogger<OneSignalNotificationService> logger)
    {
        _appId = configuration["OneSignal:AppId"] ?? throw new ArgumentException("OneSignal:AppId not configured");
        _restApiKey = configuration["OneSignal:RestApiKey"] ?? throw new ArgumentException("OneSignal:RestApiKey not configured");
        _logger = logger;

        // Configure OneSignal client
        var config = new ApiConfiguration();
        config.BasePath = "https://onesignal.com/api/v1";
        config.AccessToken = _restApiKey;
        _oneSignalClient = new DefaultApi(config);
    }

    public async Task SendReceiptProcessedNotificationAsync(
        string userId,
        string receiptId,
        string storeName,
        decimal totalAmount,
        CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogInformation("Sending receipt processed notification to user {UserId} for receipt {ReceiptId}", userId, receiptId);
            _logger.LogInformation("OneSignal App ID: {AppId}", _appId);
#pragma warning disable CS0612 // Type or member is obsolete
            var notification = new Notification(appId: _appId)
            {
                Contents = new StringMap(en: $"Your receipt from {storeName} (RM {totalAmount:F2}) has been processed!"),
                Headings = new StringMap(en: "Receipt Ready ✅"),
                IncludeExternalUserIds = new List<string> { userId },
                Data = new Dictionary<string, object>
                {
                    { "type", "receipt_processed" },
                    { "receiptId", receiptId },
                    { "storeName", storeName }
                },
                Url = $"/receipt/{receiptId}",
                WebUrl = $"/receipt/{receiptId}"
            };
#pragma warning restore CS0612 // Type or member is obsolete

            var result = await _oneSignalClient.CreateNotificationAsync(notification);
            _logger.LogInformation("Receipt processed notification sent to user {UserId}, notification ID: {NotificationId}", userId, result.Id);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to send receipt processed notification to user {UserId}", userId);
        }
    }

    public async Task SendPriceDropAlertAsync(
        string userId,
        string productName,
        decimal oldPrice,
        decimal newPrice,
        string storeName,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var savingsPercent = ((oldPrice - newPrice) / oldPrice) * 100;
            
#pragma warning disable CS0612 // Type or member is obsolete
            var notification = new Notification(appId: _appId)
            {
                Contents = new StringMap(en: $"{productName} dropped to RM {newPrice:F2} at {storeName}! Save {savingsPercent:F0}%"),
                Headings = new StringMap(en: "Price Drop Alert 🔥"),
                IncludeExternalUserIds = new List<string> { userId },
                Data = new Dictionary<string, object>
                {
                    { "type", "price_drop" },
                    { "productName", productName },
                    { "oldPrice", oldPrice },
                    { "newPrice", newPrice },
                    { "storeName", storeName }
                },
                Url = "/nearby-deals",
                WebUrl = "/nearby-deals"
            };
#pragma warning restore CS0612 // Type or member is obsolete

            var result = await _oneSignalClient.CreateNotificationAsync(notification);
            _logger.LogInformation("Price drop alert sent to user {UserId}, notification ID: {NotificationId}", userId, result.Id);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to send price drop alert to user {UserId}", userId);
        }
    }

    public async Task SendPointsEarnedNotificationAsync(
        string userId,
        int pointsEarned,
        int totalPoints,
        CancellationToken cancellationToken = default)
    {
        try
        {
#pragma warning disable CS0612 // Type or member is obsolete
            var notification = new Notification(appId: _appId)
            {
                Contents = new StringMap(en: $"You earned {pointsEarned} points! You now have {totalPoints} points total."),
                Headings = new StringMap(en: "Points Earned 🎁"),
                IncludeExternalUserIds = new List<string> { userId },
                Data = new Dictionary<string, object>
                {
                    { "type", "points_earned" },
                    { "pointsEarned", pointsEarned },
                    { "totalPoints", totalPoints }
                },
                Url = "/rewards",
                WebUrl = "/rewards"
            };
#pragma warning restore CS0612 // Type or member is obsolete

            var result = await _oneSignalClient.CreateNotificationAsync(notification);
            _logger.LogInformation("Points earned notification sent to user {UserId}, notification ID: {NotificationId}", userId, result.Id);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to send points earned notification to user {UserId}", userId);
        }
    }

    public async Task SendTargetedNotificationAsync(
        string title,
        string message,
        Dictionary<string, string> targetTags,
        string? url = null,
        CancellationToken cancellationToken = default)
    {
        try
        {
            // Use tag-based filtering to target specific user segments
            // For now, send to all users and refine filtering in future versions
            var notification = new Notification(appId: _appId)
            {
                Contents = new StringMap(en: message),
                Headings = new StringMap(en: title),
                IncludedSegments = new List<string> { "All" }, // Send to all subscribed users
                Url = url,
                WebUrl = url
            };

            var result = await _oneSignalClient.CreateNotificationAsync(notification);
            _logger.LogInformation("Targeted notification sent, notification ID: {NotificationId}", result.Id);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to send targeted notification");
        }
    }
}
