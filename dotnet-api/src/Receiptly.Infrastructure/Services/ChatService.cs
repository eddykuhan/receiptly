using System.Net.Http;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Http;
using Microsoft.Extensions.Logging;
using Receiptly.Core.Interfaces;

namespace Receiptly.Infrastructure.Services;

public class ChatService : IChatService
{
    private readonly IGoldLayerQueryService _goldLayerService;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<ChatService> _logger;
    private readonly string _llmServiceUrl;

    public ChatService(
        IGoldLayerQueryService goldLayerService,
        IHttpClientFactory httpClientFactory,
        ILogger<ChatService> logger,
        IConfiguration configuration)
    {
        _goldLayerService = goldLayerService;
        _httpClientFactory = httpClientFactory;
        _logger = logger;
        _llmServiceUrl = configuration["LlmService:Url"] ?? "http://localhost:8500";
    }

    public async Task<string> AskQuestionAsync(
        string userId, 
        string question, 
        CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Processing chat question for user {UserId}: {Question}", userId, question);
        
        try
        {
            // Step 1: Extract item keywords from the question using LLM
            _logger.LogInformation("Step 1: Extracting item keywords from question");
            var items = await ExtractItemKeywordsAsync(question, cancellationToken);
            _logger.LogInformation("Extracted {ItemCount} items: {Items}", items?.Count ?? 0, string.Join(", ", items ?? new List<string>()));
            
            if (items == null || items.Count == 0)
            {
                _logger.LogWarning("No items extracted from question: {Question}", question);
                return "I couldn't identify any specific items in your question. Could you please mention what groceries you're looking for?";
            }

            // Step 2: Query gold layer for price data
            _logger.LogInformation("Step 2: Gathering price data for {ItemCount} items", items.Count);
            var priceData = await GatherPriceDataAsync(items, cancellationToken);
            _logger.LogInformation("Found price data for {DataCount} items", priceData.Count);

            // Step 3: Send question + price data to LLM for natural language answer
            _logger.LogInformation("Step 3: Getting LLM answer with {DataCount} price entries", priceData.Count);
            var answer = await GetLlmAnswerAsync(question, priceData, cancellationToken);
            _logger.LogInformation("Successfully generated answer (length: {AnswerLength})", answer.Length);

            return answer;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing chat question: {Question}", question);
            return "I'm having trouble processing your question right now. Please try again later.";
        }
    }

    private async Task<List<string>> ExtractItemKeywordsAsync(
        string question, 
        CancellationToken cancellationToken)
    {
        try
        {
            _logger.LogDebug("Calling LLM service to extract items from: {Question}", question);
            var httpClient = _httpClientFactory.CreateClient();
            var requestBody = new { question };
            var content = new StringContent(
                JsonSerializer.Serialize(requestBody),
                Encoding.UTF8,
                "application/json");

            var response = await httpClient.PostAsync(
                $"{_llmServiceUrl}/chat/extract_items",
                content,
                cancellationToken);

            response.EnsureSuccessStatusCode();

            var responseBody = await response.Content.ReadAsStringAsync(cancellationToken);
            _logger.LogInformation("LLM extract_items response: {Response}", responseBody);
            
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            };
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

    private async Task<Dictionary<string, object>> GatherPriceDataAsync(
        List<string> items, 
        CancellationToken cancellationToken)
    {
        var priceData = new Dictionary<string, object>();

        foreach (var item in items)
        {
            try
            {
                _logger.LogDebug("Querying gold layer for item: {Item}", item);
                var comparisons = await _goldLayerService.GetPriceComparisonAsync(
                    item, 
                    days: 30, 
                    cancellationToken);

                if (comparisons.Any())
                {
                    // Use the canonical item name from the first comparison result
                    var canonicalItemName = comparisons.First().ItemName;
                    _logger.LogInformation("Found {Count} store prices for item: {Item} (canonical: {CanonicalName})", 
                        comparisons.Count, item, canonicalItemName);
                    
                    priceData[canonicalItemName] = comparisons.Select(c => new
                    {
                        store = c.StoreName,
                        avg_price = c.AveragePrice,
                        min_price = c.MinPrice,
                        max_price = c.MaxPrice,
                        last_seen = c.LastSeenDate.ToString("yyyy-MM-dd"),
                        samples = c.SampleCount
                    }).ToList();
                }
                else
                {
                    _logger.LogInformation("No price data found for item: {Item}", item);
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error gathering price data for item: {Item}", item);
            }
        }

        return priceData;
    }

    private async Task<string> GetLlmAnswerAsync(
        string question, 
        Dictionary<string, object> priceData, 
        CancellationToken cancellationToken)
    {
        try
        {
            _logger.LogDebug("Sending question to LLM with {ItemCount} items of price data", priceData.Count);
            var httpClient = _httpClientFactory.CreateClient();
            var requestBody = new
            {
                question,
                price_data = priceData
            };

            var requestJson = JsonSerializer.Serialize(requestBody);
            _logger.LogDebug("LLM request payload size: {Size} bytes", requestJson.Length);
            
            var content = new StringContent(
                requestJson,
                Encoding.UTF8,
                "application/json");

            var response = await httpClient.PostAsync(
                $"{_llmServiceUrl}/chat/ask",
                content,
                cancellationToken);

            response.EnsureSuccessStatusCode();

            var responseBody = await response.Content.ReadAsStringAsync(cancellationToken);
            _logger.LogDebug("LLM chat/ask response: {Response}", responseBody);
            
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            };
            var result = JsonSerializer.Deserialize<ChatResponse>(responseBody, options);

            return result?.Answer ?? "I couldn't generate an answer. Please try again.";
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting LLM answer");
            return "I'm having trouble connecting to my knowledge base. Please try again later.";
        }
    }

    private class ExtractItemsResponse
    {
        public List<string> Items { get; set; } = new();
    }

    private class ChatResponse
    {
        public string Answer { get; set; } = string.Empty;
    }
}
