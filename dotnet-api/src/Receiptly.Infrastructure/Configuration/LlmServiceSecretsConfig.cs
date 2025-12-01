using System.Text.Json.Serialization;

namespace Receiptly.Infrastructure.Configuration;

/// <summary>
/// Configuration class for LLM service credentials from AWS Secrets Manager.
/// Maps to the JSON structure stored in receiptly/llm/service secret.
/// </summary>
public class LlmServiceSecretsConfig
{
    [JsonPropertyName("base_url")]
    public string BaseUrl { get; set; } = string.Empty;

    [JsonPropertyName("health_check_url")]
    public string HealthCheckUrl { get; set; } = string.Empty;
}
