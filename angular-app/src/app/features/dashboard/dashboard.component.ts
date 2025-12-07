import { Component, signal, inject, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DealService, Deal } from '../../core/services/deal.service';
import { MyrPipe } from '../../core/pipes/myr.pipe';
import { PullToRefreshComponent } from '../../shared/components/pull-to-refresh/pull-to-refresh.component';
import { ReceiptService } from '../../core/services/receipt.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, MyrPipe, PullToRefreshComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  @ViewChild(PullToRefreshComponent) pullToRefresh?: PullToRefreshComponent;
  
  private router = inject(Router);
  private dealService = inject(DealService);
  private receiptService = inject(ReceiptService);

  // State
  isLoading = signal(false);
  deals = signal<Deal[]>([]);
  dealsLoading = signal(false);

  // Mock data for summary stats (optional, can be removed if not needed)
  receiptCount = signal(0);
  totalSpent = signal(0);
  averagePerReceipt = signal(0);
  topStore = signal('');

  // Period selector (optional, can be removed)
  selectedPeriod = signal('month');
  periods = [
    { label: 'This Month', value: 'month' },
    { label: 'Last 3 Months', value: 'quarter' },
    { label: 'This Year', value: 'year' }
  ];

  ngOnInit() {
    this.loadHotDeals();
  }

  loadHotDeals() {
    this.dealsLoading.set(true);
    this.dealService.getHotDeals().subscribe({
      next: (deals) => {
        this.deals.set(deals);
        this.dealsLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load deals:', err);
        this.dealsLoading.set(false);
      }
    });
  }

  onRefresh() {
    // Refresh both deals and receipts
    this.loadHotDeals();
    this.receiptService.loadReceipts();
    
    // Complete the pull-to-refresh animation after data loads
    setTimeout(() => {
      this.pullToRefresh?.completeRefresh();
    }, 1000);
  }

  getSavingsAmount(deal: Deal): number {
    return this.dealService.getSavingsAmount(deal);
  }

  onSearch(query: string) {
    if (query && query.trim()) {
      this.router.navigate(['/price-map'], { queryParams: { q: query } });
    }
  }

  navigateToMap() {
    this.router.navigate(['/price-map']);
  }

  navigateToScan() {
    this.router.navigate(['/camera']);
  }

  navigateToRewards() {
    this.router.navigate(['/rewards']);
  }

  navigateToProfile() {
    this.router.navigate(['/profile']);
  }

  onPeriodChange(period: string) {
    this.selectedPeriod.set(period);
    // Logic to refresh stats if kept
  }
}
