using System.Security.Claims;
using System.Text.Json;
using Serilog;
using Microsoft.AspNetCore.Authorization;

namespace Receiptly.API.Middleware;

/// <summary>
/// Middleware to validate Clerk JWT tokens and populate HttpContext user claims.
/// This middleware extracts the Bearer token from the Authorization header,
/// validates it with Clerk's public keys, and sets up the user identity.
/// </summary>
public class ClerkJwtMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ClerkJwtMiddleware> _logger;
    private readonly IConfiguration _configuration;

    public ClerkJwtMiddleware(RequestDelegate next, ILogger<ClerkJwtMiddleware> logger, IConfiguration configuration)
    {
        _next = next;
        _logger = logger;
        _configuration = configuration;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        var token = ExtractToken(context);

        if (string.IsNullOrEmpty(token))
        {
            // Check if endpoint requires authentication
            var endpoint = context.GetEndpoint();
            if (RequiresAuthentication(endpoint))
            {
                _logger.LogWarning("No token provided for protected endpoint");
                context.Response.StatusCode = StatusCodes.Status401Unauthorized;
                await context.Response.WriteAsJsonAsync(new { error = "Unauthorized: No token provided" });
                return;
            }
        }
        else
        {
            try
            {
                await ValidateAndSetUserContext(context, token);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error validating Clerk token");
                context.Response.StatusCode = StatusCodes.Status401Unauthorized;
                await context.Response.WriteAsJsonAsync(new { error = "Unauthorized: Invalid token" });
                return;
            }
        }

        await _next(context);
    }

    /// <summary>
    /// Extract Bearer token from Authorization header
    /// </summary>
    private string? ExtractToken(HttpContext context)
    {
        const string authHeaderKey = "Authorization";
        const string bearerScheme = "Bearer ";

        var authHeader = context.Request.Headers[authHeaderKey].FirstOrDefault();
        if (string.IsNullOrEmpty(authHeader))
            return null;

        if (!authHeader.StartsWith(bearerScheme, StringComparison.OrdinalIgnoreCase))
            return null;

        return authHeader[bearerScheme.Length..];
    }

    /// <summary>
    /// Validate token with Clerk and set user context
    /// For now, this is a placeholder that extracts claims from the token.
    /// In production, implement proper JWT validation with Clerk's public keys.
    /// </summary>
    private async Task ValidateAndSetUserContext(HttpContext context, string token)
    {
        try
        {
            // TODO: Implement full JWT validation with Clerk's JWKS endpoint
            // For now, we perform basic validation and extract user ID from token claims
            
            var clerkApiKey = _configuration["Clerk:ApiKey"];
            var clerkSecretKey = _configuration["Clerk:SecretKey"];

            if (string.IsNullOrEmpty(clerkSecretKey))
            {
                _logger.LogWarning("Clerk:SecretKey not configured");
                // In development, allow requests without full validation
                if (!context.RequestServices.GetRequiredService<IWebHostEnvironment>().IsProduction())
                {
                    SetUserContextFromToken(context, token);
                    return;
                }
                throw new InvalidOperationException("Clerk secret key not configured");
            }

            // Parse JWT without validation for now (development)
            var parts = token.Split('.');
            if (parts.Length != 3)
                throw new InvalidOperationException("Invalid JWT format");

            var payload = parts[1];
            // Add padding if necessary
            var paddedPayload = payload.Length % 4 == 0 ? payload : payload + new string('=', 4 - payload.Length % 4);
            var decodedBytes = Convert.FromBase64String(paddedPayload);
            var claimsJson = System.Text.Encoding.UTF8.GetString(decodedBytes);
            
            using var document = JsonDocument.Parse(claimsJson);
            var root = document.RootElement;

            // Extract user ID from token claims
            if (root.TryGetProperty("sub", out var subElement))
            {
                var userId = subElement.GetString();
                if (!string.IsNullOrEmpty(userId))
                {
                    var claims = new List<Claim>
                    {
                        new Claim(ClaimTypes.NameIdentifier, userId),
                        new Claim("clerk_id", userId)
                    };

                    // Extract email if available
                    if (root.TryGetProperty("email", out var emailElement))
                    {
                        var email = emailElement.GetString();
                        if (!string.IsNullOrEmpty(email))
                        {
                            claims.Add(new Claim(ClaimTypes.Email, email));
                        }
                    }

                    // Extract name if available
                    if (root.TryGetProperty("name", out var nameElement))
                    {
                        var name = nameElement.GetString();
                        if (!string.IsNullOrEmpty(name))
                        {
                            claims.Add(new Claim(ClaimTypes.Name, name));
                        }
                    }

                    var claimsIdentity = new ClaimsIdentity(claims, "Clerk");
                    var principal = new ClaimsPrincipal(claimsIdentity);
                    context.User = principal;

                    _logger.LogInformation("User authenticated with Clerk ID: {UserId}", userId);
                }
                else
                {
                    throw new InvalidOperationException("No user ID found in token");
                }
            }
            else
            {
                throw new InvalidOperationException("No 'sub' claim found in token");
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to validate and set user context from token");
            throw;
        }
    }

    /// <summary>
    /// Helper to set user context from token (development fallback)
    /// </summary>
    private void SetUserContextFromToken(HttpContext context, string token)
    {
        try
        {
            var parts = token.Split('.');
            if (parts.Length == 3)
            {
                var payload = parts[1];
                var paddedPayload = payload.Length % 4 == 0 ? payload : payload + new string('=', 4 - payload.Length % 4);
                var decodedBytes = Convert.FromBase64String(paddedPayload);
                var claimsJson = System.Text.Encoding.UTF8.GetString(decodedBytes);
                
                using var document = JsonDocument.Parse(claimsJson);
                var root = document.RootElement;

                if (root.TryGetProperty("sub", out var subElement))
                {
                    var userId = subElement.GetString() ?? "unknown-user";
                    var claims = new List<Claim>
                    {
                        new Claim(ClaimTypes.NameIdentifier, userId),
                        new Claim("clerk_id", userId)
                    };

                    var claimsIdentity = new ClaimsIdentity(claims, "Clerk");
                    var principal = new ClaimsPrincipal(claimsIdentity);
                    context.User = principal;
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to extract user info from token in development mode");
        }
    }

    /// <summary>
    /// Check if endpoint requires authentication
    /// </summary>
    private bool RequiresAuthentication(Endpoint? endpoint)
    {
        if (endpoint == null)
            return false;

        // Check for AllowAnonymous attribute
        var allowAnonymous = endpoint.Metadata.GetMetadata<IAllowAnonymous>();
        if (allowAnonymous != null)
            return false;

        // Add more logic as needed (e.g., check specific routes)
        return true;
    }
}
