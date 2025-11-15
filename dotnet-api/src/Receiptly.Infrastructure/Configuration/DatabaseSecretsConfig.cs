using System.Text.Json.Serialization;

namespace Receiptly.Infrastructure.Configuration;

/// <summary>
/// Configuration class for PostgreSQL database credentials stored in AWS Secrets Manager
/// Matches the JSON structure in receiptly/database/credentials secret
/// </summary>
public class DatabaseSecretsConfig
{
    [JsonPropertyName("username")]
    public string Username { get; set; } = string.Empty;

    [JsonPropertyName("password")]
    public string Password { get; set; } = string.Empty;

    [JsonPropertyName("host")]
    public string Host { get; set; } = string.Empty;

    [JsonPropertyName("port")]
    public int Port { get; set; } = 5432;

    [JsonPropertyName("database")]
    public string Database { get; set; } = string.Empty;

    [JsonPropertyName("engine")]
    public string Engine { get; set; } = "postgres";

    /// <summary>
    /// Build PostgreSQL connection string from credentials
    /// </summary>
    public string ToConnectionString()
    {
        return $"Host={Host};Port={Port};Database={Database};Username={Username};Password={Password};";
    }
}
