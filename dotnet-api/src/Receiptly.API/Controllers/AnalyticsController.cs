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

    /// <summary>
    /// Returns price history for a specific product over time.
    /// </summary>
    [HttpGet("price-history")]
    [ProducesResponseType(typeof(PriceHistoryResponseDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<PriceHistoryResponseDto>> GetPriceHistory(
        [FromQuery] string userId,
        [FromQuery] string canonicalName,
        [FromQuery] int days = 30,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(userId))
        {
            return BadRequest(new { error = "userId is required" });
        }

        if (string.IsNullOrWhiteSpace(canonicalName))
        {
            return BadRequest(new { error = "canonicalName is required" });
        }

        if (days <= 0 || days > 365)
        {
            return BadRequest(new { error = "days must be between 1 and 365" });
        }

        _logger.LogInformation(
            "Price history request for user {UserId}, product {Product}, days {Days}",
            userId,
            canonicalName,
            days);

        var result = await _purchaseAnalyticsService.GetPriceHistoryAsync(
            userId,
            canonicalName,
            days,
            cancellationToken);

        var response = new PriceHistoryResponseDto
        {
            CanonicalName = result.CanonicalName,
            PricePoints = result.PricePoints.Select(p => new PriceHistoryPointDto
            {
                PurchaseDate = p.PurchaseDate,
                UnitPrice = p.UnitPrice,
                StoreName = p.StoreName,
                ItemId = p.ItemId
            }).ToList(),
            Statistics = new PriceStatisticsDto
            {
                MinPrice = result.Statistics.MinPrice,
                MaxPrice = result.Statistics.MaxPrice,
                AveragePrice = result.Statistics.AveragePrice,
                CurrentPrice = result.Statistics.CurrentPrice,
                CheapestStore = result.Statistics.CheapestStore,
                MostExpensiveStore = result.Statistics.MostExpensiveStore
            }
        };

        return Ok(response);
    }

    /// <summary>
    /// Returns a savings report showing potential savings by shopping at different stores.
    /// </summary>
    [HttpGet("savings-report")]
    [ProducesResponseType(typeof(SavingsReportResponseDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<SavingsReportResponseDto>> GetSavingsReport(
        [FromQuery] string userId,
        [FromQuery] int days = 7,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(userId))
        {
            return BadRequest(new { error = "userId is required" });
        }

        if (days <= 0 || days > 365)
        {
            return BadRequest(new { error = "days must be between 1 and 365" });
        }

        _logger.LogInformation(
            "Savings report request for user {UserId}, days {Days}",
            userId,
            days);

        var result = await _purchaseAnalyticsService.GetSavingsReportAsync(
            userId,
            days,
            cancellationToken);

        var response = new SavingsReportResponseDto
        {
            TotalSpent = result.TotalSpent,
            PotentialSavings = result.PotentialSavings,
            SavingsPercentage = result.SavingsPercentage,
            StartDate = result.StartDate,
            EndDate = result.EndDate,
            Opportunities = result.Opportunities.Select(o => new SavingsOpportunityDto
            {
                CanonicalName = o.CanonicalName,
                PurchasedAt = o.PurchasedAt,
                PaidPrice = o.PaidPrice,
                CheaperAt = o.CheaperAt,
                CheaperPrice = o.CheaperPrice,
                PotentialSaving = o.PotentialSaving,
                Quantity = o.Quantity,
                PurchaseDate = o.PurchaseDate
            }).ToList()
        };

        return Ok(response);
    }

    /// <summary>
    /// Returns store comparison statistics for user's purchases.
    /// </summary>
    [HttpGet("store-comparison")]
    [ProducesResponseType(typeof(StoreComparisonResponseDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<StoreComparisonResponseDto>> GetStoreComparison(
        [FromQuery] string userId,
        [FromQuery] int days = 30,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(userId))
        {
            return BadRequest(new { error = "userId is required" });
        }

        if (days <= 0 || days > 365)
        {
            return BadRequest(new { error = "days must be between 1 and 365" });
        }

        _logger.LogInformation(
            "Store comparison request for user {UserId}, days {Days}",
            userId,
            days);

        var result = await _purchaseAnalyticsService.GetStoreComparisonAsync(
            userId,
            days,
            cancellationToken);

        var response = new StoreComparisonResponseDto
        {
            StartDate = result.StartDate,
            EndDate = result.EndDate,
            TotalPurchases = result.TotalPurchases,
            TotalSpent = result.TotalSpent,
            Stores = result.Stores.Select(s => new StoreStatsDto
            {
                StoreName = s.StoreName,
                PurchaseCount = s.PurchaseCount,
                TotalSpent = s.TotalSpent,
                AverageTransactionValue = s.AverageTransactionValue,
                PriceIndex = s.PriceIndex,
                UniqueItemsCount = s.UniqueItemsCount,
                Latitude = s.Latitude.HasValue ? (decimal)s.Latitude.Value : null,
                Longitude = s.Longitude.HasValue ? (decimal)s.Longitude.Value : null,
                TopItems = s.TopItems
            }).ToList()
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

