using Receiptly.Infrastructure.Configuration;
using Microsoft.Extensions.Logging;
using System.Net.Http.Json;
using System.Text.Json.Serialization;
using System.Web;

namespace Receiptly.Infrastructure.Services;

/// <summary>
/// Client for Google Places API autocomplete functionality
/// Provides address suggestions for store location corrections
/// </summary>
public class GooglePlacesClient
{
    private readonly HttpClient _httpClient;
    private readonly GooglePlacesSecretsConfig _config;
    private readonly ILogger<GooglePlacesClient> _logger;
    private const string PlacesApiBaseUrl = "https://places.googleapis.com/v1";

    public GooglePlacesClient(
        HttpClient httpClient, 
        GooglePlacesSecretsConfig config,
        ILogger<GooglePlacesClient> logger)
    {
        _httpClient = httpClient;
        _config = config;
        _logger = logger;
    }

    /// <summary>
    /// Get autocomplete suggestions for a given address query
    /// </summary>
    /// <param name="input">User's partial address input</param>
    /// <param name="location">Geographic bias (default: Malaysia)</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>List of address suggestions</returns>
    public async Task<List<PlaceSuggestion>> GetAutocompleteSuggestionsAsync(
        string input, 
        string location = "Malaysia",
        CancellationToken cancellationToken = default)
    {
        if (!_config.Enabled)
        {
            _logger.LogWarning("Google Places API is disabled");
            return new List<PlaceSuggestion>();
        }

        if (string.IsNullOrWhiteSpace(input))
        {
            return new List<PlaceSuggestion>();
        }

        try
        {
            var url = $"{PlacesApiBaseUrl}/places:searchText";
            
            var requestBody = new
            {
                textQuery = $"{input} {location}",
                maxResultCount = 5
            };

            var request = new HttpRequestMessage(HttpMethod.Post, url);
            request.Headers.Add("X-Goog-Api-Key", _config.ApiKey);
            request.Headers.Add("X-Goog-FieldMask", "places.displayName,places.formattedAddress,places.location");
            request.Content = JsonContent.Create(requestBody);

            var response = await _httpClient.SendAsync(request, cancellationToken);

            if (!response.IsSuccessStatusCode)
            {
                var errorContent = await response.Content.ReadAsStringAsync(cancellationToken);
                _logger.LogError("Google Places API returned {StatusCode}: {Error}", 
                    response.StatusCode, errorContent);
                return new List<PlaceSuggestion>();
            }

            var result = await response.Content.ReadFromJsonAsync<PlacesSearchResponse>(cancellationToken: cancellationToken);
            
            if (result?.Places == null || result.Places.Count == 0)
            {
                _logger.LogInformation("No suggestions found for input: {Input}", input);
                return new List<PlaceSuggestion>();
            }

            return result.Places
                .Select(p => new PlaceSuggestion
                {
                    Description = p.FormattedAddress ?? p.DisplayName?.Text ?? "",
                    MainText = p.DisplayName?.Text ?? "",
                    SecondaryText = p.FormattedAddress ?? "",
                    Latitude = p.Location?.Latitude,
                    Longitude = p.Location?.Longitude
                })
                .Where(s => !string.IsNullOrWhiteSpace(s.Description))
                .ToList();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error fetching autocomplete suggestions for input: {Input}", input);
            return new List<PlaceSuggestion>();
        }
    }
}

/// <summary>
/// Response from Google Places API search
/// </summary>
public class PlacesSearchResponse
{
    [JsonPropertyName("places")]
    public List<Place> Places { get; set; } = new();
}

/// <summary>
/// Individual place result from Google Places API
/// </summary>
public class Place
{
    [JsonPropertyName("displayName")]
    public DisplayName? DisplayName { get; set; }

    [JsonPropertyName("formattedAddress")]
    public string? FormattedAddress { get; set; }
    
    [JsonPropertyName("location")]
    public Location? Location { get; set; }
}

/// <summary>
/// Display name object from Google Places API
/// </summary>
public class DisplayName
{
    [JsonPropertyName("text")]
    public string? Text { get; set; }
}

/// <summary>
/// Location coordinates from Google Places API
/// </summary>
public class Location
{
    [JsonPropertyName("latitude")]
    public double? Latitude { get; set; }
    
    [JsonPropertyName("longitude")]
    public double? Longitude { get; set; }
}

/// <summary>
/// Simplified place suggestion for frontend
/// </summary>
public class PlaceSuggestion
{
    public string Description { get; set; } = string.Empty;
    public string MainText { get; set; } = string.Empty;
    public string SecondaryText { get; set; } = string.Empty;
    public double? Latitude { get; set; }
    public double? Longitude { get; set; }
}
