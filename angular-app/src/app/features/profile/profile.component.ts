import { Component, signal, ViewChild, inject, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ReceiptService } from '../../core/services/receipt.service';
import { ClerkAuthService } from '../../core/services/clerk-auth.service';
import { ThemeService } from '../../core/services/theme.service';
import { PointsService, UserPoints } from '../../core/services/points.service';
import { UserPreferencesService } from '../../core/services/user-preferences.service';
import { PushNotificationService } from '../../core/services/push-notification.service';
import { MyrPipe } from '../../core/pipes/myr.pipe';
import { PullToRefreshComponent } from '../../shared/components/pull-to-refresh/pull-to-refresh.component';
import { Receipt } from '../../core/models/receipt.model';

interface UserProfile {
    id: string;
    name: string;
    email: string;
    avatar?: string;
    phone?: string;
    memberSince: Date;
    preferences: {
        theme: 'light' | 'dark';
        searchRadiusKm: number;
    };
}

@Component({
    selector: 'app-profile',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterModule, MyrPipe, PullToRefreshComponent],
    templateUrl: './profile.component.html',
    styleUrl: './profile.component.scss',
    changeDetection: ChangeDetectionStrategy.OnPush
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
    private userPreferencesService = inject(UserPreferencesService);
    private pushNotificationService = inject(PushNotificationService);
    private router = inject(Router);

    // Notification state
    notificationState = this.pushNotificationService.notificationState;

    // User profile - initialized from Clerk auth service
    profile = signal<UserProfile>({
        id: '',
        name: '',
        email: '',
        memberSince: new Date(),
        preferences: {
            theme: 'light',
            searchRadiusKm: 10
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

        // Update preferences service
        this.userPreferencesService.updateTheme(newTheme);
    }

    updateSearchRadius(event: Event) {
        const input = event.target as HTMLInputElement;
        const radiusKm = parseFloat(input.value);
        
        if (radiusKm >= 10 && radiusKm <= 100) {
            // Check if value actually changed to avoid unnecessary updates
            const currentRadius = this.profile().preferences.searchRadiusKm;
            if (currentRadius !== radiusKm) {
                // Update profile
                this.profile.update(p => ({
                    ...p,
                    preferences: { ...p.preferences, searchRadiusKm: radiusKm }
                }));
                
                // Update preferences service - this will save to localStorage and make it available immediately
                this.userPreferencesService.updateSearchRadius(radiusKm);
                
                console.log(`Search radius updated to ${radiusKm}km`);
            }
        }
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

    async toggleNotifications() {
        const state = this.notificationState();
        
        try {
            if (state.permission === 'default') {
                // Request permission
                console.log('Requesting notification permission...');
                const granted = await this.pushNotificationService.requestPermission();
                if (granted) {
                    await this.pushNotificationService.subscribe();
                    console.log('Notifications enabled and persisted to localStorage');
                } else {
                    console.log('Notification permission denied');
                }
            } else if (state.permission === 'granted') {
                // Toggle subscription
                if (state.subscribed) {
                    await this.pushNotificationService.unsubscribe();
                    console.log('Notifications disabled and persisted to localStorage');
                } else {
                    await this.pushNotificationService.subscribe();
                    console.log('Notifications enabled and persisted to localStorage');
                }
            }
        } catch (error) {
            console.error('Error toggling notifications:', error);
            alert('Failed to update notification settings. Please try again.');
        }
    }

    navigateToPurchasedItems(event: Event) {
        event.stopPropagation();
        event.preventDefault();
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

    ngOnInit() {
        this.initializeUserProfile();
        this.loadData();
        this.loadPointsData();
        
        // Sync theme
        const currentTheme = this.themeService.getCurrentTheme();
        this.profile.update(p => ({
            ...p,
            preferences: { ...p.preferences, theme: currentTheme }
        }));
        
        // Sync search radius
        const searchRadiusKm = this.userPreferencesService.getSearchRadius();
        this.profile.update(p => ({
            ...p,
            preferences: { ...p.preferences, searchRadiusKm }
        }));
        
        // Refresh notification state to sync with browser permissions
        this.pushNotificationService.refreshNotificationState();
        
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
                // Sort receipts by purchase date, newest first
                const sortedReceipts = [...data].sort((a, b) => {
                    const dateA = new Date(a.purchaseDate).getTime();
                    const dateB = new Date(b.purchaseDate).getTime();
                    return dateB - dateA; // Descending order (newest first)
                });
                this.receipts.set(sortedReceipts);
                this.isLoading.set(false);
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

    async deleteReceipt(receipt: any, event?: Event) {
        if (event) {
            event.stopPropagation();
        }

        if (!confirm('Are you sure you want to delete this receipt?')) {
            return;
        }

        try {
            this.receipts.update(current => current.filter(r => r.id !== receipt.id));
            await firstValueFrom(this.receiptService.deleteReceipt(receipt.id));
            console.log('Receipt deleted successfully');
        } catch (error) {
            console.error('Error deleting receipt:', error);
            this.receiptService.loadReceipts();
            alert('Failed to delete receipt. Please try again.');
        }
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
