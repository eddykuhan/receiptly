import { Component, signal, ViewChild, ElementRef, inject, AfterViewInit, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { Chart, registerables } from 'chart.js';
import { ReceiptService } from '../../core/services/receipt.service';
import { ClerkAuthService } from '../../core/services/clerk-auth.service';
import { ThemeService } from '../../core/services/theme.service';
import { PointsService, UserPoints } from '../../core/services/points.service';
import { MyrPipe } from '../../core/pipes/myr.pipe';
import { PullToRefreshComponent } from '../../shared/components/pull-to-refresh/pull-to-refresh.component';
import { Receipt } from '../../core/models/receipt.model';

Chart.register(...registerables);

interface UserProfile {
    id: string;
    name: string;
    email: string;
    avatar?: string;
    phone?: string;
    memberSince: Date;
    authProvider: 'google' | 'apple';
    linkedAccounts: {
        google?: {
            email: string;
            linkedAt: Date;
            isPrimary: boolean;
        };
        apple?: {
            email: string;
            linkedAt: Date;
            isPrimary: boolean;
        };
    };
    stats: {
        totalReceipts: number;
        totalSaved: number;
        uniqueStores: number;
        avgReceiptValue: number;
    };
    preferences: {
        theme: 'light' | 'dark';
        language: string;
        currency: string;
        dateFormat: string;
    };
    notifications: {
        email: boolean;
        priceDrops: boolean;
        weeklySummary: boolean;
        rewards: boolean;
    };
    security: {
        twoFactorEnabled: boolean;
    };
}

@Component({
    selector: 'app-profile',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterModule, MyrPipe, PullToRefreshComponent],
    templateUrl: './profile.component.html',
    styleUrl: './profile.component.scss'
})
export class ProfileComponent implements OnInit {
    @ViewChild(PullToRefreshComponent) pullToRefresh?: PullToRefreshComponent;

    // State
    receipts = signal<Receipt[]>([]);
    isLoading = signal(true);
    userPoints = signal<UserPoints | null>(null);
    private receiptService = inject(ReceiptService);
    private authService = inject(ClerkAuthService);
    private themeService = inject(ThemeService);
    private pointsService = inject(PointsService);
    private router = inject(Router);

    // Computed Stats
    totalReceipts = computed(() => this.receipts().length);
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

    // Mock user profile data
    profile = signal<UserProfile>({
        id: 'user-123',
        name: 'John Doe',
        email: 'john.doe@gmail.com',
        avatar: undefined,
        phone: '+60 12-345 6789',
        memberSince: new Date('2024-01-15'),
        authProvider: 'google',
        linkedAccounts: {
            google: {
                email: 'john.doe@gmail.com',
                linkedAt: new Date('2024-01-15'),
                isPrimary: true
            }
        },
        stats: {
            totalReceipts: 125,
            totalSaved: 450.50,
            uniqueStores: 8,
            avgReceiptValue: 35.20
        },
        preferences: {
            theme: 'light',
            language: 'en',
            currency: 'MYR',
            dateFormat: 'DD/MM/YYYY'
        },
        notifications: {
            email: true,
            priceDrops: true,
            weeklySummary: false,
            rewards: true
        },
        security: {
            twoFactorEnabled: false
        }
    });

    editMode = signal(false);
    showSaveMessage = signal(false);

    toggleEditMode() {
        this.editMode.set(!this.editMode());
    }

    saveProfile() {
        // In production, save to backend
        this.editMode.set(false);
        this.showSaveMessage.set(true);
        setTimeout(() => this.showSaveMessage.set(false), 3000);
    }

    toggleTheme() {
        // Toggle theme using the theme service
        this.themeService.toggleTheme();

        // Update profile to match
        const newTheme = this.themeService.getCurrentTheme();
        this.profile.update(p => ({
            ...p,
            preferences: { ...p.preferences, theme: newTheme }
        }));

        // TODO: In production, save theme preference to backend
    }

    async signOut() {
        if (confirm('Are you sure you want to sign out?')) {
            try {
                await this.authService.signOut();
                console.log('User signed out successfully');
                this.router.navigate(['/sign-in']);
            } catch (error) {
                console.error('Error signing out:', error);
                alert('Failed to sign out. Please try again.');
            }
        }
    }

    navigateToPurchasedItems(event: Event) {
        event.stopPropagation(); // Prevent navigation to receipt detail
        event.preventDefault(); // Prevent default link behavior
        this.router.navigate(['/purchased-items']);
    }

    onAvatarChange(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.profile.update(p => ({ ...p, avatar: e.target?.result as string }));
            };
            reader.readAsDataURL(input.files[0]);
        }
    }

    // Chart references
    @ViewChild('spendingChart') spendingChartRef!: ElementRef;

    // Chart instances
    spendingChart: Chart | null = null;

    ngOnInit() {
        this.initializeUserProfile();
        this.loadData();
        this.loadPointsData();
        this.syncThemeWithProfile();
        
        // Subscribe to points updates
        this.pointsService.points$.subscribe(points => {
            if (points) {
                this.userPoints.set(points);
            }
        });
    }

    /**
     * Load user points data from backend
     */
    private loadPointsData() {
        this.pointsService.getBalance().subscribe({
            next: (points) => {
                this.userPoints.set(points);
            },
            error: (error) => {
                console.error('Error loading points data:', error);
            }
        });
    }

    /**
     * Sync theme service with profile preferences
     */
    private syncThemeWithProfile() {
        const currentTheme = this.themeService.getCurrentTheme();
        this.profile.update(p => ({
            ...p,
            preferences: { ...p.preferences, theme: currentTheme }
        }));
    }

    /**
     * Initialize user profile from Clerk auth service
     */
    private initializeUserProfile() {
        this.authService.user$.subscribe((clerkUser) => {
            if (clerkUser) {
                this.profile.update(p => ({
                    ...p,
                    id: clerkUser.id,
                    name: `${clerkUser.firstName || ''} ${clerkUser.lastName || ''}`.trim() || 'User',
                    email: clerkUser.email || p.email,
                    avatar: clerkUser.imageUrl || undefined,
                    memberSince: clerkUser.createdAt ? new Date(clerkUser.createdAt) : p.memberSince
                }));
            }
        });
    }

    loadData() {
        this.isLoading.set(true);
        // Trigger load
        this.receiptService.loadReceipts();

        // Subscribe to cache
        this.receiptService.receipts$.subscribe({
            next: (data: any[]) => {
                this.receipts.set(data);
                this.isLoading.set(false);
                // Initialize charts if data is available and view is ready
                if (data.length > 0) {
                    setTimeout(() => this.initCharts(), 0);
                }
            },
            error: (err: any) => {
                console.error('Failed to load receipts', err);
                this.isLoading.set(false);
            }
        });
    }

    onRefresh() {
        // Refresh receipts data
        this.receiptService.loadReceipts();

        // Complete the pull-to-refresh animation after data loads
        setTimeout(() => {
            this.pullToRefresh?.completeRefresh();
        }, 1000);
    }

    initCharts() {
        if (this.receipts().length > 0) {
            this.initSpendingChart();
        }
    }

    async deleteReceipt(receipt: any, event?: Event) {
        // Prevent navigation if it was a click on the swipe action
        if (event) {
            event.stopPropagation();
        }

        if (!confirm('Are you sure you want to delete this receipt?')) {
            // Reset swipe state if we implemented it via JS, 
            // but with CSS scroll snap, the user just scrolls back.
            // If we want to force close, we can use ViewChild references, 
            // but for now simple confirm is fine.
            return;
        }

        try {
            // Optimistic update
            const oldReceipts = this.receipts();
            this.receipts.update(current => current.filter(r => r.id !== receipt.id));

            await firstValueFrom(this.receiptService.deleteReceipt(receipt.id));

            // Recalculate stats
            // Note: Computed signals update automatically when receipts signal changes
            console.log('Receipt deleted successfully');
        } catch (error) {
            console.error('Error deleting receipt:', error);
            // Revert on error
            // This is a bit complex with signals without storing 'oldReceipts' in a wider scope 
            // or reloading. For now simple reload on error.
            this.receiptService.loadReceipts();
            alert('Failed to delete receipt. Please try again.');
        }
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

        // Get theme colors
        const style = getComputedStyle(document.body);
        const primaryColor = style.getPropertyValue('--p').trim() || '#570df8';
        // Convert to hex if it's an oklch value (simplified fallback)
        const barColor = primaryColor.startsWith('oklch') ? '#570df8' : `hsl(${primaryColor})`;

        this.spendingChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Array.from(monthlySpending.keys()),
                datasets: [{
                    label: 'Spending',
                    data: Array.from(monthlySpending.values()),
                    backgroundColor: '#570df8', // Use fixed color for now to ensure visibility
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

    getMemberDuration(): string {
        const memberSince = this.profile().memberSince;
        const now = new Date();
        const diffTime = Math.abs(now.getTime() - memberSince.getTime());
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays < 1) return 'today';
        if (diffDays === 1) return '1 day';
        if (diffDays < 7) return `${diffDays} days`;
        if (diffDays < 30) {
            const weeks = Math.floor(diffDays / 7);
            return weeks === 1 ? '1 week' : `${weeks} weeks`;
        }

        const months = Math.floor(diffDays / 30);
        if (months < 12) return months === 1 ? '1 month' : `${months} months`;

        const years = Math.floor(months / 12);
        const remainingMonths = months % 12;

        if (remainingMonths === 0) {
            return years === 1 ? '1 year' : `${years} years`;
        } else {
            const yearText = years === 1 ? '1 year' : `${years} years`;
            const monthText = remainingMonths === 1 ? '1 month' : `${remainingMonths} months`;
            return `${yearText}, ${monthText}`;
        }
    }
}
