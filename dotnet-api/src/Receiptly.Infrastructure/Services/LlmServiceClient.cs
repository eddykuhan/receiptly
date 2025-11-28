using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Receiptly.Infrastructure.Services;

public class LlmServiceClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<LlmServiceClient> _logger;
    private const string BaseUrl = "http://localhost:8500";

    public LlmServiceClient(HttpClient httpClient, ILogger<LlmServiceClient> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
        _httpClient.BaseAddress = new Uri(BaseUrl);
    }

    public async Task<string> CanonicalizeItemAsync(string rawItem)
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
            using var doc = JsonDocument.Parse(json);
            return doc.RootElement.GetProperty("canonical_name").GetString() ?? rawItem;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling LLM service for item: {Item}", rawItem);
            return rawItem; // Fallback to raw item
        }
    }

    public async Task<List<string>> CanonicalizeBatchAsync(List<string> items)
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
            var array = doc.RootElement.GetProperty("canonical_names");
            var result = new List<string>();
            foreach (var element in array.EnumerateArray())
            {
                result.Add(element.GetString() ?? string.Empty);
            }
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling LLM service for batch");
            return items; // Fallback
        }
    }
}
