using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using Receiptly.Infrastructure.Configuration;

namespace Receiptly.Infrastructure.Services;

public class LlmServiceClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<LlmServiceClient> _logger;

    public LlmServiceClient(HttpClient httpClient, LlmServiceSecretsConfig llmConfig, ILogger<LlmServiceClient> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
        _httpClient.BaseAddress = new Uri(llmConfig.BaseUrl);
    }

    public async Task<CanonicalizationResult> CanonicalizeItemAsync(string rawItem)
    {
        try
        {
            var content = new StringContent(
                JsonSerializer.Serialize(new { raw_item = rawItem }),
                Encoding.UTF8,
                "application/json");

            var response = await _httpClient.PostAsync("/canonicalize_item", content);
            response.EnsureSuccessStatusCode();

            var json = await response.Content.ReadAsStringAsync();
            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            return JsonSerializer.Deserialize<CanonicalizationResult>(json, options) 
                ?? new CanonicalizationResult { CanonicalName = rawItem };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling LLM service for item: {Item}", rawItem);
            return new CanonicalizationResult { CanonicalName = rawItem }; // Fallback to raw item
        }
    }

    public async Task<List<CanonicalizationResult>> CanonicalizeBatchAsync(List<string> items)
    {
        try
        {
            var content = new StringContent(
                JsonSerializer.Serialize(new { items = items }),
                Encoding.UTF8,
                "application/json");

            var response = await _httpClient.PostAsync("/canonicalize_batch", content);
            response.EnsureSuccessStatusCode();

            var json = await response.Content.ReadAsStringAsync();
            using var doc = JsonDocument.Parse(json);
            var resultsArray = doc.RootElement.GetProperty("results");
            
            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            return JsonSerializer.Deserialize<List<CanonicalizationResult>>(resultsArray.GetRawText(), options) 
                ?? items.Select(i => new CanonicalizationResult { CanonicalName = i }).ToList();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling LLM service for batch");
            return items.Select(i => new CanonicalizationResult { CanonicalName = i }).ToList();
        }
    }
}

public class CanonicalizationResult
{
    public string CanonicalName { get; set; } = string.Empty;
    public Guid? CanonicalItemId { get; set; }
}

