using System.Text.RegularExpressions;
using Receiptly.Core.Interfaces;
using Receiptly.Domain.Models;

namespace Receiptly.Core.Services;

/// <summary>
/// Service for applying user corrections to receipts
/// </summary>
public class ReceiptCorrectionService : IReceiptCorrectionService
{
    private readonly IUserCorrectionRepository _userCorrectionRepository;

    public ReceiptCorrectionService(
        IUserCorrectionRepository userCorrectionRepository)
    {
        _userCorrectionRepository = userCorrectionRepository;
    }

    public async Task ApplyCorrectionsAsync(Receipt receipt, CancellationToken cancellationToken = default)
    {
        if (receipt == null)
        {
            return;
        }

        try
        {
            // Fetch all corrections for this receipt
            var corrections = await _userCorrectionRepository.GetByReceiptIdAsync(receipt.Id, cancellationToken);

            if (corrections == null || !corrections.Any())
            {
                return;
            }

            foreach (var correction in corrections)
            {
                ApplyCorrectionToReceipt(receipt, correction);
            }
        }
        catch (Exception)
        {
            // Don't throw - we want to return the receipt even if corrections fail
        }
    }

    public async Task ApplyCorrectionsAsync(List<Receipt> receipts, CancellationToken cancellationToken = default)
    {
        if (receipts == null || !receipts.Any())
        {
            return;
        }

        foreach (var receipt in receipts)
        {
            await ApplyCorrectionsAsync(receipt, cancellationToken);
        }
    }

    private void ApplyCorrectionToReceipt(Receipt receipt, UserCorrection correction)
    {
        try
        {
            switch (correction.FieldName?.ToLowerInvariant())
            {
                case "storename":
                    receipt.StoreName = correction.CorrectedValue ?? receipt.StoreName;
                    break;

                case "totalamount":
                    if (decimal.TryParse(correction.CorrectedValue, out var totalAmount))
                    {
                        receipt.TotalAmount = totalAmount;
                    }
                    break;

                case "purchasedate":
                    if (DateTime.TryParse(correction.CorrectedValue, out var purchaseDate))
                    {
                        receipt.PurchaseDate = DateTime.SpecifyKind(purchaseDate, DateTimeKind.Utc);
                    }
                    break;

                case "storeaddress":
                    receipt.StoreAddress = correction.CorrectedValue ?? receipt.StoreAddress;
                    // Also update latitude/longitude if available
                    if (correction.Latitude.HasValue && correction.Longitude.HasValue)
                    {
                        receipt.Latitude = correction.Latitude.Value;
                        receipt.Longitude = correction.Longitude.Value;
                    }
                    break;

                default:
                    // Handle item-specific corrections (e.g., "Items[0].Name", "Items[1].Price")
                    ApplyItemCorrection(receipt, correction);
                    break;
            }
        }
        catch (Exception)
        {
            // Silent fail - don't break the entire receipt fetch
        }
    }

    private void ApplyItemCorrection(Receipt receipt, UserCorrection correction)
    {
        if (string.IsNullOrEmpty(correction.FieldName) || receipt.Items == null)
        {
            return;
        }

        // Pattern: Items[0].Name or Items[1].Price
        var match = Regex.Match(correction.FieldName, @"Items\[(\d+)\]\.(Name|Price)", RegexOptions.IgnoreCase);
        if (!match.Success)
        {
            return;
        }

        if (!int.TryParse(match.Groups[1].Value, out var itemIndex))
        {
            return;
        }

        if (itemIndex < 0 || itemIndex >= receipt.Items.Count)
        {
            return;
        }

        var item = receipt.Items[itemIndex];
        var property = match.Groups[2].Value.ToLowerInvariant();

        switch (property)
        {
            case "name":
                item.Name = correction.CorrectedValue ?? item.Name;
                break;

            case "price":
                if (decimal.TryParse(correction.CorrectedValue, out var price))
                {
                    item.Price = price;
                }
                break;
        }
    }
}
