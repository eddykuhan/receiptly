using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;

namespace Receiptly.Infrastructure.Services;

/// <summary>
/// Service for validating uploaded receipt files
/// </summary>
public class FileValidationService
{
    private readonly ILogger<FileValidationService> _logger;
    
    // Allowed MIME types for receipts
    private static readonly string[] AllowedMimeTypes = {
        "image/jpeg",
        "image/jpg", 
        "image/png",
        "image/tiff",
        "image/tif",
        "application/pdf"
    };
    
    // File signatures (magic numbers) for validation
    private static readonly Dictionary<string, byte[]> FileSignatures = new()
    {
        { "jpeg", new byte[] { 0xFF, 0xD8, 0xFF } },
        { "png", new byte[] { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A } },
        { "pdf", new byte[] { 0x25, 0x50, 0x44, 0x46 } }, // %PDF
        { "tiff_ii", new byte[] { 0x49, 0x49, 0x2A, 0x00 } }, // TIFF little-endian
        { "tiff_mm", new byte[] { 0x4D, 0x4D, 0x00, 0x2A } }  // TIFF big-endian
    };
    
    private const long MaxFileSizeBytes = 10 * 1024 * 1024; // 10MB
    private const long MinFileSizeBytes = 1024; // 1KB
    
    public FileValidationService(ILogger<FileValidationService> logger)
    {
        _logger = logger;
    }
    
    /// <summary>
    /// Validates if the uploaded file is a valid receipt image or PDF
    /// </summary>
    public async Task<FileValidationResult> ValidateReceiptFileAsync(IFormFile file)
    {
        _logger.LogInformation("Validating file: {FileName}, Size: {Size} bytes, ContentType: {ContentType}", 
            file.FileName, file.Length, file.ContentType);
        
        // Check if file is null or empty
        if (file == null || file.Length == 0)
        {
            return new FileValidationResult
            {
                IsValid = false,
                ErrorMessage = "No file uploaded or file is empty"
            };
        }
        
        // Check file size
        if (file.Length > MaxFileSizeBytes)
        {
            return new FileValidationResult
            {
                IsValid = false,
                ErrorMessage = $"File size ({file.Length / 1024 / 1024}MB) exceeds maximum allowed size ({MaxFileSizeBytes / 1024 / 1024}MB)",
                FileSize = file.Length
            };
        }
        
        if (file.Length < MinFileSizeBytes)
        {
            return new FileValidationResult
            {
                IsValid = false,
                ErrorMessage = $"File size ({file.Length} bytes) is too small to be a valid receipt",
                FileSize = file.Length
            };
        }
        
        // Check MIME type
        if (!AllowedMimeTypes.Contains(file.ContentType?.ToLowerInvariant()))
        {
            return new FileValidationResult
            {
                IsValid = false,
                ErrorMessage = $"Invalid file type '{file.ContentType}'. Allowed types: {string.Join(", ", AllowedMimeTypes)}",
                FileSize = file.Length
            };
        }
        
        // Validate file signature (magic numbers)
        var signatureValidation = await ValidateFileSignatureAsync(file);
        if (!signatureValidation.IsValid)
        {
            return signatureValidation;
        }
        
        _logger.LogInformation("File validation successful. Type: {FileType}, Size: {Size} bytes", 
            signatureValidation.DetectedFileType, file.Length);
        
        return new FileValidationResult
        {
            IsValid = true,
            DetectedFileType = signatureValidation.DetectedFileType,
            FileSize = file.Length
        };
    }
    
    /// <summary>
    /// Validates file signature by checking magic numbers
    /// </summary>
    private async Task<FileValidationResult> ValidateFileSignatureAsync(IFormFile file)
    {
        try
        {
            using var stream = file.OpenReadStream();
            var headerBytes = new byte[8]; // Read first 8 bytes
            var bytesRead = await stream.ReadAsync(headerBytes, 0, headerBytes.Length);
            
            if (bytesRead < 4)
            {
                return new FileValidationResult
                {
                    IsValid = false,
                    ErrorMessage = "Unable to read file header for validation",
                    FileSize = file.Length
                };
            }
            
            // Check against known signatures
            foreach (var (fileType, signature) in FileSignatures)
            {
                if (HeaderMatchesSignature(headerBytes, signature))
                {
                    // Map file type to friendly name
                    var detectedType = fileType switch
                    {
                        "jpeg" => "JPEG Image",
                        "png" => "PNG Image",
                        "pdf" => "PDF Document",
                        "tiff_ii" or "tiff_mm" => "TIFF Image",
                        _ => fileType.ToUpperInvariant()
                    };
                    
                    return new FileValidationResult
                    {
                        IsValid = true,
                        DetectedFileType = detectedType,
                        FileSize = file.Length
                    };
                }
            }
            
            return new FileValidationResult
            {
                IsValid = false,
                ErrorMessage = "File signature does not match any supported receipt format. The file may be corrupted or have the wrong extension.",
                FileSize = file.Length
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error validating file signature for {FileName}", file.FileName);
            return new FileValidationResult
            {
                IsValid = false,
                ErrorMessage = $"Error reading file: {ex.Message}",
                FileSize = file.Length
            };
        }
    }
    
    /// <summary>
    /// Checks if header bytes match a known file signature
    /// </summary>
    private static bool HeaderMatchesSignature(byte[] header, byte[] signature)
    {
        if (header.Length < signature.Length)
            return false;
            
        for (int i = 0; i < signature.Length; i++)
        {
            if (header[i] != signature[i])
                return false;
        }
        
        return true;
    }
}

public class FileValidationResult
{
    public bool IsValid { get; set; }
    public string? ErrorMessage { get; set; }
    public string? DetectedFileType { get; set; }
    public long FileSize { get; set; }
}
