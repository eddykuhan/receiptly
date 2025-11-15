using System.Security.Cryptography;
using System.Text;
using Receiptly.Core.Interfaces;

namespace Receiptly.Infrastructure.Services;

/// <summary>
/// Service for computing SHA256 hashes of images for duplicate detection
/// </summary>
public class ImageHashService : IImageHashService
{
    /// <inheritdoc />
    public async Task<string> ComputeHashAsync(Stream imageStream, CancellationToken cancellationToken = default)
    {
        if (imageStream == null)
            throw new ArgumentNullException(nameof(imageStream));
        
        if (!imageStream.CanSeek)
            throw new ArgumentException("Stream must be seekable to allow position reset after hashing", nameof(imageStream));
        
        // Save the current position
        var originalPosition = imageStream.Position;
        
        try
        {
            // Reset to beginning to ensure we hash the entire stream
            imageStream.Position = 0;
            
            // Compute SHA256 hash
            var hashBytes = await SHA256.HashDataAsync(imageStream, cancellationToken);
            
            // Convert to lowercase hexadecimal string
            var hashString = Convert.ToHexString(hashBytes).ToLowerInvariant();
            
            return hashString;
        }
        finally
        {
            // Reset stream position so it can be read again (e.g., for S3 upload)
            imageStream.Position = originalPosition;
        }
    }
}
