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

    public async Task<CanonicalizationResult> GetCanonicalNameAsync(string rawName)
    {
        if (string.IsNullOrWhiteSpace(rawName)) 
            return new CanonicalizationResult { CanonicalName = rawName };

        // Call LLM Service (which handles cleanup, vector search, and its own caching)
        return await _llmClient.CanonicalizeItemAsync(rawName);
    }
}


