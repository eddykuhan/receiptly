import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface Deal {
    id: string;
    productName: string;
    lowestPrice: number;
    averagePrice: number; // For comparison
    storeName: string;
    storeAddress: string;
    distance: number; // km
    imageUrl: string;
    lastSeenDate: Date; // When this price was last recorded
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
export class DealService {
    private http = inject(HttpClient);
    private readonly analyticsUrl = `${environment.apiUrl}/analytics/purchases`;

    /**
     * Get hot deals near a location
     * Fetches recent purchases and groups by product to find deals
     */
    getHotDeals(lat?: number, lng?: number): Observable<Deal[]> {
        const params = new HttpParams()
            .set('pageSize', 100)
            .set('includeMetadata', true)
            .set('page', 1);

        return this.http.get<PurchaseAnalyticsResponseDto>(this.analyticsUrl, { params }).pipe(
            map(response => this.transformToDeals(response, lat, lng))
        );
    }

    private transformToDeals(response: PurchaseAnalyticsResponseDto, userLat?: number, userLon?: number): Deal[] {
        console.log('Transform to deals - input items:', response.items.length);

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
            }>;
        }>();

        response.items.forEach(item => {
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
                    longitude
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
                let distance = 0;
                if (userLat && userLon && cheapestStore.latitude && cheapestStore.longitude) {
                    distance = this.calculateDistance(
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
                    imageUrl: this.getProductImage(productName),
                    lastSeenDate: cheapestStore.date
                });
            }
        });

        // Sort by distance if location is available, otherwise by savings amount
        if (userLat && userLon) {
            // Filter deals within 10km radius
            const MAX_RADIUS_KM = 10;
            console.log('Filtering deals with user location:', { userLat, userLon, totalDeals: deals.length });
            const dealsWithDistance = deals.map(d => ({ name: d.productName, distance: d.distance }));
            console.log('Deals with distances:', dealsWithDistance);
            deals = deals.filter(deal => deal.distance <= MAX_RADIUS_KM);
            console.log('Deals within 10km:', deals.length);
            deals.sort((a, b) => a.distance - b.distance);
        } else {
            console.log('No user location, sorting by savings. Total deals:', deals.length);
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

    /**
     * Calculate distance between two points using Haversine formula
     */
    private calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
        const R = 6371; // Earth's radius in km
        const dLat = this.toRad(lat2 - lat1);
        const dLon = this.toRad(lon2 - lon1);
        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(this.toRad(lat1)) *
            Math.cos(this.toRad(lat2)) *
            Math.sin(dLon / 2) *
            Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    private toRad(degrees: number): number {
        return degrees * (Math.PI / 180);
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
}
