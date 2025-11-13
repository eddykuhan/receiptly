using Microsoft.EntityFrameworkCore;
using Receiptly.Domain.Models;

namespace Receiptly.Infrastructure.Data;

public class ApplicationDbContext : DbContext
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
        : base(options)
    {
    }

    public DbSet<Receipt> Receipts { get; set; }
    public DbSet<Item> Items { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<Receipt>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.StoreName).IsRequired();
            entity.Property(e => e.StoreAddress).IsRequired();
            entity.Property(e => e.PurchaseDate).IsRequired();
            entity.Property(e => e.TotalAmount).HasColumnType("decimal(18,2)");
            entity.Property(e => e.CreatedAt).IsRequired();
        });

        modelBuilder.Entity<Item>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Name).IsRequired();
            entity.Property(e => e.Price).HasColumnType("decimal(18,2)");
            entity.Property(e => e.Quantity).IsRequired();
            entity.Property(e => e.CreatedAt).IsRequired();

            entity.HasOne(e => e.Receipt)
                  .WithMany(e => e.Items)
                  .HasForeignKey(e => e.ReceiptId)
                  .OnDelete(DeleteBehavior.Cascade);
        });
    }
}