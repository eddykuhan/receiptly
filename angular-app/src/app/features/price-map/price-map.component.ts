import { Component, OnInit, OnDestroy, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import * as L from 'leaflet';
import { firstValueFrom } from 'rxjs';
import { PriceMapService, StoreWithPrice } from './price-map.service';
import { MyrPipe } from '../../core/pipes/myr.pipe';
import { TimeAgoPipe } from '../../core/pipes/time-ago.pipe';
import { APP_CONSTANTS } from '../../core/constants/app.constants';
import { LocationService } from '../../core/services/location.service';
import { UserPreferencesService } from '../../core/services/user-preferences.service';

@Component({
    selector: 'app-price-map',
    standalone: true,
    imports: [CommonModule, FormsModule, MyrPipe, TimeAgoPipe],
    templateUrl: './price-map.component.html',
    styleUrl: './price-map.component.scss'
})
export class PriceMapComponent implements OnInit, OnDestroy {
    private locationService = inject(LocationService);
    private userPreferencesService = inject(UserPreferencesService);
    private map?: L.Map;
    private markers: L.Marker[] = [];
    private userMarker?: L.Marker;

    searchQuery = signal('');
    searchResults = signal<StoreWithPrice[]>([]);
    selectedStore = signal<StoreWithPrice | null>(null);
    productSuggestions = signal<string[]>([]);
    showSuggestions = signal(false);
    userLocation = computed(() => this.locationService.userLocation());
    isLoading = signal(false);
    errorMessage = signal<string | null>(null);
    isBottomSheetExpanded = signal(false);
    showMobileResults = signal(false);
    daysFilter = signal(7); // Default to 7 days
    distanceFilter = signal<number | null>(null); // null = no distance filter

    // Computed properties
    hasResults = computed(() => this.searchResults().length > 0);
    cheapestPrice = computed(() => {
        const results = this.searchResults();
        return results.length > 0 ? results[0].price : 0;
    });

    constructor(
        private priceMapService: PriceMapService,
        private route: ActivatedRoute
    ) { }

    ngOnInit() {
        this.initMap();
        // Location is already requested during splash screen
        this.addUserLocationMarker();
        this.loadProductSuggestions();

        // Set search query from params but don't auto-search
        this.route.queryParams.subscribe(params => {
            if (params['q']) {
                this.searchQuery.set(params['q']);
                // User needs to manually click search button or press enter
            }
        });
    }

    ngOnDestroy() {
        this.map?.remove();
    }

    onDaysFilterChange(days: number) {
        this.daysFilter.set(days);
        // Reload results with new filter
        if (this.searchQuery()) {
            this.performSearch();
        } else {
            this.loadNearbyItems();
        }
    }

    onDistanceFilterChange(distance: number | null) {
        this.distanceFilter.set(distance);
        // Reload results with new filter
        if (this.searchQuery()) {
            this.performSearch();
        } else {
            this.loadNearbyItems();
        }
    }

    private initMap() {
        // Get user location or default to Kuala Lumpur
        const userLoc = this.userLocation();
        const initialLat = userLoc?.lat ?? 3.1390;
        const initialLon = userLoc?.lon ?? 101.6869;
        
        this.map = L.map('map').setView([initialLat, initialLon], 11);

        // Add OpenStreetMap tiles (free, no API key needed!)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(this.map);

        // Fix for grey tiles - invalidate size after DOM is ready
        setTimeout(() => {
            this.map?.invalidateSize();
        }, 100);
    }

    private addUserLocationMarker() {
        const userLoc = this.userLocation();
        if (!userLoc || !this.map) {
            console.log('No user location available for map marker');
            return;
        }

        console.log('✅ Adding user location marker:', userLoc.lat, userLoc.lon);

        const blueIcon = L.icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        });

        this.userMarker = L.marker([userLoc.lat, userLoc.lon], { icon: blueIcon })
            .bindPopup('<strong>📍 Your Location</strong>')
            .addTo(this.map);

        // Load nearby items but don't auto-zoom to fit them
        this.loadNearbyItems();
    }

    onSearchInput(value: string) {
        this.searchQuery.set(value);
        this.showSuggestions.set(value.length > 0);
    }

    selectSuggestion(productName: string) {
        this.searchQuery.set(productName);
        this.showSuggestions.set(false);
        this.performSearch();
    }

    async performSearch() {
        const query = this.searchQuery().trim();
        if (!query) {
            this.clearSearch();
            return;
        }

        this.isLoading.set(true);
        this.errorMessage.set(null);

        try {
            let results = await firstValueFrom(this.priceMapService.searchProduct(query, this.daysFilter()));

            const userLoc = this.userLocation();
            if (userLoc) {
                results = this.priceMapService.addDistanceToResults(results, userLoc.lat, userLoc.lon);
                
                // Apply distance filter if set
                const distFilter = this.distanceFilter();
                if (distFilter !== null) {
                    results = results.filter(r => r.distance !== undefined && r.distance <= distFilter);
                }
            }

            this.searchResults.set(results);
            this.showSuggestions.set(false);
            this.updateMapMarkers(results);
            
            // Show mobile bottom sheet when search completes
            if (results.length > 0) {
                this.showMobileResults.set(true);
                this.isBottomSheetExpanded.set(true);
            }
        } catch (error) {
            console.error('Failed to fetch price map data', error);
            this.errorMessage.set('Unable to load price data. Please try again.');
            this.searchResults.set([]);
            this.clearMarkers();
        } finally {
            this.isLoading.set(false);
        }
    }

    async loadNearbyItems() {
        const userLoc = this.userLocation();
        if (!userLoc) {
            console.log('No user location available for nearby items');
            return;
        }

        this.isLoading.set(true);
        const userSearchRadius = this.userPreferencesService.getSearchRadius();
        console.log(`🔍 Loading items within ${userSearchRadius}km...`);

        try {
            const radiusKm = this.distanceFilter() ?? userSearchRadius;
            const nearbyItems = await firstValueFrom(
                this.priceMapService.getNearbyItems(userLoc.lat, userLoc.lon, radiusKm, this.daysFilter())
            );

            console.log(`✅ Found ${nearbyItems.length} items within ${radiusKm}km`);
            this.searchResults.set(nearbyItems);
            this.updateMapMarkers(nearbyItems, false); // Don't auto-zoom
        } catch (error) {
            console.error('Failed to load nearby items:', error);
            this.errorMessage.set('Unable to load nearby items.');
        } finally {
            this.isLoading.set(false);
        }
    }

    private updateMapMarkers(results: StoreWithPrice[], autoZoom: boolean = true) {
        this.clearMarkers();

        if (!this.map || results.length === 0) return;

        const bounds = L.latLngBounds([]);
        const cheapest = results[0].price;
        const mostExpensive = results[results.length - 1].price;
        const priceRange = mostExpensive - cheapest;

        results.forEach((result, index) => {
            const { store, price } = result;

            // Color code based on price (green = cheap, red = expensive)
            let iconColor = 'green';
            if (priceRange > 0) {
                const priceRatio = (price - cheapest) / priceRange;
                if (priceRatio > 0.66) {
                    iconColor = 'red';
                } else if (priceRatio > 0.33) {
                    iconColor = 'orange';
                }
            }

            // Create custom colored marker
            const icon = L.icon({
                iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${iconColor}.png`,
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            });

            const popupContent = `
        <div class="p-2">
          <h3 class="font-bold text-sm">${store.name}</h3>
          ${result.itemName ? `<p class="text-xs font-semibold text-primary">${result.itemName}</p>` : ''}
          <p class="text-xs text-gray-600">${store.address}</p>
          <p class="font-mono font-bold text-purple-600 mt-1">RM ${price.toFixed(2)}</p>
          ${result.distance ? `<p class="text-xs text-gray-500">${result.distance.toFixed(1)} km away</p>` : ''}
          <p class="text-xs text-gray-400">Updated ${this.getRelativeTime(result.lastPurchaseDate)}</p>
        </div>
      `;

            const marker = L.marker([store.latitude, store.longitude], { icon })
                .bindPopup(popupContent)
                .addTo(this.map!);

            marker.on('click', () => {
                this.selectedStore.set(result);
                // Don't show mobile bottom sheet on marker click
            });

            this.markers.push(marker);
            bounds.extend([store.latitude, store.longitude]);
        });

        // Only fit bounds if autoZoom is true (e.g., when user searches)
        if (autoZoom && results.length > 0) {
            this.map.fitBounds(bounds, { padding: [50, 50] });
        }
    }

    clearSearch() {
        this.searchQuery.set('');
        this.searchResults.set([]);
        this.selectedStore.set(null);
        this.showSuggestions.set(false);
        this.errorMessage.set(null);
        this.showMobileResults.set(false);
        this.isBottomSheetExpanded.set(false);
        this.clearMarkers();

        // Reset map view to user location or default to KL
        if (this.map) {
            const userLoc = this.userLocation();
            if (userLoc) {
                this.map.setView([userLoc.lat, userLoc.lon], 13, { animate: true });
            } else {
                this.map.setView([3.1390, 101.6869], 11);
            }
        }
    }

    selectStore(store: StoreWithPrice) {
        this.selectedStore.set(store);
        this.showMobileResults.set(true);
        this.isBottomSheetExpanded.set(true);
        if (this.map) {
            this.map.setView([store.store.latitude, store.store.longitude], 14, {
                animate: true
            });

            // Open the popup for this store
            const marker = this.markers.find(m => {
                const latLng = m.getLatLng();
                return latLng.lat === store.store.latitude && latLng.lng === store.store.longitude;
            });
            marker?.openPopup();
        }
    }

    getFilteredSuggestions() {
        const query = this.searchQuery().toLowerCase();
        if (!query) return [];
        return this.productSuggestions()
            .filter(name => name.toLowerCase().includes(query))
            .slice(0, 5);
    }

    toggleBottomSheet() {
        this.isBottomSheetExpanded.update(expanded => !expanded);
    }


    private getRelativeTime(date: Date): string {
        const now = new Date();
        const diffMs = now.getTime() - new Date(date).getTime();
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        const diffWeeks = Math.floor(diffDays / 7);

        if (diffSecs < 60) return 'just now';
        if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
        return `${diffWeeks} week${diffWeeks > 1 ? 's' : ''} ago`;
    }

    private async loadProductSuggestions() {
        try {
            const suggestions = await firstValueFrom(this.priceMapService.getProductSuggestions(60));
            this.productSuggestions.set(suggestions);
        } catch (error) {
            console.warn('Unable to load product suggestions', error);
        }
    }

    private clearMarkers() {
        this.markers.forEach(marker => marker.remove());
        this.markers = [];
    }
}
