import { Component, OnInit, OnDestroy, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import * as L from 'leaflet';
import { firstValueFrom } from 'rxjs';
import { PriceMapService, StoreWithPrice } from './price-map.service';
import { MyrPipe } from '../../core/pipes/myr.pipe';
import { TimeAgoPipe } from '../../core/pipes/time-ago.pipe';

@Component({
    selector: 'app-price-map',
    standalone: true,
    imports: [CommonModule, FormsModule, MyrPipe, TimeAgoPipe],
    templateUrl: './price-map.component.html',
    styleUrl: './price-map.component.scss'
})
export class PriceMapComponent implements OnInit, OnDestroy {
    private map?: L.Map;
    private markers: L.Marker[] = [];
    private userMarker?: L.Marker;

    searchQuery = signal('');
    searchResults = signal<StoreWithPrice[]>([]);
    selectedStore = signal<StoreWithPrice | null>(null);
    productSuggestions = signal<string[]>([]);
    showSuggestions = signal(false);
    userLocation = signal<{ lat: number; lon: number } | null>(null);
    isLoading = signal(false);
    errorMessage = signal<string | null>(null);

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
        this.getUserLocation();
        this.loadProductSuggestions();

        // Check for search query params
        this.route.queryParams.subscribe(params => {
            if (params['q']) {
                this.searchQuery.set(params['q']);
                // Small delay to ensure map is ready
                setTimeout(() => this.performSearch(), 500);
            }
        });
    }

    ngOnDestroy() {
        this.map?.remove();
    }

    private initMap() {
        // Center on Kuala Lumpur
        this.map = L.map('map').setView([3.1390, 101.6869], 11);

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

    private getUserLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.userLocation.set({
                        lat: position.coords.latitude,
                        lon: position.coords.longitude
                    });

                    // Add user location marker and center map
                    if (this.map) {
                        const blueIcon = L.icon({
                            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
                            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
                            iconSize: [25, 41],
                            iconAnchor: [12, 41],
                            popupAnchor: [1, -34],
                            shadowSize: [41, 41]
                        });

                        this.userMarker = L.marker([position.coords.latitude, position.coords.longitude], { icon: blueIcon })
                            .bindPopup('<strong>Your Location</strong>')
                            .addTo(this.map);

                        // Center map on user's location
                        this.map.setView([position.coords.latitude, position.coords.longitude], 13);
                    }
                },
                (error) => {
                    console.log('Location access denied:', error);
                }
            );
        }
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
            let results = await firstValueFrom(this.priceMapService.searchProduct(query));

            const userLoc = this.userLocation();
            if (userLoc) {
                results = this.priceMapService.addDistanceToResults(results, userLoc.lat, userLoc.lon);
            }

            this.searchResults.set(results);
            this.showSuggestions.set(false);
            this.updateMapMarkers(results);
        } catch (error) {
            console.error('Failed to fetch price map data', error);
            this.errorMessage.set('Unable to load price data. Please try again.');
            this.searchResults.set([]);
            this.clearMarkers();
        } finally {
            this.isLoading.set(false);
        }
    }

    private updateMapMarkers(results: StoreWithPrice[]) {
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
          <p class="text-xs text-gray-600">${store.address}</p>
          <p class="font-mono font-bold text-purple-600 mt-1">RM ${price.toFixed(2)}</p>
          ${result.distance ? `<p class="text-xs text-gray-500">${result.distance.toFixed(1)} km away</p>` : ''}
        </div>
      `;

            const marker = L.marker([store.latitude, store.longitude], { icon })
                .bindPopup(popupContent)
                .addTo(this.map!);

            marker.on('click', () => {
                this.selectedStore.set(result);
            });

            this.markers.push(marker);
            bounds.extend([store.latitude, store.longitude]);
        });

        // Fit map to show all markers
        if (results.length > 0) {
            this.map.fitBounds(bounds, { padding: [50, 50] });
        }
    }

    clearSearch() {
        this.searchQuery.set('');
        this.searchResults.set([]);
        this.selectedStore.set(null);
        this.showSuggestions.set(false);
        this.errorMessage.set(null);
        this.clearMarkers();

        // Reset map view to KL
        if (this.map) {
            this.map.setView([3.1390, 101.6869], 11);
        }
    }

    selectStore(store: StoreWithPrice) {
        this.selectedStore.set(store);
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
    private async loadProductSuggestions() {
        try {
            const suggestions = await firstValueFrom(this.priceMapService.getProductSuggestions());
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
