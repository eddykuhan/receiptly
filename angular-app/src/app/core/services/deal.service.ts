import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';

export interface Deal {
    id: string;
    productName: string;
    price: number;
    originalPrice?: number;
    storeName: string;
    storeAddress: string;
    distance: number; // km
    imageUrl: string;
    expiresAt?: Date;
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
                price: 5.90,
                originalPrice: 7.50,
                storeName: 'Tesco',
                storeAddress: 'Bangsar Shopping Centre',
                distance: 1.2,
                imageUrl: 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=300&fit=crop'
            },
            {
                id: '2',
                productName: 'White Bread',
                price: 2.50,
                originalPrice: 3.20,
                storeName: 'Jaya Grocer',
                storeAddress: 'Publika',
                distance: 2.1,
                imageUrl: 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=300&fit=crop'
            },
            {
                id: '3',
                productName: 'Eggs (10pcs)',
                price: 4.80,
                originalPrice: 6.00,
                storeName: 'Village Grocer',
                storeAddress: 'Bangsar Village',
                distance: 0.8,
                imageUrl: 'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400&h=300&fit=crop'
            },
            {
                id: '4',
                productName: 'Chicken Breast 1kg',
                price: 12.90,
                originalPrice: 15.50,
                storeName: 'AEON',
                storeAddress: 'Mid Valley',
                distance: 3.5,
                imageUrl: 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400&h=300&fit=crop'
            },
            {
                id: '5',
                productName: 'Rice 5kg',
                price: 18.50,
                originalPrice: 22.00,
                storeName: 'Giant',
                storeAddress: 'Kota Damansara',
                distance: 4.2,
                imageUrl: 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop'
            },
            {
                id: '6',
                productName: 'Cooking Oil 2L',
                price: 9.90,
                originalPrice: 12.50,
                storeName: 'Mydin',
                storeAddress: 'USJ',
                distance: 5.0,
                imageUrl: 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400&h=300&fit=crop'
            }
        ];

        return of(mockDeals);
    }

    /**
     * Calculate discount percentage
     */
    getDiscountPercentage(deal: Deal): number {
        if (!deal.originalPrice) return 0;
        return Math.round(((deal.originalPrice - deal.price) / deal.originalPrice) * 100);
    }
}
