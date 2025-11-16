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

    /// <summary>
    /// Move failed receipt to quarantine folder
    /// Structure: users/{userId}/failed-receipts/{YYYY}/{MM}/{DD}/{receiptId}/
    /// This keeps failed receipts separate from valid ones for later review/cleanup
    /// </summary>
    public async Task<string> MoveToFailedFolderAsync(
        string userId,
        Guid receiptId,
        string originalKey,
        string failureReason)
    {
        var now = DateTime.UtcNow;
        var failedKey = $"users/{userId}/failed-receipts/{now:yyyy}/{now:MM}/{now:dd}/{receiptId}/{Path.GetFileName(originalKey)}";

        try
        {
            // Copy to failed folder
            var copyRequest = new CopyObjectRequest
            {
                SourceBucket = _bucketName,
                SourceKey = originalKey,
                DestinationBucket = _bucketName,
                DestinationKey = failedKey,
                ServerSideEncryptionMethod = ServerSideEncryptionMethod.AES256,
                MetadataDirective = S3MetadataDirective.REPLACE
            };

            // Add metadata about the failure
            copyRequest.Metadata.Add("x-amz-meta-failure-reason", failureReason);
            copyRequest.Metadata.Add("x-amz-meta-failed-at", DateTime.UtcNow.ToString("o"));
            copyRequest.Metadata.Add("x-amz-meta-original-key", originalKey);

            await _s3Client.CopyObjectAsync(copyRequest);

            // Delete from original location
            await _s3Client.DeleteObjectAsync(_bucketName, originalKey);

            _logger.LogInformation("Moved failed receipt to quarantine. ReceiptId: {ReceiptId}, Reason: {Reason}", 
                receiptId, failureReason);

            return failedKey;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to move receipt to failed folder. ReceiptId: {ReceiptId}", receiptId);
            throw;
        }
    }

    /// <summary>
    /// Save failure details to S3 for debugging and auditing
    /// </summary>
    public async Task SaveFailureDetailsAsync(
        string userId,
        Guid receiptId,
        string failureReason,
        string? ocrResponse = null,
        Exception? exception = null)
    {
        var now = DateTime.UtcNow;
        var key = $"users/{userId}/failed-receipts/{now:yyyy}/{now:MM}/{now:dd}/{receiptId}/failure_details.json";

        var failureDetails = new
        {
            ReceiptId = receiptId,
            UserId = userId,
            FailedAt = DateTime.UtcNow,
            Reason = failureReason,
            OcrResponse = ocrResponse,
            Exception = exception != null ? new
            {
                Message = exception.Message,
                StackTrace = exception.StackTrace,
                InnerException = exception.InnerException?.Message
            } : null
        };

        var json = JsonSerializer.Serialize(failureDetails, new JsonSerializerOptions
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
        _logger.LogInformation("Saved failure details. ReceiptId: {ReceiptId}, Key: {Key}", receiptId, key);
    }

    /// <summary>
    /// Delete a specific receipt and all its associated files
    /// </summary>
    public async Task DeleteReceiptAsync(string userId, Guid receiptId, DateTime? receiptDate = null)
    {
        var date = receiptDate ?? DateTime.UtcNow;
        var prefix = $"users/{userId}/receipts/{date:yyyy}/{date:MM}/{date:dd}/{receiptId}/";

        try
        {
            var listRequest = new ListObjectsV2Request
            {
                BucketName = _bucketName,
                Prefix = prefix
            };

            var listResponse = await _s3Client.ListObjectsV2Async(listRequest);

            foreach (var obj in listResponse.S3Objects)
            {
                await _s3Client.DeleteObjectAsync(_bucketName, obj.Key);
                _logger.LogDebug("Deleted S3 object: {Key}", obj.Key);
            }

            _logger.LogInformation("Deleted all S3 objects for receipt. ReceiptId: {ReceiptId}, Prefix: {Prefix}", 
                receiptId, prefix);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error deleting receipt from S3. ReceiptId: {ReceiptId}", receiptId);
            throw;
        }
    }
}
