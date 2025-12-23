using Microsoft.AspNetCore.Mvc;
using Receiptly.Core.Interfaces;
using System.Security.Claims;

namespace Receiptly.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class PointsController : ControllerBase
{
    private readonly IPointsService _pointsService;
    private readonly ILogger<PointsController> _logger;

    public PointsController(IPointsService pointsService, ILogger<PointsController> logger)
    {
        _pointsService = pointsService;
        _logger = logger;
    }

    /// <summary>
    /// Get current user's points balance
    /// </summary>
    [HttpGet("balance")]
    public async Task<IActionResult> GetBalance(CancellationToken cancellationToken)
    {
        try
        {
            var userId = GetAuthenticatedUserId();

            var userPoints = await _pointsService.GetUserPointsAsync(userId, cancellationToken);
            
            return Ok(new
            {
                userId = userPoints.UserId,
                totalPoints = userPoints.TotalPoints,
                availablePoints = userPoints.AvailablePoints,
                lifetimePoints = userPoints.LifetimePoints,
                lastUpdated = userPoints.UpdatedAt
            });
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Get balance request cancelled");
            return StatusCode(499, new { error = "Request cancelled" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting user points balance");
            return StatusCode(500, new { error = "Failed to get points balance" });
        }
    }

    /// <summary>
    /// Get current user's point transaction history
    /// </summary>
    [HttpGet("transactions")]
    public async Task<IActionResult> GetTransactions(
        [FromQuery] int limit = 50, 
        CancellationToken cancellationToken = default)
    {
        try
        {
            var userId = GetAuthenticatedUserId();

            var transactions = await _pointsService.GetUserTransactionsAsync(userId, limit, cancellationToken);
            
            return Ok(transactions.Select(t => new
            {
                id = t.Id,
                points = t.Points,
                transactionType = t.TransactionType,
                description = t.Description,
                referenceId = t.ReferenceId,
                earnedAt = t.EarnedAt,
                expiresAt = t.ExpiresAt,
                isExpired = t.IsExpired
            }));
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Get transactions request cancelled");
            return StatusCode(499, new { error = "Request cancelled" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting point transactions");
            return StatusCode(500, new { error = "Failed to get transactions" });
        }
    }

    /// <summary>
    /// Get current user's achievements
    /// </summary>
    [HttpGet("achievements")]
    public async Task<IActionResult> GetAchievements(CancellationToken cancellationToken)
    {
        try
        {
            var userId = GetAuthenticatedUserId();

            var achievements = await _pointsService.GetUserAchievementsAsync(userId, cancellationToken);
            
            return Ok(achievements.Select(a => new
            {
                id = a.Id,
                achievementType = a.AchievementType,
                pointsAwarded = a.PointsAwarded,
                unlockedAt = a.UnlockedAt
            }));
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Get achievements request cancelled");
            return StatusCode(499, new { error = "Request cancelled" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting user achievements");
            return StatusCode(500, new { error = "Failed to get achievements" });
        }
    }

    private string GetAuthenticatedUserId()
    {
        var clerkUserId = User.FindFirstValue("clerk_user_id");
        if (!string.IsNullOrEmpty(clerkUserId))
        {
            return clerkUserId;
        }

        var nameIdentifier = User.FindFirstValue(ClaimTypes.NameIdentifier);
        if (!string.IsNullOrEmpty(nameIdentifier))
        {
            return nameIdentifier;
        }

        _logger.LogWarning("No authenticated user ID found, using default");
        return "default-user";
    }
}
