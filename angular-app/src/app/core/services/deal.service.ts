import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { GeolocationUtil } from '../utils/geolocation.util';
import { APP_CONSTANTS } from '../constants/app.constants';
import { UserPreferencesService } from './user-preferences.service';

export interface Deal {
    id: string;
    productName: string;
    lowestPrice: number;
    averagePrice: number; // For comparison
    storeName: string;
    storeAddress: string;
    distance: number; // km
    latitude?: number;
    longitude?: number;
    imageUrl: string;
    lastSeenDate: Date; // When this price was last recorded
    category?: string;
}

interface PurchaseAnalyticsMetadataDto {
    storeAddress?: string;
    storePhoneNumber?: string;
    latitude?: number;
    longitude?: number;
}

interface PurchaseAnalyticsItemDto {
    itemId: string;
    receiptId: string;
    itemName: string;
    canonicalName?: string;
    unitPrice: number;
    totalPrice?: number;
    quantity: number;
    purchaseDate: string;
    storeName: string;
    category?: string;
    metadata?: PurchaseAnalyticsMetadataDto | null;
}

interface PurchaseAnalyticsResponseDto {
    items: PurchaseAnalyticsItemDto[];
}

@Injectable({
    providedIn: 'root'
})
export class DealService {
    private http = inject(HttpClient);
    private userPreferencesService = inject(UserPreferencesService);
    private readonly analyticsUrl = `${environment.apiUrl}/analytics/purchases`;

    /**
     * Get hot deals near a location
     * Fetches recent purchases and groups by product to find deals
     */
    getHotDeals(
        lat?: number,
        lng?: number,
        radius: number = 10,
        category?: string,
        storeName?: string
    ): Observable<Deal[]> {
        let params = new HttpParams()
            .set('pageSize', 100)
            .set('includeMetadata', true)
            .set('page', 1);

        if (lat && lng) {
            params = params.set('minLat', lat - radius / 111)
                .set('maxLat', lat + radius / 111)
                .set('minLng', lng - radius / (111 * Math.cos(lat * (Math.PI / 180))))
                .set('maxLng', lng + radius / (111 * Math.cos(lat * (Math.PI / 180))));
        }

        if (category) {
            params = params.set('category', category);
        }

        if (storeName) {
            params = params.set('storeName', storeName);
        }

        return this.http.get<PurchaseAnalyticsResponseDto>(this.analyticsUrl, { params }).pipe(
            map(response => this.transformToDeals(response, lat, lng))
        );
    }

    private transformToDeals(response: PurchaseAnalyticsResponseDto, userLat?: number, userLon?: number): Deal[] {
        console.log('Transform to deals - input items:', response.items.length);

        // Filter items to only include purchases from the last 7 days
        const oneWeekAgo = new Date();
        oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
        const recentItems = response.items.filter(item => {
            const purchaseDate = new Date(item.purchaseDate);
            return purchaseDate >= oneWeekAgo;
        });
        console.log('Items from last 7 days:', recentItems.length);

        // Group items by canonical name or item name
        const productMap = new Map<string, {
            prices: number[];
            stores: Map<string, {
                name: string;
                address: string;
                price: number;
                date: Date;
                latitude?: number;
                longitude?: number;
                category?: string;
            }>;
        }>();

        recentItems.forEach(item => {
            const productName = (item.canonicalName || item.itemName).trim();
            if (!productName) return;

            // Use unit price only, not total price
            const finalPrice = Number(item.unitPrice) || 0;

            if (finalPrice <= 0) return;

            const metadata = item.metadata;
            const storeAddress = metadata?.storeAddress?.trim() || 'Address unavailable';
            const latitude = metadata?.latitude;
            const longitude = metadata?.longitude;
            const storeKey = `${item.storeName}-${storeAddress}`;
            const purchaseDate = new Date(item.purchaseDate);

            if (!productMap.has(productName)) {
                productMap.set(productName, {
                    prices: [],
                    stores: new Map()
                });
            }

            const product = productMap.get(productName)!;
            product.prices.push(finalPrice);

            // Keep only the cheapest price per store
            const existingStore = product.stores.get(storeKey);
            if (!existingStore || finalPrice < existingStore.price) {
                product.stores.set(storeKey, {
                    name: item.storeName,
                    address: storeAddress,
                    price: finalPrice,
                    date: purchaseDate,
                    latitude,
                    longitude,
                    category: item.category
                });
            }
        });

        // Convert to Deal array
        let deals: Deal[] = [];
        productMap.forEach((product, productName) => {
            // Find the store with the lowest price
            let cheapestStore: any = null;
            let lowestPrice = Infinity;

            product.stores.forEach(store => {
                if (store.price < lowestPrice) {
                    lowestPrice = store.price;
                    cheapestStore = store;
                }
            });

            if (cheapestStore) {
                const averagePrice = product.prices.reduce((a, b) => a + b, 0) / product.prices.length;
                const savingsPercent = product.prices.length > 1
                    ? ((averagePrice - lowestPrice) / averagePrice) * 100
                    : 0;

                // Calculate distance if user location is available
                // Set to Infinity if we can't calculate (so it gets filtered out or sorted last)
                let distance = Infinity;
                if (userLat && userLon && cheapestStore.latitude && cheapestStore.longitude) {
                    distance = GeolocationUtil.calculateDistance(
                        userLat,
                        userLon,
                        cheapestStore.latitude,
                        cheapestStore.longitude
                    );
                }

                deals.push({
                    id: `${productName}-${cheapestStore.name}`,
                    productName,
                    lowestPrice,
                    averagePrice,
                    storeName: cheapestStore.name,
                    storeAddress: cheapestStore.address,
                    distance,
                    latitude: cheapestStore.latitude,
                    longitude: cheapestStore.longitude,
                    imageUrl: this.getProductImage(productName),
                    lastSeenDate: cheapestStore.date,
                    category: cheapestStore.category
                });
            }
        });

        // Sort by distance if location is available, otherwise by savings amount
        if (userLat && userLon) {
            // Filter deals within configured radius (customized via user preferences)
            // IMPORTANT: Only include deals that have valid store coordinates
            const MAX_RADIUS_KM = this.userPreferencesService.getSearchRadius();
            console.log(`Filtering deals with user location (${MAX_RADIUS_KM}km radius):`, { userLat, userLon, totalDeals: deals.length });
            const dealsWithDistance = deals.map(d => ({ name: d.productName, distance: d.distance, hasCoords: !!(d.latitude && d.longitude) }));
            console.log('Deals with distances:', dealsWithDistance);

            // Filter: must have coordinates AND be within radius AND not Infinity distance
            deals = deals.filter(deal => {
                const hasValidCoordinates = !!(deal.latitude && deal.longitude);
                const hasValidDistance = deal.distance !== Infinity && !isNaN(deal.distance);
                const withinRadius = deal.distance <= MAX_RADIUS_KM;
                return hasValidCoordinates && hasValidDistance && withinRadius;
            });
            console.log(`Deals within ${MAX_RADIUS_KM}km with valid coordinates:`, deals.length);
            deals.sort((a, b) => a.distance - b.distance);
        } else {
            // No user location - show ALL deals sorted by best savings
            console.log('No user location, showing all deals sorted by savings. Total deals:', deals.length);
            deals.sort((a, b) => {
                const savingsA = a.averagePrice - a.lowestPrice;
                const savingsB = b.averagePrice - b.lowestPrice;
                return savingsB - savingsA;
            });
        }

        console.log('Total deals found:', deals.length);
        console.log('Product map size:', productMap.size);

        // Return top 10 deals
        return deals.slice(0, 10);
    }

    private getProductImage(productName: string): string {
        const lowerName = productName.toLowerCase();

        // Map product categories to Unsplash images
        if (lowerName.includes('milk') || lowerName.includes('susu')) {
            return 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=300&fit=crop';
        } else if (lowerName.includes('bread') || lowerName.includes('roti')) {
            return 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=300&fit=crop';
        } else if (lowerName.includes('egg') || lowerName.includes('telur')) {
            return 'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400&h=300&fit=crop';
        } else if (lowerName.includes('chicken') || lowerName.includes('ayam')) {
            return 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400&h=300&fit=crop';
        } else if (lowerName.includes('rice') || lowerName.includes('beras')) {
            return 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop';
        } else if (lowerName.includes('oil') || lowerName.includes('minyak')) {
            return 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400&h=300&fit=crop';
        } else if (lowerName.includes('vegetable') || lowerName.includes('sayur')) {
            return 'https://images.unsplash.com/photo-1540420773420-3366772f4999?w=400&h=300&fit=crop';
        } else if (lowerName.includes('fruit') || lowerName.includes('buah')) {
            return 'https://images.unsplash.com/photo-1619566636858-adf3ef46400b?w=400&h=300&fit=crop';
        }

        // Default grocery image
        return 'https://images.unsplash.com/photo-1543168256-418811576931?w=400&h=300&fit=crop';
    }

    /**
     * Calculate how much cheaper the lowest price is vs average
     */
    getSavingsAmount(deal: Deal): number {
        return deal.averagePrice - deal.lowestPrice;
    }

    getSuggestions(query: string, lat?: number, lng?: number, radius?: number): Observable<string[]> {
        let params = new HttpParams().set('query', query);
        if (lat && lng && radius) {
            params = params.set('latitude', lat.toString())
                .set('longitude', lng.toString())
                .set('radius', radius.toString());
        }
        return this.http.get<string[]>(`${environment.apiUrl}/analytics/suggestions`, { params });
    }

    getCategories(): Observable<string[]> {
        return this.http.get<string[]>(`${environment.apiUrl}/analytics/categories`);
    }

    getNearbyStores(lat: number, lng: number, radius: number = 10): Observable<any[]> {
        const params = new HttpParams()
            .set('latitude', lat.toString())
            .set('longitude', lng.toString())
            .set('radius', radius.toString());
        return this.http.get<any[]>(`${environment.apiUrl}/analytics/stores`, { params });
    }
}
