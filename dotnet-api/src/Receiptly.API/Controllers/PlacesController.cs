using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Receiptly.Infrastructure.Services;

namespace Receiptly.API.Controllers;

/// <summary>
/// API endpoints for Google Places autocomplete functionality
/// Provides address suggestions for store location corrections
/// Requires Clerk authentication to prevent API abuse and control costs.
/// </summary>
[ApiController]
[Route("api/places")]
public class PlacesController : ControllerBase
{
    private readonly GooglePlacesClient _placesClient;
    private readonly ILogger<PlacesController> _logger;

    public PlacesController(
        GooglePlacesClient placesClient,
        ILogger<PlacesController> logger)
    {
        _placesClient = placesClient;
        _logger = logger;
    }

    /// <summary>
    /// Get address autocomplete suggestions
    /// </summary>
    /// <param name="input">User's partial address input</param>
    /// <param name="location">Geographic region (default: Malaysia)</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>List of address suggestions</returns>
    [HttpGet("autocomplete")]
    public async Task<ActionResult<PlacesAutocompleteResponse>> GetAutocomplete(
        [FromQuery] string input,
        [FromQuery] string? location,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(input))
        {
            return BadRequest(new { error = "Input parameter is required" });
        }

        try
        {
            var suggestions = await _placesClient.GetAutocompleteSuggestionsAsync(
                input, 
                location ?? "Malaysia",
                cancellationToken);

            return Ok(new PlacesAutocompleteResponse
            {
                Success = true,
                Suggestions = suggestions
            });
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Autocomplete request cancelled for input: {Input}", input);
            return StatusCode(499, new { error = "Request cancelled" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting autocomplete suggestions for input: {Input}", input);
            return StatusCode(500, new { error = "Failed to fetch suggestions" });
        }
    }
}

/// <summary>
/// Response for autocomplete endpoint
/// </summary>
public class PlacesAutocompleteResponse
{
    public bool Success { get; set; }
    public List<PlaceSuggestion> Suggestions { get; set; } = new();
}
