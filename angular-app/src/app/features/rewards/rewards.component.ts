import { Component, signal, computed, inject, OnInit, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PointsService, UserPoints, Achievement, PointTransaction } from '../../core/services/points.service';
import { FirstUploadModalComponent } from './components/first-upload-modal.component';
import { ReceiptProcessingService } from '../../core/services/receipt-processing.service';

interface PointsMilestone {
    points: number;
    label: string;
    icon: string;
    unlocked: boolean;
    reward: string;
}

interface VoucherReward {
    id: string;
    name: string;
    pointsCost: number;
    description: string;
    icon: string;
    claimed: boolean;
}

@Component({
    selector: 'app-rewards',
    standalone: true,
    imports: [CommonModule, FirstUploadModalComponent],
    templateUrl: './rewards.component.html',
    styleUrl: './rewards.component.scss'
})
export class RewardsComponent implements OnInit {
    private pointsService = inject(PointsService);
    private receiptProcessingService = inject(ReceiptProcessingService);

    // Points data
    userPoints = signal<UserPoints | null>(null);
    achievements = signal<Achievement[]>([]);
    recentTransactions = signal<PointTransaction[]>([]);
    
    // Modal state
    showFirstUploadModal = signal(false);
    
    // UI state
    showAllTransactions = signal(false);

    constructor() {
        // Listen for first upload events
        effect(() => {
            const event = this.receiptProcessingService.uploadEvents$();
            if (event?.type === 'first_upload') {
                this.showFirstUploadModal.set(true);
            }
        });
    }

    // Computed properties based on points
    pointsMilestones = computed<PointsMilestone[]>(() => {
        const points = this.userPoints()?.lifetimePoints || 0;
        return [
            { points: 100, label: 'Starter', icon: 'rocket_launch', unlocked: points >= 100, reward: 'Achievement Badge' },
            { points: 500, label: 'Regular', icon: 'workspace_premium', unlocked: points >= 500, reward: 'RM5 Voucher' },
            { points: 1000, label: 'Champion', icon: 'military_tech', unlocked: points >= 1000, reward: 'RM10 Voucher' },
            { points: 2500, label: 'Legend', icon: 'stars', unlocked: points >= 2500, reward: 'RM25 Voucher' }
        ];
    });
    
    // Available vouchers (mock data - in production, fetch from backend)
    availableVouchers = signal<VoucherReward[]>([
        {
            id: 'tng-5',
            name: 'Touch n Go RM5',
            pointsCost: 500,
            description: 'RM5 e-wallet credit',
            icon: 'payments',
            claimed: false
        },
        {
            id: 'tng-10',
            name: 'Touch n Go RM10',
            pointsCost: 1000,
            description: 'RM10 e-wallet credit',
            icon: 'account_balance_wallet',
            claimed: false
        },
        {
            id: 'grab-10',
            name: 'Grab RM10',
            pointsCost: 1000,
            description: 'RM10 Grab voucher',
            icon: 'local_taxi',
            claimed: false
        },
        {
            id: 'shopee-15',
            name: 'Shopee RM15',
            pointsCost: 1500,
            description: 'RM15 shopping voucher',
            icon: 'shopping_bag',
            claimed: false
        }
    ]);

    showCopiedMessage = signal(false);

    ngOnInit() {
        this.loadPointsData();
    }
    
    loadPointsData() {
        this.pointsService.getBalance().subscribe(points => {
            this.userPoints.set(points);
        });
        
        this.pointsService.getAchievements().subscribe(achievements => {
            this.achievements.set(achievements);
        });
        
        this.pointsService.getTransactions(10).subscribe(transactions => {
            this.recentTransactions.set(transactions);
        });
    }

    claimVoucher(voucher: VoucherReward) {
        const currentPoints = this.userPoints()?.availablePoints || 0;
        
        if (currentPoints >= voucher.pointsCost && !voucher.claimed) {
            // In production, call backend API to claim voucher
            console.log(`Claiming voucher: ${voucher.name} for ${voucher.pointsCost} points`);
            
            // Update local state (temporary - should come from backend)
            this.availableVouchers.update(vouchers => 
                vouchers.map(v => v.id === voucher.id ? { ...v, claimed: true } : v)
            );
            
            // Show success message
            alert(`Successfully claimed ${voucher.name}! Check your email for the voucher code.`);
        } else if (currentPoints < voucher.pointsCost) {
            alert(`Not enough points! You need ${voucher.pointsCost - currentPoints} more points.`);
        } else {
            alert('Voucher already claimed!');
        }
    }
    
    canClaimVoucher(voucher: VoucherReward): boolean {
        const currentPoints = this.userPoints()?.availablePoints || 0;
        return currentPoints >= voucher.pointsCost && !voucher.claimed;
    }
    
    getAchievementIcon(type: string): string {
        const icons: Record<string, string> = {
            'first_upload': 'rocket_launch',
            'five_stores': 'store',
            'three_cities': 'location_city',
            'seven_day_streak': 'local_fire_department'
        };
        return icons[type] || 'emoji_events';
    }
    
    getAchievementTitle(type: string): string {
        const titles: Record<string, string> = {
            'first_upload': 'First Upload',
            'five_stores': '5 Stores',
            'three_cities': '3 Locations',
            'seven_day_streak': '7 Day Streak'
        };
        return titles[type] || type;
    }
    
    formatDate(date: Date): string {
        const now = new Date();
        const diffMs = now.getTime() - new Date(date).getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return new Date(date).toLocaleDateString();
    }
    
    toggleShowAllTransactions() {
        this.showAllTransactions.update(value => !value);
    }

}

