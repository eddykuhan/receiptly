import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { map, shareReplay } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

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
     * Query the analytics endpoint for a given product name.
     */
    searchProduct(productName: string): Observable<StoreWithPrice[]> {
        const params = new HttpParams()
            .set('productName', productName)
            .set('includeMetadata', true)
            .set('pageSize', 500)
            .set('page', 1);

        return this.http.get<PurchaseAnalyticsResponseDto>(this.analyticsUrl, { params }).pipe(
            map(response => this.transformResponse(response))
        );
    }

    /**
     * Fetch cached product suggestions derived from analytics data.
     * Uses canonical names for better grouping.
     * Only includes items that have valid latitude/longitude coordinates.
     */
    getProductSuggestions(): Observable<string[]> {
        if (this.suggestions$) {
            return this.suggestions$;
        }

        const params = new HttpParams()
            .set('pageSize', 200)
            .set('includeMetadata', true); // Changed to true to get lat/long data

        this.suggestions$ = this.http
            .get<PurchaseAnalyticsResponseDto>(this.analyticsUrl, { params })
            .pipe(
                map(response => {
                    const uniqueNames = new Set(
                        response.items
                            // Filter: Only include items with valid lat/long
                            .filter(item => {
                                const metadata = item.metadata;
                                const latitude = metadata?.latitude;
                                const longitude = metadata?.longitude;
                                return latitude != null && longitude != null;
                            })
                            // Prefer canonical name over raw item name
                            .map(item => (item.canonicalName || item.itemName).trim())
                            .filter(Boolean)
                    );
                    return Array.from(uniqueNames).sort();
                }),
                shareReplay(1)
            );

        return this.suggestions$;
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

            if (latitude == null || longitude == null) {
                return;
            }

            const storeId =
                metadata?.storePhoneNumber ??
                (storeAddress ? `${item.storeName}-${storeAddress}` : item.receiptId);
            const key = storeId;

            // Use unit price only, not total price
            const finalPrice = Number(item.unitPrice) || 0;
            const purchaseDate = new Date(item.purchaseDate);

            const storeLocation: StoreLocation = {
                id: key,
                name: item.storeName,
                address: storeAddress ?? 'Address unavailable',
                latitude,
                longitude
            };

            const existing = storeMap.get(key);
            if (!existing) {
                storeMap.set(key, {
                    store: storeLocation,
                    price: finalPrice,
                    lastPurchaseDate: purchaseDate
                });
            } else {
                const updatedPrice = Math.min(existing.price, finalPrice);
                const latestPurchaseDate =
                    purchaseDate > existing.lastPurchaseDate ? purchaseDate : existing.lastPurchaseDate;

                storeMap.set(key, {
                    store: storeLocation,
                    price: updatedPrice,
                    lastPurchaseDate: latestPurchaseDate,
                    distance: existing.distance
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

