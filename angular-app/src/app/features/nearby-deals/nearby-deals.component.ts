import { Component, signal, inject, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { DealService, Deal } from '../../core/services/deal.service';
import { LocationService } from '../../core/services/location.service';
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

    deals = signal<Deal[]>([]);
    isLoading = signal(true);
    userLocation = computed(() => this.locationService.userLocation());
    radius = 5; // 5km radius

    ngOnInit() {
        // Location is already requested during splash screen
        this.loadNearbyDeals();
    }

    loadNearbyDeals() {
        this.isLoading.set(true);
        const location = this.userLocation();

        this.dealService.getHotDeals(location?.lat, location?.lon).subscribe({
            next: (deals) => {
                // Filter deals within 5km if location is available
                if (location) {
                    this.deals.set(deals.filter(deal => deal.distance <= this.radius));
                } else {
                    this.deals.set(deals);
                }
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
