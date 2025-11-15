using System.Text.Json.Serialization;

namespace Receiptly.Infrastructure.Configuration;

/// <summary>
/// Configuration class for OCR service credentials from AWS Secrets Manager.
/// Maps to the JSON structure stored in receiptly/ocr/service secret.
/// </summary>
public class OcrServiceSecretsConfig
{
    [JsonPropertyName("base_url")]
    public string BaseUrl { get; set; } = string.Empty;

    [JsonPropertyName("health_check_url")]
    public string HealthCheckUrl { get; set; } = string.Empty;
}
