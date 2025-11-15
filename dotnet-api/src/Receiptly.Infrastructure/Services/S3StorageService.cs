using Amazon.S3;
using Amazon.S3.Model;
using Amazon.S3.Transfer;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Receiptly.Infrastructure.Configuration;
using System.Text;
using System.Text.Json;

namespace Receiptly.Infrastructure.Services;

public class S3StorageService
{
    private readonly IAmazonS3 _s3Client;
    private readonly string _bucketName;
    private readonly ILogger<S3StorageService> _logger;

    public S3StorageService(S3SecretsConfig s3Config, ILogger<S3StorageService> logger)
    {
        _logger = logger;
        _bucketName = s3Config.BucketName;

        var config = new AmazonS3Config
        {
            RegionEndpoint = Amazon.RegionEndpoint.GetBySystemName(s3Config.Region)
        };

        _s3Client = new AmazonS3Client(s3Config.AwsAccessKeyId, s3Config.AwsSecretAccessKey, config);
        
        _logger.LogInformation("S3StorageService initialized with bucket: {BucketName} in region: {Region}", 
            _bucketName, s3Config.Region);
    }

    /// <summary>
    /// Upload receipt image to S3 with organized folder structure
    /// Structure: users/{userId}/receipts/{YYYY}/{MM}/{DD}/{receiptId}/
    /// </summary>
    public async Task<string> UploadReceiptImageAsync(
        string userId,
        Guid receiptId,
        Stream imageStream,
        string contentType,
        string filename)
    {
        var now = DateTime.UtcNow;
        var key = $"users/{userId}/receipts/{now:yyyy}/{now:MM}/{now:dd}/{receiptId}/{filename}";

        var uploadRequest = new TransferUtilityUploadRequest
        {
            InputStream = imageStream,
            Key = key,
            BucketName = _bucketName,
            ContentType = contentType,
            CannedACL = S3CannedACL.Private,
            ServerSideEncryptionMethod = ServerSideEncryptionMethod.AES256
        };

        var transferUtility = new TransferUtility(_s3Client);
        await transferUtility.UploadAsync(uploadRequest);

        // Return presigned URL valid for 1 hour (for Python OCR service to download)
        var request = new GetPreSignedUrlRequest
        {
            BucketName = _bucketName,
            Key = key,
            Expires = DateTime.UtcNow.AddHours(1)
        };

        return _s3Client.GetPreSignedURL(request);
    }

    /// <summary>
    /// Save raw Azure Document Intelligence response to S3
    /// </summary>
    public async Task<string> SaveRawResponseAsync(
        string userId,
        Guid receiptId,
        object rawResponse)
    {
        var now = DateTime.UtcNow;
        var key = $"users/{userId}/receipts/{now:yyyy}/{now:MM}/{now:dd}/{receiptId}/raw_response.json";

        var json = JsonSerializer.Serialize(rawResponse, new JsonSerializerOptions
        {
            WriteIndented = true
        });

        var putRequest = new PutObjectRequest
        {
            BucketName = _bucketName,
            Key = key,
            ContentBody = json,
            ContentType = "application/json",
            ServerSideEncryptionMethod = ServerSideEncryptionMethod.AES256
        };

        await _s3Client.PutObjectAsync(putRequest);
        return key;
    }

    /// <summary>
    /// Save extracted receipt data to S3
    /// </summary>
    public async Task<string> SaveExtractedDataAsync(
        string userId,
        Guid receiptId,
        object extractedData)
    {
        var now = DateTime.UtcNow;
        var key = $"users/{userId}/receipts/{now:yyyy}/{now:MM}/{now:dd}/{receiptId}/extracted_data.json";

        var json = JsonSerializer.Serialize(extractedData, new JsonSerializerOptions
        {
            WriteIndented = true
        });

        var putRequest = new PutObjectRequest
        {
            BucketName = _bucketName,
            Key = key,
            ContentBody = json,
            ContentType = "application/json",
            ServerSideEncryptionMethod = ServerSideEncryptionMethod.AES256
        };

        await _s3Client.PutObjectAsync(putRequest);
        return key;
    }

    /// <summary>
    /// Get a presigned URL for accessing a file in S3
    /// </summary>
    public string GetPresignedUrl(string key, int expirationMinutes = 60)
    {
        var request = new GetPreSignedUrlRequest
        {
            BucketName = _bucketName,
            Key = key,
            Expires = DateTime.UtcNow.AddMinutes(expirationMinutes)
        };

        return _s3Client.GetPreSignedURL(request);
    }
}
