using System.Text.Json.Serialization;

namespace Receiptly.Infrastructure.Configuration;

/// <summary>
/// Configuration class for Google Places API credentials stored in AWS Secrets Manager
/// Matches the JSON structure in receiptly/google/credentials secret
/// </summary>
public class GooglePlacesSecretsConfig
{
    [JsonPropertyName("api_key")]
    public string ApiKey { get; set; } = string.Empty;

    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; } = true;
}
