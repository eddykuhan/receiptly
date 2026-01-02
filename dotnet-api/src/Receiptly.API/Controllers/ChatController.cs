using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Receiptly.Core.Interfaces;
using System.Security.Claims;

namespace Receiptly.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ChatController : ControllerBase
{
    private readonly IChatService _chatService;
    private readonly ILogger<ChatController> _logger;

    public ChatController(
        IChatService chatService,
        ILogger<ChatController> logger)
    {
        _chatService = chatService;
        _logger = logger;
    }

    /// <summary>
    /// Ask AI a question about prices and grocery shopping
    /// </summary>
    /// <param name="request">The chat request containing the user's question</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>AI-generated answer based on price data</returns>
    [HttpPost("ask")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status429TooManyRequests)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    public async Task<ActionResult<ChatResponse>> AskQuestion(
        [FromBody] ChatRequest request,
        CancellationToken cancellationToken)
    {
        try
        {
            // Extract user ID from JWT claims
            var userId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value 
                ?? User.FindFirst("sub")?.Value 
                ?? "anonymous";

            _logger.LogInformation("Processing chat question for user {UserId}", userId);

            if (string.IsNullOrWhiteSpace(request.Question))
            {
                return BadRequest(new { error = "Question cannot be empty" });
            }

            if (request.Question.Length > 500)
            {
                return BadRequest(new { error = "Question is too long (max 500 characters)" });
            }

            var answer = await _chatService.AskQuestionAsync(
                userId, 
                request.Question, 
                cancellationToken);

            return Ok(new ChatResponse
            {
                Answer = answer,
                Timestamp = DateTime.UtcNow
            });
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Chat request cancelled");
            return StatusCode(499, new { error = "Request cancelled" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing chat question");
            return StatusCode(500, new { error = "An error occurred while processing your question" });
        }
    }

    /// <summary>
    /// Request model for chat questions
    /// </summary>
    public class ChatRequest
    {
        /// <summary>
        /// The user's question (max 500 characters)
        /// </summary>
        public string Question { get; set; } = string.Empty;
    }

    /// <summary>
    /// Response model for chat answers
    /// </summary>
    public class ChatResponse
    {
        /// <summary>
        /// AI-generated answer
        /// </summary>
        public string Answer { get; set; } = string.Empty;

        /// <summary>
        /// Timestamp of the response
        /// </summary>
        public DateTime Timestamp { get; set; }
    }
}
