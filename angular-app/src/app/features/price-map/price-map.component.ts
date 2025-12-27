import { Component, OnInit, OnDestroy, signal, computed, inject, ViewChild, TemplateRef, ViewContainerRef, ApplicationRef, ChangeDetectorRef } from '@angular/core';
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
    // Map of storeId -> marker for quick lookup and selection handling
    private markersMap: Map<string, L.Marker> = new Map();
    // Currently selected store id (for visual state)
    private selectedStoreId: string | null = null;
    private userMarker?: L.Marker;

    @ViewChild('storePopupTpl', { read: TemplateRef }) private storePopupTpl?: TemplateRef<any>;
    // Keep track of created views so we can cleanup if needed
    private activePopupViews: { viewRef: any, container: HTMLElement }[] = [];
    private activePopups: { viewRef: any, container: HTMLElement, popup: any, marker?: L.Marker }[] = [];

    searchQuery = signal('');
    searchResults = signal<StoreWithPrice[]>([]);
    selectedStore = signal<StoreWithPrice | null>(null);
    // When showing a specific store's items in the side sheet
    storeDetails = signal<any | null>(null);
    previousSearchResults = signal<StoreWithPrice[] | null>(null);
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
        private route: ActivatedRoute,
        private vcr: ViewContainerRef,
        private appRef: ApplicationRef,
        private cdr: ChangeDetectorRef
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

            // Clear any active store detail view so the sheet shows all matching stores
            this.storeDetails.set(null);
            this.previousSearchResults.set(null);
            this.setSelectedMarker(null);

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
            // If a store details view is active, only show items for that store
            const activeStore = this.storeDetails();
            let itemsToShow = nearbyItems;
            if (activeStore) {
                itemsToShow = nearbyItems.filter(r => r.store.id === activeStore.id);
            }

            this.searchResults.set(itemsToShow);
            this.updateMapMarkers(itemsToShow, false); // Don't auto-zoom
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

        // Group results by store id so we only create one marker per store
        const storeMap = new Map<string, { store: any; items: StoreWithPrice[] }>();
        results.forEach(r => {
            const key = r.store.id;
            if (!storeMap.has(key)) {
                storeMap.set(key, { store: r.store, items: [r] });
            } else {
                storeMap.get(key)!.items.push(r);
            }
        });

        // Compute overall price bounds for color scaling
        const allPrices = results.map(r => r.price).sort((a, b) => a - b);
        const cheapest = allPrices[0] ?? 0;
        const mostExpensive = allPrices[allPrices.length - 1] ?? cheapest;
        const priceRange = mostExpensive - cheapest;

        // Create one marker per store
        storeMap.forEach(({ store, items }) => {
            // Use store's cheapest item price for color coding
            const storePrices = items.map(i => i.price).sort((a, b) => a - b);
            const storePrice = storePrices[0] ?? 0;

            // For now, make all markers green
            const iconColor = 'green';

            const storeInitial = (store.name && store.name.trim().length > 0) ? store.name.trim().charAt(0).toUpperCase() : 'S';
            const html = `<div class="store-marker marker-${iconColor}"><span class="store-icon material-icons">store</span><span class="store-initial">${storeInitial}</span></div>`;
            const icon = L.divIcon({ className: 'price-label-icon', html, iconSize: [42, 42], iconAnchor: [21, 42] });

            const marker = L.marker([store.latitude, store.longitude], { icon }).addTo(this.map!);

            // capture items in closure
            const itemsForStore = items.slice();
            marker.on('click', () => {
                // Visually select this marker
                this.setSelectedMarker(store.id);
                // Show this store's items in the side sheet instead of popup
                this.openStoreInSheet(marker, store, itemsForStore);
            });

            this.markers.push(marker);
            this.markersMap.set(store.id, marker);
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
        const itemsForStore = this.searchResults().filter(r => r.store.id === store.store.id);
        // If searchResults currently contains many stores, open the store items in the sheet
        this.openStoreInSheet(undefined as any, store.store, itemsForStore);
        if (this.map) {
            const currentZoom = this.map.getZoom();
            const targetZoom = Math.max(currentZoom ?? 11, 15);
            this.map.flyTo([store.store.latitude, store.store.longitude], targetZoom, {
                animate: true
            });

            // Lookup marker by store id so we can highlight it
            const marker = this.markersMap.get(store.store.id);
            if (marker) {
                // visually select
                this.setSelectedMarker(store.store.id);
                // ensure sheet shows the store items as well
                const itemsForStore = this.searchResults().filter(r => r.store.id === store.store.id);
                this.openStoreInSheet(marker, store.store, itemsForStore);
            }
        }
    }

    private openStoreInSheet(marker: L.Marker | undefined, store: any, items: StoreWithPrice[]) {
        // Save current results so we can restore when closing the store view
        this.previousSearchResults.set(this.searchResults());

        // Set search results to this store's items and open the side sheet / bottom sheet
        this.storeDetails.set(store);
        this.searchResults.set(items);
        this.selectedStore.set(items[0] ?? null);
        this.showMobileResults.set(true);
        this.isBottomSheetExpanded.set(true);

        // Center map on marker if provided
        if (marker && this.map) {
            const currentZoom = this.map.getZoom();
            const targetZoom = Math.max(currentZoom ?? 11, 15);
            this.map.flyTo(marker.getLatLng(), targetZoom, { animate: true });
        } else if (this.map && store?.latitude && store?.longitude) {
            const currentZoom = this.map.getZoom();
            const targetZoom = Math.max(currentZoom ?? 11, 15);
            this.map.flyTo([store.latitude, store.longitude], targetZoom, { animate: true });
        }
    }

    private openPopupForStore(marker: L.Marker, store: any, items: StoreWithPrice[]) {
        if (!this.storePopupTpl || !this.map) return;

        this.clearAllPopups();

        const viewRef = this.storePopupTpl.createEmbeddedView({ $implicit: store, items });
        this.appRef.attachView(viewRef);
        this.cdr.detectChanges();

        const container = document.createElement('div');
        viewRef.rootNodes.forEach((n: Node) => container.appendChild(n));

        const popup = L.popup({ maxWidth: 360, minWidth: 220, className: 'price-map-popup' })
            .setLatLng(marker.getLatLng())
            .setContent(container)
            .openOn(this.map);

        const cleanup = () => {
            try {
                this.appRef.detachView(viewRef);
                viewRef.destroy();
            } catch (e) {
                // ignore
            }
        };

        popup.on('remove', cleanup);

        this.activePopups.push({ viewRef, container, popup, marker });
    }

    private clearAllPopups() {
        while (this.activePopups.length > 0) {
            const item = this.activePopups.pop();
            try {
                item?.popup?.remove();
            } catch {}
            try {
                this.appRef.detachView(item!.viewRef);
                item!.viewRef.destroy();
            } catch {}
        }
    }

    // Visually mark a marker as selected by store id
    private setSelectedMarker(storeId: string | null) {
        // If the selected id is unchanged, do nothing
        if (this.selectedStoreId === storeId) return;

        // Clear previous selection
        if (this.selectedStoreId) {
            const prev = this.markersMap.get(this.selectedStoreId);
            if (prev) this.setMarkerSelectedVisual(prev, false);
        }

        this.selectedStoreId = storeId;

        if (storeId) {
            const marker = this.markersMap.get(storeId);
                if (marker) {
                this.setMarkerSelectedVisual(marker, true);
                try { (marker as any).bringToFront?.(); } catch {}
            }
        }
    }

    private setMarkerSelectedVisual(marker: L.Marker, selected: boolean) {
        const outerEl = (marker as any).getElement && (marker as any).getElement();
        if (!outerEl) return;
        // The divIcon HTML contains an inner element with class 'store-marker'.
        // Add/remove the selected class on that inner element so our styles apply.
        const innerEl: HTMLElement | null = outerEl.querySelector && outerEl.querySelector('.store-marker');
        const targetEl = innerEl ?? outerEl;
        if (selected) {
            targetEl.classList.add('selected');
            // also mark outer for z-index so it overlaps map tiles
            outerEl.classList.add('selected');
            (outerEl.style as any).zIndex = '9999';
        } else {
            targetEl.classList.remove('selected');
            outerEl.classList.remove('selected');
            (outerEl.style as any).zIndex = '';
        }
    }

    // Used by the popup template close button
    clearPopup() {
        // If we are viewing a store's items in the sheet, restore previous results
        if (this.storeDetails()) {
            const prev = this.previousSearchResults();
            this.searchResults.set(prev ?? []);
            this.storeDetails.set(null);
            this.previousSearchResults.set(null);
            this.isBottomSheetExpanded.set(false);
            this.showMobileResults.set(false);
            // Rebuild markers for the restored results
            if (prev && prev.length > 0) {
                this.updateMapMarkers(prev, true);
            } else {
                this.clearMarkers();
            }
            return;
        }

        this.clearAllPopups();
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


    public getRelativeTime(date: Date): string {
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
        // Close and cleanup any open popups first
        this.clearAllPopups();
        this.markers.forEach(marker => marker.remove());
        this.markers = [];
        // clear map and selection state
        this.markersMap.forEach(m => {
            try { (m as any).remove(); } catch {};
        });
        this.markersMap.clear();
        this.setSelectedMarker(null);
    }
}
