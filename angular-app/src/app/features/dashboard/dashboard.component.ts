import { Component, signal, computed, inject, OnInit, ViewChild, ElementRef, AfterViewInit, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Chart, ChartConfiguration, registerables } from 'chart.js';
import { ReceiptService } from '../../core/services/receipt.service';
import { Receipt } from '../../core/models/receipt.model';
import { MyrPipe } from '../../core/pipes/myr.pipe';

// Register Chart.js components
Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MyrPipe,
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit, AfterViewInit {
  private receiptService = inject(ReceiptService);

  @ViewChild('spendingChart', { static: false }) spendingChartRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('storeChart', { static: false }) storeChartRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('monthlyChart', { static: false }) monthlyChartRef?: ElementRef<HTMLCanvasElement>;

  private spendingChart?: Chart;
  private storeChart?: Chart;
  private monthlyChart?: Chart;

  receipts = signal<Receipt[]>([]);
  selectedPeriod = signal<'all' | 'week' | 'month' | '3months' | 'year'>('all');
  isLoading = signal(true);
  chartsInitialized = signal(false);

  periods = [
    { value: 'all', label: 'All Time' },
    { value: 'week', label: 'This Week' },
    { value: 'month', label: 'This Month' },
    { value: '3months', label: 'Last 3 Months' },
    { value: 'year', label: 'This Year' },
  ];

  // Computed values for summary cards
  totalSpent = computed(() => {
    const filtered = this.getFilteredReceipts();
    return filtered.reduce((sum: number, r: Receipt) => sum + this.getTotalAmount(r), 0);
  });

  receiptCount = computed(() => this.getFilteredReceipts().length);

  averagePerReceipt = computed(() => {
    const count = this.receiptCount();
    return count > 0 ? this.totalSpent() / count : 0;
  });

  topStore = computed(() => {
    const filtered = this.getFilteredReceipts();
    if (filtered.length === 0) return '—';

    const storeTotals = new Map<string, number>();
    filtered.forEach((receipt: Receipt) => {
      const total = this.getTotalAmount(receipt);
      storeTotals.set(
        receipt.storeName,
        (storeTotals.get(receipt.storeName) || 0) + total
      );
    });

    let maxStore = '—';
    let maxAmount = 0;
    storeTotals.forEach((amount, store) => {
      if (amount > maxAmount) {
        maxAmount = amount;
        maxStore = store;
      }
    });

    return maxStore;
  });

  constructor() {
    // Re-render charts when period or receipts change
    effect(() => {
      const _ = this.selectedPeriod(); // Track period changes
      const __ = this.receipts().length; // Track receipt changes
      if (this.chartsInitialized()) {
        setTimeout(() => this.updateCharts(), 0);
      }
    });
  }

  ngOnInit() {
    this.receiptService.receipts$.subscribe({
      next: (receipts) => {
        this.receipts.set(receipts);
        this.isLoading.set(false);
        // Initialize charts after data is loaded
        if (this.chartsInitialized()) {
          setTimeout(() => this.initializeCharts(), 100);
        }
      },
      error: (error: Error) => {
        console.error('Error loading receipts:', error);
        this.isLoading.set(false);
      },
    });
  }

  ngAfterViewInit() {
    // Initialize charts after view is ready
    setTimeout(() => {
      this.initializeCharts();
      this.chartsInitialized.set(true);
    }, 100);
  }

  initializeCharts() {
    this.initSpendingChart();
    this.initStoreChart();
    this.initMonthlyChart();
  }

  private initSpendingChart() {
    if (!this.spendingChartRef?.nativeElement) {
      return;
    }

    const filtered = this.getFilteredReceipts();
    const dailyTotals = this.getDailyTotals(filtered);

    const config: ChartConfiguration = {
      type: 'line',
      data: {
        labels: Array.from(dailyTotals.keys()),
        datasets: [{
          label: 'Daily Spending',
          data: Array.from(dailyTotals.values()),
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99, 102, 241, 0.1)',
          fill: true,
          tension: 0.4,
          borderWidth: 3,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: '#6366f1',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#111827',
            titleColor: '#fff',
            bodyColor: '#fff',
            padding: 12,
            cornerRadius: 8,
            displayColors: false,
            callbacks: {
              label: (context) => `RM ${(context.parsed.y ?? 0).toFixed(2)}`,
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            border: {
              display: false,
            },
            grid: {
              color: '#f3f4f6',
            },
            ticks: {
              color: '#6b7280',
              font: { size: 12 },
              callback: (value) => `RM ${value}`,
            },
          },
          x: {
            border: {
              display: false,
            },
            grid: {
              display: false,
            },
            ticks: {
              color: '#6b7280',
              font: { size: 11 },
            },
          },
        },
      },
    };

    if (this.spendingChart) {
      this.spendingChart.destroy();
    }
    this.spendingChart = new Chart(this.spendingChartRef.nativeElement, config);
  }

  private initStoreChart() {
    if (!this.storeChartRef?.nativeElement) return;

    const filtered = this.getFilteredReceipts();
    const storeTotals = this.getStoreTotals(filtered);
    const topStores = Array.from(storeTotals.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    const config: ChartConfiguration = {
      type: 'pie',
      data: {
        labels: topStores.map(([store]) => store),
        datasets: [{
          data: topStores.map(([, total]) => total),
          backgroundColor: [
            '#6366f1', // Indigo
            '#10b981', // Emerald
            '#f59e0b', // Amber
            '#8b5cf6', // Purple
            '#ef4444', // Red
          ],
          borderWidth: 0,
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              padding: 16,
              color: '#6b7280',
              font: { size: 12 },
              usePointStyle: true,
              pointStyle: 'circle',
            },
          },
          tooltip: {
            backgroundColor: '#111827',
            titleColor: '#fff',
            bodyColor: '#fff',
            padding: 12,
            cornerRadius: 8,
            displayColors: true,
            callbacks: {
              label: (context) => {
                const label = context.label || '';
                const value = context.parsed || 0;
                return `${label}: RM ${value.toFixed(2)}`;
              },
            },
          },
        },
      },
    };

    if (this.storeChart) {
      this.storeChart.destroy();
    }
    this.storeChart = new Chart(this.storeChartRef.nativeElement, config);
  }

  private initMonthlyChart() {
    if (!this.monthlyChartRef?.nativeElement) return;

    const monthlyTotals = this.getMonthlyTotals();

    const config: ChartConfiguration = {
      type: 'bar',
      data: {
        labels: Array.from(monthlyTotals.keys()),
        datasets: [{
          label: 'Monthly Spending',
          data: Array.from(monthlyTotals.values()),
          backgroundColor: '#6366f1',
          borderRadius: 8,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#111827',
            titleColor: '#fff',
            bodyColor: '#fff',
            padding: 12,
            cornerRadius: 8,
            displayColors: false,
            callbacks: {
              label: (context) => `RM ${(context.parsed.y ?? 0).toFixed(2)}`,
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            border: {
              display: false,
            },
            grid: {
              color: '#f3f4f6',
            },
            ticks: {
              color: '#6b7280',
              font: { size: 12 },
              callback: (value) => `RM ${value}`,
            },
          },
          x: {
            border: {
              display: false,
            },
            grid: {
              display: false,
            },
            ticks: {
              color: '#6b7280',
              font: { size: 11 },
            },
          },
        },
      },
    };

    if (this.monthlyChart) {
      this.monthlyChart.destroy();
    }
    this.monthlyChart = new Chart(this.monthlyChartRef.nativeElement, config);
  }

  updateCharts() {
    this.initSpendingChart();
    this.initStoreChart();
    this.initMonthlyChart();
  }

  onPeriodChange(newPeriod: string) {
    this.selectedPeriod.set(newPeriod as 'all' | 'week' | 'month' | '3months' | 'year');
  }

  private getFilteredReceipts(): Receipt[] {
    const now = new Date();
    const period = this.selectedPeriod();
    const all = this.receipts();

    switch (period) {
      case 'all': {
        return all;
      }
      case 'week': {
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        return all.filter(r => new Date(r.purchaseDate) >= weekAgo);
      }
      case 'month': {
        const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        return all.filter(r => new Date(r.purchaseDate) >= monthAgo);
      }
      case '3months': {
        const threeMonthsAgo = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
        return all.filter(r => new Date(r.purchaseDate) >= threeMonthsAgo);
      }
      case 'year': {
        const yearAgo = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
        return all.filter(r => new Date(r.purchaseDate) >= yearAgo);
      }
      default:
        return all;
    }
  }

  private getDailyTotals(receipts: Receipt[]): Map<string, number> {
    const dailyTotals = new Map<string, number>();

    receipts.forEach((receipt: Receipt) => {
      const date = new Date(receipt.purchaseDate).toLocaleDateString();
      const total = this.getTotalAmount(receipt);
      dailyTotals.set(date, (dailyTotals.get(date) || 0) + total);
    });

    return new Map([...dailyTotals.entries()].sort((a, b) =>
      new Date(a[0]).getTime() - new Date(b[0]).getTime()
    ));
  }

  private getStoreTotals(receipts: Receipt[]): Map<string, number> {
    const storeTotals = new Map<string, number>();

    receipts.forEach((receipt: Receipt) => {
      const total = this.getTotalAmount(receipt);
      storeTotals.set(
        receipt.storeName,
        (storeTotals.get(receipt.storeName) || 0) + total
      );
    });

    return storeTotals;
  }

  private getMonthlyTotals(): Map<string, number> {
    const monthlyTotals = new Map<string, number>();
    const all = this.receipts();

    // Get last 6 months
    const now = new Date();
    for (let i = 5; i >= 0; i--) {
      const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const key = date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
      monthlyTotals.set(key, 0);
    }

    all.forEach((receipt: Receipt) => {
      const date = new Date(receipt.purchaseDate);
      const key = date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
      if (monthlyTotals.has(key)) {
        const total = this.getTotalAmount(receipt);
        monthlyTotals.set(key, (monthlyTotals.get(key) || 0) + total);
      }
    });

    return monthlyTotals;
  }

  private getTotalAmount(receipt: Receipt): number {
    // Use the totalAmount from the receipt (OCR data) instead of summing items
    // Items may have missing prices/quantities, but totalAmount is the authoritative value
    return receipt.totalAmount || 0;
  }
}
