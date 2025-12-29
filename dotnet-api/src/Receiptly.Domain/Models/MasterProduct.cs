using System;
using Pgvector;

namespace Receiptly.Domain.Models;

public class MasterProduct
{
    public Guid Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Category { get; set; }
    public string? Brand { get; set; }
    public string? Size { get; set; }
    public string? Source { get; set; }
    public Vector? Embedding { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}
