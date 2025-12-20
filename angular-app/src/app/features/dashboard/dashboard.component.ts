import { Component, signal, inject, OnInit, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DealService, Deal } from '../../core/services/deal.service';
import { MyrPipe } from '../../core/pipes/myr.pipe';
import { TimeAgoPipe } from '../../core/pipes/time-ago.pipe';
import { PullToRefreshComponent } from '../../shared/components/pull-to-refresh/pull-to-refresh.component';
import { ReceiptService } from '../../core/services/receipt.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, MyrPipe, TimeAgoPipe, PullToRefreshComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit, OnDestroy {
  @ViewChild(PullToRefreshComponent) pullToRefresh?: PullToRefreshComponent;

  private router = inject(Router);
  private dealService = inject(DealService);
  private receiptService = inject(ReceiptService);

  // State
  isLoading = signal(false);
  deals = signal<Deal[]>([]);
  dealsLoading = signal(false);
  searchQuery = signal('');
  currentDealIndex = signal(0);
  userLocation = signal<{ lat: number; lon: number } | null>(null);

  private rotationInterval?: number;

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
    this.getUserLocation();
    this.loadHotDeals();
    this.startDealRotation();
  }

  ngOnDestroy() {
    if (this.rotationInterval) {
      clearInterval(this.rotationInterval);
    }
  }

  getUserLocation() {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          this.userLocation.set({
            lat: position.coords.latitude,
            lon: position.coords.longitude
          });
          // Reload deals with location
          this.loadHotDeals();
        },
        (error) => {
          console.log('Location access denied or unavailable, showing all deals');
        }
      );
    }
  }

  startDealRotation() {
    this.rotationInterval = window.setInterval(() => {
      const dealsCount = this.deals().length;
      if (dealsCount > 0) {
        this.currentDealIndex.set((this.currentDealIndex() + 1) % dealsCount);
      }
    }, 4000); // Change every 4 seconds
  }

  loadHotDeals() {
    this.dealsLoading.set(true);
    const location = this.userLocation();

    this.dealService.getHotDeals(location?.lat, location?.lon).subscribe({
      next: (deals) => {
        console.log('Hot deals loaded:', deals.length, deals);
        this.deals.set(deals);
        this.dealsLoading.set(false);
        // Reset to first deal when new deals load
        this.currentDealIndex.set(0);
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

  onSearch() {
    const query = this.searchQuery().trim();
    if (query) {
      this.router.navigate(['/price-map'], { queryParams: { q: query } });
    }
  }

  navigateToMap() {
    this.router.navigate(['/nearby-deals']);
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
