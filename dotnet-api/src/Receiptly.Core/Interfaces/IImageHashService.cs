namespace Receiptly.Core.Interfaces;

/// <summary>
/// Service for computing cryptographic hashes of images for duplicate detection
/// </summary>
public interface IImageHashService
{
    /// <summary>
    /// Computes the SHA256 hash of an image stream
    /// </summary>
    /// <param name="imageStream">The image stream to hash</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>The SHA256 hash as a lowercase hexadecimal string</returns>
    /// <remarks>
    /// The stream position will be reset to 0 after hashing to allow re-reading.
    /// The hash is returned as a 64-character lowercase hexadecimal string.
    /// </remarks>
    Task<string> ComputeHashAsync(Stream imageStream, CancellationToken cancellationToken = default);
}
