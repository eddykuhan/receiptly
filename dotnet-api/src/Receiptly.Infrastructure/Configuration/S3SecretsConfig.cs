using System.Text.Json.Serialization;

namespace Receiptly.Infrastructure.Configuration;

/// <summary>
/// Configuration class for S3 credentials stored in AWS Secrets Manager
/// Matches the JSON structure in receiptly/s3/credentials secret
/// </summary>
public class S3SecretsConfig
{
    [JsonPropertyName("aws_access_key_id")]
    public string AwsAccessKeyId { get; set; } = string.Empty;

    [JsonPropertyName("aws_secret_access_key")]
    public string AwsSecretAccessKey { get; set; } = string.Empty;

    [JsonPropertyName("bucket_name")]
    public string BucketName { get; set; } = string.Empty;

    [JsonPropertyName("region")]
    public string Region { get; set; } = string.Empty;
}
