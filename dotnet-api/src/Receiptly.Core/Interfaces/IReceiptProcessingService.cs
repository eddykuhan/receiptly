using Receiptly.Domain.Models;

namespace Receiptly.Core.Services;

public interface IReceiptProcessingService
{
    Task<Receipt> ProcessReceiptAsync(string userId, Stream imageStream, string contentType, string filename);
}
