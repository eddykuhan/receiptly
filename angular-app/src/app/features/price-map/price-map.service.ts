import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { map, shareReplay } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { APP_CONSTANTS } from '../../core/constants/app.constants';

export interface StoreLocation {
    id: string;
    name: string;
    address: string;
    latitude: number;
    longitude: number;
}

export interface StoreWithPrice {
    store: StoreLocation;
    price: number;
    lastPurchaseDate: Date;
    distance?: number;
    itemName?: string; // Add itemName for nearby items display
    status?: number; // Receipt validation status (1 = Validated)
}

export interface ProductSuggestion {
    id: string;
    name: string;
}

interface PurchaseAnalyticsMetadataDto {
    storeAddress?: string;
    storePhoneNumber?: string;
    latitude?: number;
    longitude?: number;
    status?: number;
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
    metadata?: PurchaseAnalyticsMetadataDto | null;
}

interface PurchaseAnalyticsResponseDto {
    items: PurchaseAnalyticsItemDto[];
}

@Injectable({
    providedIn: 'root'
})
export class PriceMapService {
    private http = inject(HttpClient);
    private readonly analyticsUrl = `${environment.apiUrl}/analytics/purchases`;
    private suggestions$?: Observable<string[]>;

    /**
     * Query the analytics endpoint for a given product.
     */
    searchProduct(query: { productName?: string, canonicalItemId?: string, userLat?: number, userLng?: number }): Observable<StoreWithPrice[]> {
        let params = new HttpParams()
            .set('includeMetadata', true)
            .set('pageSize', 500)
            .set('page', 1);

        if (query.productName) {
            params = params.set('productName', query.productName);
        }
        if (query.canonicalItemId) {
            params = params.set('canonicalItemId', query.canonicalItemId);
        }
        if (query.userLat !== undefined && query.userLng !== undefined) {
            params = params
                .set('userLat', query.userLat)
                .set('userLng', query.userLng);
        }

        return this.http.get<PurchaseAnalyticsResponseDto>(this.analyticsUrl, { params }).pipe(
            map(response => this.transformResponse(response))
        );
    }

    /**
     * Search for product suggestions from the backend API.
     * @param query Search query string
     * @param limit Max number of suggestions (default: 10)
     */
    searchSuggestions(query: string, lat?: number, lng?: number, radius?: number, limit: number = 10): Observable<ProductSuggestion[]> {
        if (!query || query.trim().length < 2) {
            return of([]);
        }

        let params = new HttpParams()
            .set('query', query.trim())
            .set('limit', limit);

        if (lat !== undefined && lng !== undefined && radius !== undefined && radius !== null) {
            params = params
                .set('latitude', lat)
                .set('longitude', lng)
                .set('radius', radius);
        }

        return this.http.get<ProductSuggestion[]>(`${environment.apiUrl}/analytics/suggestions`, { params });
    }

    /**
     * Get all items within specific viewport bounds
     * Grouped by store to show all available items
     */
    getItemsInBounds(bounds: { minLat: number; maxLat: number; minLng: number; maxLng: number }, days: number = 7): Observable<StoreWithPrice[]> {
        const params = new HttpParams()
            .set('pageSize', 500)
            .set('includeMetadata', true)
            .set('page', 1)
            .set('minLat', bounds.minLat)
            .set('maxLat', bounds.maxLat)
            .set('minLng', bounds.minLng)
            .set('maxLng', bounds.maxLng);

        return this.http.get<PurchaseAnalyticsResponseDto>(this.analyticsUrl, { params }).pipe(
            map(response => this.transformResponse(response))
        );
    }

    /**
     * Get all items within a certain radius of user location
     * Grouped by store to show all available items
     */
    getNearbyItems(userLat: number, userLon: number, radiusKm: number = APP_CONSTANTS.DEFAULT_SEARCH_RADIUS_KM, days: number = 7): Observable<StoreWithPrice[]> {
        const params = new HttpParams()
            .set('pageSize', 500)
            .set('includeMetadata', true)
            .set('page', 1);

        return this.http.get<PurchaseAnalyticsResponseDto>(this.analyticsUrl, { params }).pipe(
            map(response => {
                // Filter items from specified number of days
                const cutoffDate = new Date();
                cutoffDate.setDate(cutoffDate.getDate() - days);

                const itemsWithDistance = response.items
                    .filter(item => {
                        const metadata = item.metadata;
                        const latitude = metadata?.latitude;
                        const longitude = metadata?.longitude;
                        const purchaseDate = new Date(item.purchaseDate);

                        // Must have coordinates and be within specified days
                        if (!latitude || !longitude || purchaseDate < cutoffDate) {
                            return false;
                        }

                        // Calculate distance
                        const distance = this.calculateDistance(userLat, userLon, latitude, longitude);
                        return distance <= radiusKm;
                    })
                    .map(item => {
                        const metadata = item.metadata!;
                        const distance = this.calculateDistance(
                            userLat,
                            userLon,
                            metadata.latitude!,
                            metadata.longitude!
                        );

                        return {
                            item,
                            distance,
                            metadata
                        };
                    });

                // Group by store and item to get lowest price per item per store
                const storeItemMap = new Map<string, StoreWithPrice & { itemName: string }>();

                itemsWithDistance.forEach(({ item, distance, metadata }) => {
                    const storeAddress = metadata.storeAddress?.trim() || 'Address unavailable';
                    const storeId = metadata.storePhoneNumber ?? `${item.storeName}-${storeAddress}`;
                    const itemName = (item.canonicalName || item.itemName).trim();
                    const purchaseDate = new Date(item.purchaseDate);
                    // Include purchase date in key to show all unique dates
                    const dateKey = purchaseDate.toISOString();
                    const key = `${storeId}-${itemName}-${dateKey}`;
                    const finalPrice = Number(item.unitPrice) || 0;

                    if (finalPrice <= 0) return;

                    const existing = storeItemMap.get(key);
                    if (!existing || finalPrice < existing.price) {
                        storeItemMap.set(key, {
                            store: {
                                id: storeId,
                                name: item.storeName,
                                address: storeAddress,
                                latitude: metadata.latitude!,
                                longitude: metadata.longitude!
                            },
                            price: finalPrice,
                            lastPurchaseDate: purchaseDate,
                            distance,
                            itemName
                        });
                    }
                });

                return Array.from(storeItemMap.values()).sort((a, b) => (a.distance ?? 0) - (b.distance ?? 0));
            })
        );
    }

    /**
     * Add distance data based on the user's location.
     */
    addDistanceToResults(results: StoreWithPrice[], userLat: number, userLon: number): StoreWithPrice[] {
        return results.map(result => ({
            ...result,
            distance: this.calculateDistance(userLat, userLon, result.store.latitude, result.store.longitude)
        }));
    }

    private transformResponse(response: PurchaseAnalyticsResponseDto): StoreWithPrice[] {
        const storeMap = new Map<string, StoreWithPrice>();

        response.items.forEach(item => {    
            const metadata = item.metadata;
            const latitude = metadata?.latitude;
            const longitude = metadata?.longitude;
            const storeAddress = metadata?.storeAddress?.trim();
            const purchaseDate = new Date(item.purchaseDate);

            // Filter by location only
            if (latitude == null || longitude == null) {
                return;
            }

            const storeId =
                metadata?.storePhoneNumber ??
                (storeAddress ? `${item.storeName}-${storeAddress}` : item.receiptId);
            // Include purchase date in key to show all unique dates
            const dateKey = purchaseDate.toISOString();
            const key = `${storeId}-${dateKey}`;

            // Use unit price only, not total price
            const finalPrice = Number(item.unitPrice) || 0;

            const storeLocation: StoreLocation = {
                id: key,
                name: item.storeName,
                address: storeAddress ?? 'Address unavailable',
                latitude,
                longitude
            };
            const itemName = (item.canonicalName || item.itemName || '').trim();

            const existing = storeMap.get(key);
            if (!existing) {
                storeMap.set(key, {
                    store: storeLocation,
                    price: finalPrice,
                    lastPurchaseDate: purchaseDate,
                    itemName: itemName || undefined,
                    status: metadata?.status
                });
            } else {
                // If same store and date, take minimum price
                const updatedPrice = Math.min(existing.price, finalPrice);

                storeMap.set(key, {
                    store: storeLocation,
                    price: updatedPrice,
                    lastPurchaseDate: purchaseDate,
                    distance: existing.distance,
                    itemName: existing.itemName || itemName || undefined,
                    status: metadata?.status
                });
            }
        });

        return Array.from(storeMap.values()).sort((a, b) => a.price - b.price);
    }

    private calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
        const R = 6371;
        const dLat = this.toRad(lat2 - lat1);
        const dLon = this.toRad(lon2 - lon1);
        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(this.toRad(lat1)) * Math.cos(this.toRad(lat2)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    private toRad(degrees: number): number {
        return degrees * (Math.PI / 180);
    }
}

