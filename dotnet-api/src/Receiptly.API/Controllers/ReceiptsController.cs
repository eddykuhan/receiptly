using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Receiptly.Domain.Models;
using Receiptly.Infrastructure.Data;

namespace Receiptly.API.Controllers;

[Authorize]
[ApiController]
[Route("api/[controller]")]
public class ReceiptsController : ControllerBase
{
    private readonly ApplicationDbContext _context;

    public ReceiptsController(ApplicationDbContext context)
    {
        _context = context;
    }

    [HttpGet]
    public async Task<ActionResult<IEnumerable<Receipt>>> GetReceipts()
    {
        return await _context.Receipts
            .Include(r => r.Items)
            .ToListAsync();
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<Receipt>> GetReceipt(Guid id)
    {
        var receipt = await _context.Receipts
            .Include(r => r.Items)
            .FirstOrDefaultAsync(r => r.Id == id);

        if (receipt == null)
        {
            return NotFound();
        }

        return receipt;
    }

    [HttpPost]
    public async Task<ActionResult<Receipt>> CreateReceipt(Receipt receipt)
    {
        receipt.CreatedAt = DateTime.UtcNow;
        _context.Receipts.Add(receipt);
        await _context.SaveChangesAsync();

        return CreatedAtAction(nameof(GetReceipt), new { id = receipt.Id }, receipt);
    }

    [HttpPut("{id}")]
    public async Task<IActionResult> UpdateReceipt(Guid id, Receipt receipt)
    {
        if (id != receipt.Id)
        {
            return BadRequest();
        }

        receipt.UpdatedAt = DateTime.UtcNow;
        _context.Entry(receipt).State = EntityState.Modified;

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateConcurrencyException)
        {
            if (!await ReceiptExists(id))
            {
                return NotFound();
            }
            throw;
        }

        return NoContent();
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> DeleteReceipt(Guid id)
    {
        var receipt = await _context.Receipts.FindAsync(id);
        if (receipt == null)
        {
            return NotFound();
        }

        _context.Receipts.Remove(receipt);
        await _context.SaveChangesAsync();

        return NoContent();
    }

    private async Task<bool> ReceiptExists(Guid id)
    {
        return await _context.Receipts.AnyAsync(e => e.Id == id);
    }
}