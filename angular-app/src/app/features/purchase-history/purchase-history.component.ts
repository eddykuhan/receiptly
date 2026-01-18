import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ReceiptService } from '../../core/services/receipt.service';
import { Receipt } from '../../core/models/receipt.model';
import { MyrPipe } from '../../core/pipes/myr.pipe';

@Component({
    selector: 'app-purchase-history',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterLink, MyrPipe],
    templateUrl: './purchase-history.component.html',
    styleUrl: './purchase-history.component.scss'
})
export class PurchaseHistoryComponent implements OnInit {
    private receiptService = inject(ReceiptService);

    // State
    receipts = signal<Receipt[]>([]);
    isLoading = signal(true);
    searchQuery = signal('');

    ngOnInit() {
        this.loadReceipts();
    }

    loadReceipts() {
        this.isLoading.set(true);
        this.receiptService.receipts$.subscribe({
            next: (receipts) => {
                this.receipts.set(receipts);
                this.isLoading.set(false);
            },
            error: (err) => {
                console.error('Failed to load receipts', err);
                this.isLoading.set(false);
            }
        });
    }

    // Sort receipts by date (newest first)
    sortedReceipts = computed(() => {
        return [...this.receipts()].sort((a, b) => 
            new Date(b.purchaseDate).getTime() - new Date(a.purchaseDate).getTime()
        );
    });

    // Filter receipts by search query
    filteredReceipts = computed(() => {
        const query = this.searchQuery().toLowerCase();
        if (!query) return this.sortedReceipts();

        return this.sortedReceipts().filter(receipt => 
            receipt.storeName.toLowerCase().includes(query) ||
            receipt.items.some(item => item.name.toLowerCase().includes(query))
        );
    });

    async deleteReceipt(receipt: Receipt, event?: Event) {
        // Prevent navigation if it was a click on the swipe action
        if (event) {
            event.stopPropagation();
        }

        if (!confirm('Are you sure you want to delete this receipt?')) {
            return;
        }

        try {
            // Optimistic update
            this.receipts.update(current => current.filter(r => r.id !== receipt.id));

            await firstValueFrom(this.receiptService.deleteReceipt(receipt.id));

            console.log('Receipt deleted successfully');
        } catch (error) {
            console.error('Error deleting receipt:', error);
            // Reload on error
            this.loadReceipts();
            alert('Failed to delete receipt. Please try again.');
        }
    }

    onSearchChange(query: string) {
        this.searchQuery.set(query);
    }
}
