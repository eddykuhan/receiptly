namespace Receiptly.Core.Interfaces;

public interface IChatService
{
    /// <summary>
    /// Processes a user question and returns an AI-generated answer based on gold layer data
    /// </summary>
    /// <param name="userId">The ID of the user asking the question</param>
    /// <param name="question">The natural language question</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>AI-generated answer as a string</returns>
    Task<string> AskQuestionAsync(
        string userId, 
        string question, 
        CancellationToken cancellationToken = default);
}
