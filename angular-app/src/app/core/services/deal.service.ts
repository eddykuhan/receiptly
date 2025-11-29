import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';

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

@Injectable({
    providedIn: 'root'
})
export class DealService {
    /**
     * Get hot deals near a location
     * @param lat Latitude (optional, for future use)
     * @param lng Longitude (optional, for future use)
     * @returns Observable of deals
     */
    getHotDeals(lat?: number, lng?: number): Observable<Deal[]> {
        // Mock data - replace with real API call in Phase 2
        const mockDeals: Deal[] = [
            {
                id: '1',
                productName: 'Fresh Milk 1L',
                lowestPrice: 5.90,
                averagePrice: 7.20,
                storeName: 'Tesco',
                storeAddress: 'Bangsar Shopping Centre',
                distance: 1.2,
                imageUrl: 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=300&fit=crop',
                lastSeenDate: new Date('2025-11-28')
            },
            {
                id: '2',
                productName: 'White Bread',
                lowestPrice: 2.50,
                averagePrice: 3.10,
                storeName: 'Jaya Grocer',
                storeAddress: 'Publika',
                distance: 2.1,
                imageUrl: 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=300&fit=crop',
                lastSeenDate: new Date('2025-11-27')
            },
            {
                id: '3',
                productName: 'Eggs (10pcs)',
                lowestPrice: 4.80,
                averagePrice: 5.50,
                storeName: 'Village Grocer',
                storeAddress: 'Bangsar Village',
                distance: 0.8,
                imageUrl: 'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400&h=300&fit=crop',
                lastSeenDate: new Date('2025-11-29')
            },
            {
                id: '4',
                productName: 'Chicken Breast 1kg',
                lowestPrice: 12.90,
                averagePrice: 14.80,
                storeName: 'AEON',
                storeAddress: 'Mid Valley',
                distance: 3.5,
                imageUrl: 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400&h=300&fit=crop',
                lastSeenDate: new Date('2025-11-26')
            },
            {
                id: '5',
                productName: 'Rice 5kg',
                lowestPrice: 18.50,
                averagePrice: 21.00,
                storeName: 'Giant',
                storeAddress: 'Kota Damansara',
                distance: 4.2,
                imageUrl: 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop',
                lastSeenDate: new Date('2025-11-25')
            },
            {
                id: '6',
                productName: 'Cooking Oil 2L',
                lowestPrice: 9.90,
                averagePrice: 11.50,
                storeName: 'Mydin',
                storeAddress: 'USJ',
                distance: 5.0,
                imageUrl: 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400&h=300&fit=crop',
                lastSeenDate: new Date('2025-11-24')
            }
        ];

        return of(mockDeals);
    }

    /**
     * Calculate how much cheaper the lowest price is vs average
     */
    getSavingsAmount(deal: Deal): number {
        return deal.averagePrice - deal.lowestPrice;
    }
}
