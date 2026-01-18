using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
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

    public async Task<float[]?> GenerateEmbeddingAsync(string text, CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogDebug("[GenerateEmbeddingAsync] Requesting embedding for text: '{Text}' (length: {Length})", text, text.Length);
            
            var content = new StringContent(
                JsonSerializer.Serialize(new { text }),
                Encoding.UTF8,
                "application/json");

            var response = await _httpClient.PostAsync("/embeddings/generate", content, cancellationToken);
            _logger.LogDebug("[GenerateEmbeddingAsync] Response status: {Status}", response.StatusCode);

            response.EnsureSuccessStatusCode();

            var responseBody = await response.Content.ReadAsStringAsync(cancellationToken);
            _logger.LogDebug("[GenerateEmbeddingAsync] Response body length: {Length} chars", responseBody.Length);
            
            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            var result = JsonSerializer.Deserialize<EmbeddingResponse>(responseBody, options);

            if (result?.Embedding != null)
            {
                _logger.LogDebug("[GenerateEmbeddingAsync] Successfully generated embedding with {Dimension} dimensions", result.Embedding.Length);
            }
            else
            {
                _logger.LogWarning("[GenerateEmbeddingAsync] Embedding response was null or empty");
            }

            return result?.Embedding;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[GenerateEmbeddingAsync] Error generating embedding for text: '{Text}'", text);
            return null;
        }
    }

    public async Task<List<string>> ExtractItemKeywordsAsync(string question, CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogDebug("Calling LLM service to extract items from: {Question}", question);
            
            var content = new StringContent(
                JsonSerializer.Serialize(new { question }),
                Encoding.UTF8,
                "application/json");

            var response = await _httpClient.PostAsync("/chat/extract_items", content, cancellationToken);
            response.EnsureSuccessStatusCode();

            var responseBody = await response.Content.ReadAsStringAsync(cancellationToken);
            _logger.LogInformation("LLM extract_items response: {Response}", responseBody);
            
            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            var result = JsonSerializer.Deserialize<ExtractItemsResponse>(responseBody, options);
            _logger.LogInformation("Deserialized {ItemCount} items from response", result?.Items?.Count ?? 0);

            return result?.Items ?? new List<string>();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error extracting item keywords from question: {Question}", question);
            return new List<string>();
        }
    }

    public async Task<string> AskChatQuestionAsync(
        string question, 
        Dictionary<string, object> priceData, 
        CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogDebug("Sending question to LLM with {ItemCount} items of price data", priceData.Count);
            
            var requestBody = new
            {
                question,
                price_data = priceData
            };

            var requestJson = JsonSerializer.Serialize(requestBody);
            _logger.LogDebug("LLM request payload size: {Size} bytes", requestJson.Length);
            
            var content = new StringContent(requestJson, Encoding.UTF8, "application/json");

            var response = await _httpClient.PostAsync("/chat/ask", content, cancellationToken);
            response.EnsureSuccessStatusCode();

            var responseBody = await response.Content.ReadAsStringAsync(cancellationToken);
            _logger.LogDebug("LLM chat/ask response: {Response}", responseBody);
            
            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            var result = JsonSerializer.Deserialize<ChatResponse>(responseBody, options);

            return result?.Answer ?? "I couldn't generate an answer. Please try again.";
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting LLM answer");
            return "I'm having trouble connecting to my knowledge base. Please try again later.";
        }
    }
}

public class CanonicalizationResult
{
    [JsonPropertyName("canonical_name")]
    public string CanonicalName { get; set; } = string.Empty;
    [JsonPropertyName("canonical_item_id")]
    public Guid? CanonicalItemId { get; set; }
}

public class EmbeddingResponse
{
    public float[] Embedding { get; set; } = Array.Empty<float>();
}

public class ExtractItemsResponse
{
    public List<string> Items { get; set; } = new();
}

public class ChatResponse
{
    public string Answer { get; set; } = string.Empty;
}

