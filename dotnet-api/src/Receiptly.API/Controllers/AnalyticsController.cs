using System.Linq;
using Microsoft.AspNetCore.Mvc;
using Receiptly.API.DTOs;
using Receiptly.Core.Interfaces;

namespace Receiptly.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AnalyticsController : ControllerBase
{
    private readonly IPurchaseAnalyticsService _purchaseAnalyticsService;
    private readonly ILogger<AnalyticsController> _logger;

    public AnalyticsController(
        IPurchaseAnalyticsService purchaseAnalyticsService,
        ILogger<AnalyticsController> logger)
    {
        _purchaseAnalyticsService = purchaseAnalyticsService;
        _logger = logger;
    }

    /// <summary>
    /// Returns purchased items across all users for analytics/price-map consumers.
    /// </summary>
    [HttpGet("purchases")]
    [ProducesResponseType(typeof(PurchaseAnalyticsResponseDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<PurchaseAnalyticsResponseDto>> GetPurchases(
        [FromQuery] PurchaseAnalyticsRequest request,
        CancellationToken cancellationToken)
    {
        _logger.LogInformation(
            "Analytics request received. Page: {Page}, PageSize: {Size}, IncludeMetadata: {Metadata}",
            request.Page,
            request.PageSize,
            request.IncludeMetadata);

        var query = new PurchaseAnalyticsQuery
        {
            Page = request.Page,
            PageSize = request.PageSize,
            StartDate = request.StartDate,
            EndDate = request.EndDate,
            StoreName = request.StoreName,
            ProductName = request.ProductName,
            MinLatitude = request.MinLat,
            MaxLatitude = request.MaxLat,
            MinLongitude = request.MinLng,
            MaxLongitude = request.MaxLng,
            IncludeMetadata = request.IncludeMetadata
        };

        var result = await _purchaseAnalyticsService.GetPurchasesAsync(query, cancellationToken);
        var totalPages = result.PageSize == 0
            ? 0
            : (int)Math.Ceiling(result.TotalCount / (double)result.PageSize);

        var response = new PurchaseAnalyticsResponseDto
        {
            Items = result.Items.Select(item => MapToDto(item, request.IncludeMetadata)).ToList(),
            TotalCount = result.TotalCount,
            Page = result.Page,
            PageSize = result.PageSize,
            TotalPages = totalPages,
            IncludeMetadata = request.IncludeMetadata
        };

        return Ok(response);
    }

    private static PurchaseAnalyticsItemDto MapToDto(PurchaseAnalyticsRecord record, bool includeMetadata)
    {
        return new PurchaseAnalyticsItemDto
        {
            ItemId = record.ItemId,
            ReceiptId = record.ReceiptId,
            ItemName = record.ItemName,
            Description = record.Description,
            CanonicalName = record.CanonicalName,
            UnitPrice = record.UnitPrice,
            TotalPrice = record.TotalPrice,
            Quantity = record.Quantity,
            PurchaseDate = record.PurchaseDate,
            StoreName = record.StoreName,
            Metadata = includeMetadata
                ? new PurchaseAnalyticsMetadataDto
                {
                    StoreAddress = record.StoreAddress,
                    StorePhoneNumber = record.StorePhoneNumber,
                    Latitude = record.Latitude,
                    Longitude = record.Longitude,
                    ReceiptType = record.ReceiptType,
                    TransactionId = record.TransactionId,
                    PaymentMethod = record.PaymentMethod,
                    Status = record.Status
                }
                : null
        };
    }
}

