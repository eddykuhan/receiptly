using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Data;

namespace Receiptly.Infrastructure.Services;

public class CanonicalizationService
{
    private readonly ApplicationDbContext _context;
    private readonly LlmServiceClient _llmClient;
    private readonly ILogger<CanonicalizationService> _logger;

    public CanonicalizationService(
        ApplicationDbContext context,
        LlmServiceClient llmClient,
        ILogger<CanonicalizationService> logger)
    {
        _context = context;
        _llmClient = llmClient;
        _logger = logger;
    }

    public async Task<string> GetCanonicalNameAsync(string rawName)
    {
        if (string.IsNullOrWhiteSpace(rawName)) return rawName;

        // 1. Check DB Cache
        var cached = await _context.CanonicalCache.FindAsync(rawName);
        if (cached != null)
        {
            return cached.CanonicalName;
        }

        // 2. Call LLM
        var canonical = await _llmClient.CanonicalizeItemAsync(rawName);

        // 3. Save to DB
        try
        {
            _context.CanonicalCache.Add(new CanonicalCache
            {
                RawName = rawName,
                CanonicalName = canonical
            });
            await _context.SaveChangesAsync();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to save canonical cache for {RawName}", rawName);
        }

        return canonical;
    }
}
