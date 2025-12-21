using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Receiptly.Core.Interfaces;
using Receiptly.Domain.Enums;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Data;
using Receiptly.Infrastructure.Services;

namespace Receiptly.Infrastructure.Tests;

public class PurchaseAnalyticsServiceTests
{
    [Fact]
    public async Task GetPurchasesAsync_FiltersByDateAndStore()
    {
        await using var context = CreateContext();
        var targetReceipt = new Receipt
        {
            Id = Guid.NewGuid(),
            UserId = "user-1",
            StoreName = "Fresh Mart",
            StoreAddress = "123 Main",
            PurchaseDate = DateTime.UtcNow.AddDays(-1),
            TotalAmount = 50,
            Items =
            [
                new Item
                {
                    Id = Guid.NewGuid(),
                    Name = "Apple",
                    Price = 2,
                    Quantity = 5,
                    CreatedAt = DateTime.UtcNow
                }
            ],
            CreatedAt = DateTime.UtcNow.AddDays(-2),
            Status = ReceiptStatus.Processed
        };

        var otherReceipt = new Receipt
        {
            Id = Guid.NewGuid(),
            UserId = "user-2",
            StoreName = "Old Store",
            StoreAddress = "456 Other",
            PurchaseDate = DateTime.UtcNow.AddDays(-10),
            TotalAmount = 10,
            Items =
            [
                new Item
                {
                    Id = Guid.NewGuid(),
                    Name = "Banana",
                    Price = 1,
                    Quantity = 2,
                    CreatedAt = DateTime.UtcNow
                }
            ],
            CreatedAt = DateTime.UtcNow.AddDays(-11),
            Status = ReceiptStatus.Processed
        };

        context.Receipts.AddRange(targetReceipt, otherReceipt);
        await context.SaveChangesAsync();

        var mockCorrectionService = new Mock<IReceiptCorrectionService>();
        var service = new PurchaseAnalyticsService(context, mockCorrectionService.Object, NullLogger<PurchaseAnalyticsService>.Instance);
        var query = new PurchaseAnalyticsQuery
        {
            StartDate = DateTime.UtcNow.AddDays(-2),
            StoreName = "Fresh"
        };

        var result = await service.GetPurchasesAsync(query);

        Assert.Single(result.Items);
        Assert.Equal("Fresh Mart", result.Items[0].StoreName);
        Assert.Equal("Apple", result.Items[0].ItemName);
    }

    [Fact]
    public async Task GetPurchasesAsync_EnforcesPageSizeCap()
    {
        await using var context = CreateContext();

        for (var i = 0; i < 10; i++)
        {
            var receipt = new Receipt
            {
                Id = Guid.NewGuid(),
                UserId = $"user-{i}",
                StoreName = "Bulk Store",
                StoreAddress = "789 Bulk",
                PurchaseDate = DateTime.UtcNow.AddDays(-i),
                TotalAmount = 20,
                Items =
                [
                    new Item
                    {
                        Id = Guid.NewGuid(),
                        Name = $"Item-{i}",
                        Price = 2,
                        Quantity = 2,
                        CreatedAt = DateTime.UtcNow
                    }
                ],
                CreatedAt = DateTime.UtcNow.AddDays(-i),
                Status = ReceiptStatus.Processed
            };

            context.Receipts.Add(receipt);
        }

        await context.SaveChangesAsync();

        var mockCorrectionService = new Mock<IReceiptCorrectionService>();
        var service = new PurchaseAnalyticsService(context, mockCorrectionService.Object, NullLogger<PurchaseAnalyticsService>.Instance);
        var result = await service.GetPurchasesAsync(new PurchaseAnalyticsQuery
        {
            PageSize = 1000
        });

        Assert.Equal(500, result.PageSize);
        Assert.Equal(10, result.Items.Count);
    }

    [Fact]
    public async Task GetPurchasesAsync_FiltersByProductName()
    {
        await using var context = CreateContext();

        var milkReceipt = new Receipt
        {
            Id = Guid.NewGuid(),
            UserId = "user-filter",
            StoreName = "Market One",
            StoreAddress = "Addr 1",
            PurchaseDate = DateTime.UtcNow.AddDays(-3),
            TotalAmount = 30,
            Items =
            [
                new Item
                {
                    Id = Guid.NewGuid(),
                    Name = "Organic Milk",
                    Price = 5,
                    Quantity = 2,
                    CreatedAt = DateTime.UtcNow
                }
            ],
            CreatedAt = DateTime.UtcNow.AddDays(-4),
            Status = ReceiptStatus.Processed
        };

        var breadReceipt = new Receipt
        {
            Id = Guid.NewGuid(),
            UserId = "user-filter",
            StoreName = "Market Two",
            StoreAddress = "Addr 2",
            PurchaseDate = DateTime.UtcNow.AddDays(-2),
            TotalAmount = 20,
            Items =
            [
                new Item
                {
                    Id = Guid.NewGuid(),
                    Name = "Wholegrain Bread",
                    Price = 4,
                    Quantity = 1,
                    CreatedAt = DateTime.UtcNow
                }
            ],
            CreatedAt = DateTime.UtcNow.AddDays(-3),
            Status = ReceiptStatus.Processed
        };

        context.Receipts.AddRange(milkReceipt, breadReceipt);
        await context.SaveChangesAsync();

        var mockCorrectionService = new Mock<IReceiptCorrectionService>();
        var service = new PurchaseAnalyticsService(context, mockCorrectionService.Object, NullLogger<PurchaseAnalyticsService>.Instance);
        var result = await service.GetPurchasesAsync(new PurchaseAnalyticsQuery
        {
            ProductName = "milk"
        });

        Assert.Single(result.Items);
        Assert.Equal("Organic Milk", result.Items[0].ItemName);
    }

    private static ApplicationDbContext CreateContext()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;

        return new ApplicationDbContext(options);
    }
}
