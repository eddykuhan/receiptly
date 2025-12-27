using System.Text.Json.Serialization;

namespace Receiptly.Infrastructure.Configuration;

/// <summary>
/// Configuration class for OneSignal credentials stored in AWS Secrets Manager
/// Matches the JSON structure in receiptly/onesignal/credentials secret
/// </summary>
public class OneSignalSecretsConfig
{
    [JsonPropertyName("app_id")]
    public string AppId { get; set; } = string.Empty;

    [JsonPropertyName("rest_api_key")]
    public string RestApiKey { get; set; } = string.Empty;

    [JsonPropertyName("safari_web_id")]
    public string SafariWebId { get; set; } = string.Empty;
}
