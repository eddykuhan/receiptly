import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

interface Milestone {
    count: number;
    label: string;
    icon: string;
    unlocked: boolean;
}

@Component({
    selector: 'app-rewards',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './rewards.component.html',
    styleUrl: './rewards.component.scss'
})
export class RewardsComponent {
    // Mock data - in production, fetch from backend
    receiptCount = signal(73); // Demo: 73 out of 100
    voucherCode = 'TNG-CHEAP-2024-X7Y9Z'; // Revealed at 100 receipts

    // Computed properties
    progress = computed(() => Math.min((this.receiptCount() / 100) * 100, 100));
    remaining = computed(() => Math.max(100 - this.receiptCount(), 0));
    isComplete = computed(() => this.receiptCount() >= 100);

    milestones = computed<Milestone[]>(() => {
        const count = this.receiptCount();
        return [
            { count: 25, label: 'Bronze', icon: 'workspace_premium', unlocked: count >= 25 },
            { count: 50, label: 'Silver', icon: 'military_tech', unlocked: count >= 50 },
            { count: 75, label: 'Gold', icon: 'emoji_events', unlocked: count >= 75 },
            { count: 100, label: 'Diamond', icon: 'stars', unlocked: count >= 100 }
        ];
    });

    voucherRevealed = signal(false);
    showCopiedMessage = signal(false);

    revealVoucher() {
        if (this.isComplete()) {
            this.voucherRevealed.set(true);
        }
    }

    copyVoucherCode() {
        navigator.clipboard.writeText(this.voucherCode);
        this.showCopiedMessage.set(true);
        setTimeout(() => this.showCopiedMessage.set(false), 2000);
    }

    // Demo function to test completion state
    setReceiptCount(count: number) {
        this.receiptCount.set(count);
        if (count >= 100) {
            this.voucherRevealed.set(true);
        }
    }
}
