namespace Receiptly.API.DTOs;

public class SavingsReportResponseDto
{
    public decimal TotalSpent { get; set; }
    public decimal PotentialSavings { get; set; }
    public decimal SavingsPercentage { get; set; }
    public List<SavingsOpportunityDto> Opportunities { get; set; } = new();
    public DateTime StartDate { get; set; }
    public DateTime EndDate { get; set; }
}

public class SavingsOpportunityDto
{
    public string CanonicalName { get; set; } = string.Empty;
    public string PurchasedAt { get; set; } = string.Empty;
    public decimal PaidPrice { get; set; }
    public string CheaperAt { get; set; } = string.Empty;
    public decimal CheaperPrice { get; set; }
    public decimal PotentialSaving { get; set; }
    public int Quantity { get; set; }
    public DateTime PurchaseDate { get; set; }
}
