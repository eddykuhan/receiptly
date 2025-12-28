import { Component, signal, inject, OnInit, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { DealService, Deal } from '../../core/services/deal.service';
import { LocationService } from '../../core/services/location.service';
import { UserPreferencesService } from '../../core/services/user-preferences.service';
import { MyrPipe } from '../../core/pipes/myr.pipe';
import { TimeAgoPipe } from '../../core/pipes/time-ago.pipe';

@Component({
    selector: 'app-nearby-deals',
    standalone: true,
    imports: [CommonModule, RouterLink, MyrPipe, TimeAgoPipe],
    templateUrl: './nearby-deals.component.html',
    styleUrl: './nearby-deals.component.scss'
})
export class NearbyDealsComponent implements OnInit {
    private dealService = inject(DealService);
    private router = inject(Router);
    private locationService = inject(LocationService);
    private userPreferencesService = inject(UserPreferencesService);

    deals = signal<Deal[]>([]);
    isLoading = signal(true);
    userLocation = computed(() => this.locationService.userLocation());
    radius = computed(() => this.userPreferencesService.getSearchRadius()); // Dynamic radius from user preferences

    // Filters
    selectedStore = signal<string | null>(null);
    selectedCategory = signal<string | null>(null);

    // Filter options from backend
    availableCategories = signal<string[]>([]);
    availableStores = signal<any[]>([]);

    constructor() {
        // Load initial filter options
        this.loadFilterOptions();

        // Use an effect to reload deals when location or radius changes
        effect(() => {
            const location = this.userLocation();
            if (location) {
                this.loadNearbyDeals();
                this.loadNearbyStores();
            }
        }, { allowSignalWrites: true });
    }

    ngOnInit() {
        // No-op for now, logic moved to constructor/effect
    }

    private loadFilterOptions() {
        this.dealService.getCategories().subscribe(categories => {
            this.availableCategories.set(categories);
        });
    }

    private loadNearbyStores() {
        const loc = this.userLocation();
        if (!loc) return;

        const searchRadius = this.radius();
        this.dealService.getNearbyStores(loc.lat, loc.lon, searchRadius).subscribe(stores => {
            this.availableStores.set(stores);
        });
    }

    loadNearbyDeals() {
        const location = this.userLocation();
        if (!location) return;

        this.isLoading.set(true);
        const searchRadius = this.radius();

        this.dealService.getHotDeals(
            location.lat,
            location.lon,
            searchRadius,
            this.selectedCategory() || undefined,
            this.selectedStore() || undefined
        ).subscribe({
            next: (deals) => {
                this.deals.set(deals);
                this.isLoading.set(false);
            },
            error: (err) => {
                console.error('Failed to load deals:', err);
                this.isLoading.set(false);
            }
        });
    }

    getSavingsAmount(deal: Deal): number {
        return this.dealService.getSavingsAmount(deal);
    }

    getSavingsPercent(deal: Deal): number {
        if (deal.averagePrice === 0) return 0;
        return ((deal.averagePrice - deal.lowestPrice) / deal.averagePrice) * 100;
    }

    onStoreFilterChange(event: Event) {
        const value = (event.target as HTMLSelectElement).value;
        this.selectedStore.set(value === 'All Stores' || value === '' ? null : value);
        this.loadNearbyDeals();
    }

    onCategoryFilterChange(event: Event) {
        const value = (event.target as HTMLSelectElement).value;
        this.selectedCategory.set(value === 'All Categories' || value === '' ? null : value);
        this.loadNearbyDeals();
    }

    openInMaps(deal: Deal) {
        if (!this.hasLocation(deal)) return;

        // Navigate to price-map with the product name as search query
        this.router.navigate(['/price-map'], {
            queryParams: { q: deal.productName }
        });
    }

    hasLocation(deal: Deal): boolean {
        return !!(deal.latitude && deal.longitude);
    }
}
