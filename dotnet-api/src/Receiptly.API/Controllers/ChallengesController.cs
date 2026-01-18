using AutoMapper;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Receiptly.Core.Interfaces;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Data;

namespace Receiptly.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ChallengesController : ControllerBase
{
    private readonly IPointsService _pointsService;
    private readonly IMapper _mapper;
    private readonly ILogger<ChallengesController> _logger;
    private readonly ApplicationDbContext _context;

    public ChallengesController(IPointsService pointsService, IMapper mapper, ILogger<ChallengesController> logger, ApplicationDbContext context)
    {
        _pointsService = pointsService;
        _mapper = mapper;
        _logger = logger;
        _context = context;
    }

    /// <summary>
    /// Get all active weekly challenges for the current week
    /// </summary>
    [HttpGet("active")]
    public async Task<ActionResult<List<WeeklyChallengeDto>>> GetActiveChallenges(CancellationToken cancellationToken)
    {
        try
        {
            var challenges = await _pointsService.GetActiveWeeklyChallengesAsync(cancellationToken);
            var challengeDtos = _mapper.Map<List<WeeklyChallengeDto>>(challenges);
            return Ok(challengeDtos);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error fetching active challenges");
            return StatusCode(500, new { error = "Failed to fetch challenges" });
        }
    }

    /// <summary>
    /// Get user's progress on all weekly challenges
    /// </summary>
    [HttpGet("progress")]
    public async Task<ActionResult<List<UserWeeklyProgressDto>>> GetUserProgress(CancellationToken cancellationToken)
    {
        try
        {
            var userId = User.FindFirst("sub")?.Value ?? User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
            if (string.IsNullOrEmpty(userId))
            {
                return BadRequest(new { error = "User ID not found in token" });
            }

            var progress = await _pointsService.GetUserWeeklyProgressAsync(userId, cancellationToken);
            var progressDtos = _mapper.Map<List<UserWeeklyProgressDto>>(progress);
            return Ok(progressDtos);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error fetching user progress");
            return StatusCode(500, new { error = "Failed to fetch user progress" });
        }
    }

    /// <summary>
    /// Get both active challenges and user's progress
    /// </summary>
    [HttpGet("dashboard")]
    public async Task<ActionResult<ChallengesDashboardDto>> GetChallengesDashboard(CancellationToken cancellationToken)
    {
        try
        {
            var userId = User.FindFirst("sub")?.Value ?? User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
            if (string.IsNullOrEmpty(userId))
            {
                return BadRequest(new { error = "User ID not found in token" });
            }

            var challenges = await _pointsService.GetActiveWeeklyChallengesAsync(cancellationToken);
            var progress = await _pointsService.GetUserWeeklyProgressAsync(userId, cancellationToken);

            var challengeDtos = _mapper.Map<List<WeeklyChallengeDto>>(challenges);
            var progressDtos = _mapper.Map<List<UserWeeklyProgressDto>>(progress);

            var dashboard = new ChallengesDashboardDto
            {
                Challenges = challengeDtos,
                UserProgress = progressDtos,
                CompletedCount = progressDtos.Count(p => p.IsCompleted),
                TotalCount = challengeDtos.Count
            };

            return Ok(dashboard);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error fetching challenges dashboard");
            return StatusCode(500, new { error = "Failed to fetch dashboard" });
        }
    }
}

/// <summary>
/// DTO for Weekly Challenge
/// </summary>
public class WeeklyChallengeDto
{
    public Guid Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string? Description { get; set; }
    public int TargetCount { get; set; }
    public int PointsReward { get; set; }
    public string ChallengeType { get; set; } = string.Empty;
    public DateTime WeekStart { get; set; }
    public DateTime WeekEnd { get; set; }
    public bool IsActive { get; set; }
}

/// <summary>
/// DTO for User's Weekly Challenge Progress
/// </summary>
public class UserWeeklyProgressDto
{
    public Guid Id { get; set; }
    public Guid ChallengeId { get; set; }
    public int CurrentCount { get; set; }
    public int TargetCount { get; set; }
    public bool IsCompleted { get; set; }
    public DateTime? CompletedAt { get; set; }
    public DateTime WeekStart { get; set; }
}

/// <summary>
/// DTO for Challenges Dashboard
/// </summary>
public class ChallengesDashboardDto
{
    public List<WeeklyChallengeDto> Challenges { get; set; } = new();
    public List<UserWeeklyProgressDto> UserProgress { get; set; } = new();
    public int CompletedCount { get; set; }
    public int TotalCount { get; set; }
}
