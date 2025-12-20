import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ReceiptService } from '../../core/services/receipt.service';
import { Receipt, ReceiptItem } from '../../core/models/receipt.model';
import { MyrPipe } from '../../core/pipes/myr.pipe';

interface AggregatedItem {
    name: string;
    canonicalName?: string;
    totalQuantity: number;
    averagePrice: number;
    purchaseCount: number;
    mostRecentDate: Date;
    receipts: {
        id: string;
        storeName: string;
        purchaseDate: Date;
        quantity: number;
        price: number;
    }[];
}

type SortOption = 'name' | 'quantity' | 'spent' | 'recent';

@Component({
    selector: 'app-purchased-items',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterLink, MyrPipe],
    templateUrl: './purchased-items.component.html',
    styleUrl: './purchased-items.component.scss'
})
export class PurchasedItemsComponent implements OnInit {
    private receiptService = inject(ReceiptService);

    // State
    receipts = signal<Receipt[]>([]);
    isLoading = signal(true);
    searchQuery = signal('');
    selectedSort = signal<SortOption>('recent');
    expandedItems = signal<Set<string>>(new Set());

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

    // Aggregate all items from all receipts
    aggregatedItems = computed(() => {
        const itemsMap = new Map<string, AggregatedItem>();

        this.receipts().forEach(receipt => {
            receipt.items.forEach(item => {
                // Use canonical name if available, otherwise use the item name
                const key = (item.canonicalName || item.name).toLowerCase();

                if (!itemsMap.has(key)) {
                    itemsMap.set(key, {
                        name: item.canonicalName || item.name,
                        canonicalName: item.canonicalName,
                        totalQuantity: 0,
                        averagePrice: item.price,
                        purchaseCount: 0,
                        mostRecentDate: receipt.purchaseDate,
                        receipts: []
                    });
                }

                const aggregated = itemsMap.get(key)!;
                aggregated.totalQuantity += item.quantity;
                // Update average price (simple average of all unit prices seen)
                aggregated.averagePrice = ((aggregated.averagePrice * aggregated.purchaseCount) + item.price) / (aggregated.purchaseCount + 1);
                aggregated.purchaseCount += 1;

                // Update most recent date
                if (new Date(receipt.purchaseDate) > new Date(aggregated.mostRecentDate)) {
                    aggregated.mostRecentDate = receipt.purchaseDate;
                }

                // Add receipt reference
                aggregated.receipts.push({
                    id: receipt.id,
                    storeName: receipt.storeName,
                    purchaseDate: receipt.purchaseDate,
                    quantity: item.quantity,
                    price: item.price
                });
            });
        });

        return Array.from(itemsMap.values());
    });

    // Filtered and sorted items
    filteredItems = computed(() => {
        let items = this.aggregatedItems();

        // Apply search filter
        const query = this.searchQuery().toLowerCase();
        if (query) {
            items = items.filter(item =>
                item.name.toLowerCase().includes(query)
            );
        }

        // Apply sorting
        const sort = this.selectedSort();
        items = [...items].sort((a, b) => {
            switch (sort) {
                case 'name':
                    return a.name.localeCompare(b.name);
                case 'quantity':
                    return b.totalQuantity - a.totalQuantity;
                case 'spent':
                    return b.averagePrice - a.averagePrice;
                case 'recent':
                    return new Date(b.mostRecentDate).getTime() - new Date(a.mostRecentDate).getTime();
                default:
                    return 0;
            }
        });

        return items;
    });

    onSearchChange(query: string) {
        this.searchQuery.set(query);
    }

    onSortChange(sort: SortOption) {
        this.selectedSort.set(sort);
    }

    toggleItemExpanded(itemName: string) {
        const expanded = new Set(this.expandedItems());
        if (expanded.has(itemName)) {
            expanded.delete(itemName);
        } else {
            expanded.add(itemName);
        }
        this.expandedItems.set(expanded);
    }

    isItemExpanded(itemName: string): boolean {
        return this.expandedItems().has(itemName);
    }

    getTotalItems(): number {
        return this.aggregatedItems().length;
    }

    getAveragePrice(): number {
        const items = this.aggregatedItems();
        if (items.length === 0) return 0;
        return items.reduce((sum, item) => sum + item.averagePrice, 0) / items.length;
    }
}
