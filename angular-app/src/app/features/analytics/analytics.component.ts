import { Component, signal, ViewChild, ElementRef, inject, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { ReceiptService } from '../../core/services/receipt.service';
import { MyrPipe } from '../../core/pipes/myr.pipe';
import { Receipt } from '../../core/models/receipt.model';
import { ItemCategorizationUtil } from '../../core/utils/item-categorization.util';

Chart.register(...registerables);

@Component({
    selector: 'app-analytics',
    standalone: true,
    imports: [CommonModule, RouterModule, MyrPipe],
    templateUrl: './analytics.component.html',
    styleUrl: './analytics.component.scss'
})
export class AnalyticsComponent implements OnInit {
    @ViewChild('spendingChart') spendingChartRef!: ElementRef;
    @ViewChild('categoryChart') categoryChartRef!: ElementRef;

    // State
    receipts = signal<Receipt[]>([]);
    isLoading = signal(true);
    selectedCategoryMonth = signal<string>('all'); // 'all' or 'YYYY-MM' format
    private receiptService = inject(ReceiptService);

    // Chart instances
    spendingChart: Chart | null = null;
    categoryChart: Chart | null = null;

    // Computed Stats
    totalSpent = computed(() => this.receipts().reduce((sum, r) => sum + (r.totalAmount || 0), 0));
    uniqueStores = computed(() => new Set(this.receipts().map(r => r.storeName)).size);

    topStore = computed(() => {
        const stores: Record<string, number> = {};
        this.receipts().forEach(r => {
            stores[r.storeName] = (stores[r.storeName] || 0) + 1;
        });
        const sorted = Object.entries(stores).sort((a, b) => b[1] - a[1]);
        return sorted.length > 0 ? `${sorted[0][0]} (${sorted[0][1]} visits)` : 'None yet';
    });

    // Category breakdown
    categorySpending = computed(() => {
        const categories: Record<string, number> = {};
        const selectedMonth = this.selectedCategoryMonth();
        
        // Filter receipts by selected month if not 'all'
        let filteredReceipts = this.receipts();
        if (selectedMonth !== 'all') {
            const [year, month] = selectedMonth.split('-').map(Number);
            filteredReceipts = this.receipts().filter(r => {
                const d = new Date(r.purchaseDate);
                return d.getFullYear() === year && d.getMonth() === month - 1;
            });
        }
        
        filteredReceipts.forEach(r => {
            r.items.forEach(item => {
                const cat = ItemCategorizationUtil.categorizeItem(item);
                categories[cat] = (categories[cat] || 0) + (item.price * item.quantity);
            });
        });
        return categories;
    });

    categoryChartData = computed(() => {
        const data = this.categorySpending();
        return {
            labels: Object.keys(data),
            values: Object.values(data)
        };
    });

    // Available months for category filtering
    monthOptions = computed(() => {
        const months = new Set<string>();
        this.receipts().forEach(r => {
            const d = new Date(r.purchaseDate);
            const monthKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
            months.add(monthKey);
        });
        
        // Sort months in descending order (newest first)
        return Array.from(months).sort((a, b) => b.localeCompare(a));
    });

    // Month-over-month comparison
    monthlyComparison = computed(() => {
        const now = new Date();
        const currentMonth = this.getMonthSpending(now.getMonth(), now.getFullYear());
        const lastMonth = this.getMonthSpending(now.getMonth() - 1, now.getFullYear());
        
        const change = currentMonth - lastMonth;
        const percentChange = lastMonth > 0 ? ((change / lastMonth) * 100) : 0;
        
        return {
            current: currentMonth,
            previous: lastMonth,
            change: change,
            percentChange: percentChange,
            isIncrease: change > 0
        };
    });

    ngOnInit() {
        this.loadData();
    }

    loadData() {
        this.isLoading.set(true);
        // Trigger load
        this.receiptService.loadReceipts();

        // Subscribe to cache
        this.receiptService.receipts$.subscribe({
            next: (data: any[]) => {
                // Sort receipts by purchase date, newest first
                const sortedReceipts = [...data].sort((a, b) => {
                    const dateA = new Date(a.purchaseDate).getTime();
                    const dateB = new Date(b.purchaseDate).getTime();
                    return dateB - dateA;
                });
                this.receipts.set(sortedReceipts);
                this.isLoading.set(false);
                // Initialize charts if data is available and view is ready
                if (data.length > 0) {
                    setTimeout(() => {
                        this.initSpendingChart();
                        this.initCategoryChart();
                    }, 0);
                }
            },
            error: (err: any) => {
                console.error('Failed to load receipts', err);
                this.isLoading.set(false);
            }
        });
    }

    initSpendingChart() {
        if (!this.spendingChartRef) return;

        if (this.spendingChart) this.spendingChart.destroy();

        const ctx = this.spendingChartRef.nativeElement.getContext('2d');

        // Group by month for the last 6 months
        const monthlySpending = new Map<string, number>();
        const now = new Date();
        for (let i = 5; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            monthlySpending.set(d.toLocaleDateString('en-US', { month: 'short' }), 0);
        }

        this.receipts().forEach(r => {
            const d = new Date(r.purchaseDate);
            const key = d.toLocaleDateString('en-US', { month: 'short' });
            // Only count if it falls within the last 6 months
            if (monthlySpending.has(key)) {
                monthlySpending.set(key, (monthlySpending.get(key) || 0) + r.totalAmount);
            }
        });

        this.spendingChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Array.from(monthlySpending.keys()),
                datasets: [{
                    label: 'Spending',
                    data: Array.from(monthlySpending.values()),
                    backgroundColor: '#570df8',
                    borderRadius: 8,
                    barThickness: 'flex',
                    maxBarThickness: 32,
                    hoverBackgroundColor: '#4506cb'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: (context) => {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('en-MY', { style: 'currency', currency: 'MYR' }).format(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        display: true,
                        beginAtZero: true,
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.05)',
                        },
                        border: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 10
                            },
                            callback: (value) => {
                                if (typeof value === 'number') {
                                    return 'RM ' + (value >= 1000 ? (value / 1000).toFixed(1) + 'k' : value);
                                }
                                return value;
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        border: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 11
                            }
                        }
                    }
                },
                layout: {
                    padding: {
                        top: 10,
                        bottom: 0
                    }
                }
            }
        });
    }

    private getMonthSpending(month: number, year: number): number {
        // Handle negative months (previous year)
        if (month < 0) {
            month = 12 + month;
            year = year - 1;
        }
        
        return this.receipts()
            .filter(r => {
                const d = new Date(r.purchaseDate);
                return d.getMonth() === month && d.getFullYear() === year;
            })
            .reduce((sum, r) => sum + r.totalAmount, 0);
    }

    getMonthLabel(monthKey: string): string {
        if (monthKey === 'all') return 'All Time';
        const [year, month] = monthKey.split('-');
        const date = new Date(parseInt(year), parseInt(month) - 1);
        return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    }

    onCategoryMonthChange(monthKey: string): void {
        this.selectedCategoryMonth.set(monthKey);
        // Re-render chart with new data
        setTimeout(() => this.initCategoryChart(), 0);
    }

    initCategoryChart() {
        if (!this.categoryChartRef) return;

        if (this.categoryChart) this.categoryChart.destroy();

        const ctx = this.categoryChartRef.nativeElement.getContext('2d');
        const data = this.categoryChartData();

        // Color palette for categories
        const colors = [
            '#570df8', // primary
            '#f000b8', // secondary
            '#37cdbe', // accent
            '#ff6b6b', // red
            '#4ecdc4', // teal
            '#ffd93d', // yellow
            '#a29bfe', // purple
            '#fd79a8', // pink
        ];

        this.categoryChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: colors.slice(0, data.labels.length),
                    borderWidth: 2,
                    borderColor: '#ffffff',
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            font: {
                                size: 11
                            },
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = (context.dataset.data as number[]).reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                const formatted = new Intl.NumberFormat('en-MY', { 
                                    style: 'currency', 
                                    currency: 'MYR' 
                                }).format(value);
                                return `${label}: ${formatted} (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '65%'
            }
        });
    }
}
