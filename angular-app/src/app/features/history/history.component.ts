import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ReceiptService } from '../../core/services/receipt.service';
import { Receipt } from '../../core/models/receipt.model';
import { MyrPipe } from '../../core/pipes/myr.pipe';

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    MyrPipe,
  ],
  templateUrl: './history.component.html',
  styleUrl: './history.component.scss'
})
export class HistoryComponent implements OnInit {
  private receiptService = inject(ReceiptService);

  allReceipts = signal<Receipt[]>([]);
  filteredReceipts = signal<Receipt[]>([]);
  isLoading = signal(true);
  searchQuery = signal('');
  selectedFilter = signal<'all' | 'week' | 'month'>('all');

  ngOnInit() {
    this.loadReceipts();
  }

  loadReceipts() {
    this.isLoading.set(true);
    this.receiptService.receipts$.subscribe(receipts => {
      const sorted = [...receipts].sort((a, b) =>
        new Date(b.purchaseDate).getTime() - new Date(a.purchaseDate).getTime()
      );
      this.allReceipts.set(sorted);
      this.applyFilters();
      this.isLoading.set(false);
    });
  }

  onSearchChange(query: string) {
    this.searchQuery.set(query.toLowerCase());
    this.applyFilters();
  }

  onFilterChange(filter: 'all' | 'week' | 'month') {
    this.selectedFilter.set(filter);
    this.applyFilters();
  }

  async deleteReceipt(receipt: Receipt) {
    if (confirm(`Delete receipt from ${receipt.storeName}?`)) {
      try {
        await this.receiptService.deleteReceipt(receipt.id);
      } catch (error) {
        console.error('Error deleting receipt:', error);
      }
    }
  }

  private applyFilters() {
    let filtered = this.allReceipts();

    // Apply time filter
    if (this.selectedFilter() !== 'all') {
      const now = new Date();
      const cutoffDate = new Date();
      if (this.selectedFilter() === 'week') {
        cutoffDate.setDate(now.getDate() - 7);
      } else {
        cutoffDate.setMonth(now.getMonth() - 1);
      }
      filtered = filtered.filter(r => new Date(r.purchaseDate) >= cutoffDate);
    }

    // Apply search filter
    const query = this.searchQuery();
    if (query) {
      filtered = filtered.filter(r =>
        r.storeName.toLowerCase().includes(query) ||
        r.storeAddress?.toLowerCase().includes(query) ||
        r.items.some(item => item.name.toLowerCase().includes(query))
      );
    }

    this.filteredReceipts.set(filtered);
  }

  getTotalAmount(receipt: Receipt): number {
    return receipt.totalAmount || 0;
  }

  getItemCount(receipt: Receipt): number {
    return receipt.items.length;
  }

  getTotalSpent(): number {
    return this.filteredReceipts().reduce((sum, r) => sum + this.getTotalAmount(r), 0);
  }
}
