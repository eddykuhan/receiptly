using Microsoft.Extensions.Configuration;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Receiptly.Infrastructure.Services;

public class PythonOcrClient
{
    private readonly HttpClient _httpClient;
    private readonly string _ocrServiceUrl;

    public PythonOcrClient(HttpClient httpClient, IConfiguration configuration)
    {
        _httpClient = httpClient;
        _ocrServiceUrl = configuration["PythonOcr:ServiceUrl"] ?? "http://localhost:8000";
    }

    /// <summary>
    /// Send image URL to Python OCR service for analysis
    /// </summary>
    public async Task<OcrApiResponse> AnalyzeReceiptAsync(string imageUrl)
    {
        var request = new OcrRequest { ImageUrl = imageUrl };
        
        var response = await _httpClient.PostAsJsonAsync(
            $"{_ocrServiceUrl}/api/v1/ocr/analyze",
            request);

        response.EnsureSuccessStatusCode();

        var result = await response.Content.ReadFromJsonAsync<OcrApiResponse>();
        
        if (result == null || !result.Success)
        {
            throw new Exception("OCR analysis failed");
        }

        return result;
    }
}

public class OcrRequest
{
    [JsonPropertyName("image_url")]
    public string ImageUrl { get; set; } = string.Empty;
}

public class OcrApiResponse
{
    [JsonPropertyName("success")]
    public bool Success { get; set; }
    
    [JsonPropertyName("data")]
    public OcrResponse Data { get; set; } = new();
    
    [JsonPropertyName("validation")]
    public OcrValidation? Validation { get; set; }
}

public class OcrValidation
{
    [JsonPropertyName("is_valid_receipt")]
    public bool IsValidReceipt { get; set; }
    
    [JsonPropertyName("confidence")]
    public float Confidence { get; set; }
    
    [JsonPropertyName("message")]
    public string Message { get; set; } = string.Empty;
    
    [JsonPropertyName("doc_type")]
    public string DocType { get; set; } = string.Empty;
}

public class OcrResponse
{
    [JsonPropertyName("doc_type")]
    public string DocType { get; set; } = string.Empty;
    
    [JsonPropertyName("fields")]
    public Dictionary<string, OcrField> Fields { get; set; } = new();
    
    [JsonPropertyName("confidence")]
    public float Confidence { get; set; }
}

public class OcrField
{
    [JsonPropertyName("value")]
    public object? Value { get; set; }
    
    [JsonPropertyName("value_type")]
    public string? ValueType { get; set; }
    
    [JsonPropertyName("confidence")]
    public float? Confidence { get; set; }
    
    [JsonPropertyName("value_object")]
    public Dictionary<string, OcrField>? ValueObject { get; set; }
    
    [JsonPropertyName("value_array")]
    public List<OcrField>? ValueArray { get; set; }
}
