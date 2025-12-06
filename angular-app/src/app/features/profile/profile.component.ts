import { Component, signal, ViewChild, ElementRef, inject, AfterViewInit, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { ReceiptService } from '../../core/services/receipt.service';
import { ClerkAuthService } from '../../core/services/clerk-auth.service';
import { MyrPipe } from '../../core/pipes/myr.pipe';

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
    imports: [CommonModule, FormsModule, RouterModule, MyrPipe],
    templateUrl: './profile.component.html',
    styleUrl: './profile.component.scss'
})
export class ProfileComponent implements OnInit {
    // State
    receipts = signal<any[]>([]);
    isLoading = signal(true);
    private receiptService = inject(ReceiptService);
    private authService = inject(ClerkAuthService);

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
        const current = this.profile();
        const newTheme = current.preferences.theme === 'light' ? 'dark' : 'light';
        this.profile.update(p => ({
            ...p,
            preferences: { ...p.preferences, theme: newTheme }
        }));
        // In production, apply theme to document and save to backend
    }

    signOut() {
        if (confirm('Are you sure you want to sign out?')) {
            // Use Clerk's sign out when available
            // this.clerkService.signOut();
            alert('Signed out successfully');
        }
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
                    avatar: clerkUser.imageUrl || undefined
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

    initCharts() {
        if (this.receipts().length > 0) {
            this.initSpendingChart();
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
                    borderRadius: 4,
                    barThickness: 12
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { display: false },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    getMemberDuration(): string {
        // Mock member since date for now
        const memberSince = new Date('2024-01-01');
        const months = Math.floor(
            (new Date().getTime() - memberSince.getTime()) / (1000 * 60 * 60 * 24 * 30)
        );
        if (months < 1) return 'Less than a month';
        if (months === 1) return '1 month';
        if (months < 12) return `${months} months`;
        const years = Math.floor(months / 12);
        return years === 1 ? '1 year' : `${years} years`;
    }
}
