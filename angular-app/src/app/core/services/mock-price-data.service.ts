import { Injectable } from '@angular/core';

export interface StoreLocation {
    id: string;
    name: string;
    address: string;
    latitude: number;
    longitude: number;
}

export interface ProductPrice {
    productName: string;
    price: number;
    purchaseDate: Date;
    storeId: string;
}

export interface StoreWithPrice {
    store: StoreLocation;
    price: number;
    lastPurchaseDate: Date;
    distance?: number;
}

@Injectable({
    providedIn: 'root'
})
export class MockPriceDataService {
    private stores: StoreLocation[] = [
        {
            id: '1',
            name: 'Tesco Ampang',
            address: 'Jalan Ampang, Kuala Lumpur',
            latitude: 3.1569,
            longitude: 101.7622
        },
        {
            id: '2',
            name: 'Giant Wangsa Maju',
            address: 'Wangsa Maju, Kuala Lumpur',
            latitude: 3.1989,
            longitude: 101.7344
        },
        {
            id: '3',
            name: 'Aeon Mid Valley',
            address: 'Mid Valley City, Kuala Lumpur',
            latitude: 3.1181,
            longitude: 101.6774
        },
        {
            id: '4',
            name: 'Mydin USJ',
            address: 'USJ, Subang Jaya',
            latitude: 3.0436,
            longitude: 101.5818
        },
        {
            id: '5',
            name: 'Lotus Cheras',
            address: 'Cheras, Kuala Lumpur',
            latitude: 3.1095,
            longitude: 101.7272
        },
        {
            id: '6',
            name: 'Village Grocer TTDI',
            address: 'TTDI, Kuala Lumpur',
            latitude: 3.1359,
            longitude: 101.6294
        },
        {
            id: '7',
            name: '99 Speedmart Kepong',
            address: 'Kepong, Kuala Lumpur',
            latitude: 3.2189,
            longitude: 101.6389
        },
        {
            id: '8',
            name: 'Jaya Grocer Bangsar',
            address: 'Bangsar, Kuala Lumpur',
            latitude: 3.1319,
            longitude: 101.6694
        }
    ];

    private productPrices: ProductPrice[] = [
        // Milk prices across stores
        { productName: 'Fresh Milk 1L', price: 5.20, purchaseDate: new Date('2024-01-15'), storeId: '1' },
        { productName: 'Fresh Milk 1L', price: 5.80, purchaseDate: new Date('2024-01-10'), storeId: '2' },
        { productName: 'Fresh Milk 1L', price: 6.50, purchaseDate: new Date('2024-01-12'), storeId: '3' },
        { productName: 'Fresh Milk 1L', price: 4.90, purchaseDate: new Date('2024-01-18'), storeId: '4' },
        { productName: 'Fresh Milk 1L', price: 5.50, purchaseDate: new Date('2024-01-14'), storeId: '5' },
        { productName: 'Fresh Milk 1L', price: 7.20, purchaseDate: new Date('2024-01-16'), storeId: '8' },

        // Bread prices
        { productName: 'White Bread', price: 2.80, purchaseDate: new Date('2024-01-16'), storeId: '1' },
        { productName: 'White Bread', price: 2.50, purchaseDate: new Date('2024-01-11'), storeId: '2' },
        { productName: 'White Bread', price: 3.20, purchaseDate: new Date('2024-01-13'), storeId: '3' },
        { productName: 'White Bread', price: 2.30, purchaseDate: new Date('2024-01-17'), storeId: '4' },
        { productName: 'White Bread', price: 2.70, purchaseDate: new Date('2024-01-15'), storeId: '7' },

        // Eggs
        { productName: 'Eggs 10pcs', price: 6.50, purchaseDate: new Date('2024-01-14'), storeId: '1' },
        { productName: 'Eggs 10pcs', price: 6.20, purchaseDate: new Date('2024-01-12'), storeId: '2' },
        { productName: 'Eggs 10pcs', price: 7.00, purchaseDate: new Date('2024-01-16'), storeId: '3' },
        { productName: 'Eggs 10pcs', price: 5.90, purchaseDate: new Date('2024-01-18'), storeId: '4' },
        { productName: 'Eggs 10pcs', price: 6.30, purchaseDate: new Date('2024-01-15'), storeId: '5' },
        { productName: 'Eggs 10pcs', price: 7.50, purchaseDate: new Date('2024-01-17'), storeId: '6' },

        // Rice
        { productName: 'Rice 5kg', price: 18.50, purchaseDate: new Date('2024-01-10'), storeId: '1' },
        { productName: 'Rice 5kg', price: 17.90, purchaseDate: new Date('2024-01-12'), storeId: '2' },
        { productName: 'Rice 5kg', price: 19.50, purchaseDate: new Date('2024-01-14'), storeId: '3' },
        { productName: 'Rice 5kg', price: 16.80, purchaseDate: new Date('2024-01-16'), storeId: '4' },
        { productName: 'Rice 5kg', price: 18.20, purchaseDate: new Date('2024-01-13'), storeId: '5' },

        // Cooking Oil
        { productName: 'Cooking Oil 1L', price: 8.90, purchaseDate: new Date('2024-01-15'), storeId: '1' },
        { productName: 'Cooking Oil 1L', price: 8.50, purchaseDate: new Date('2024-01-11'), storeId: '2' },
        { productName: 'Cooking Oil 1L', price: 9.20, purchaseDate: new Date('2024-01-17'), storeId: '3' },
        { productName: 'Cooking Oil 1L', price: 7.90, purchaseDate: new Date('2024-01-14'), storeId: '4' },
        { productName: 'Cooking Oil 1L', price: 8.70, purchaseDate: new Date('2024-01-16'), storeId: '7' }
    ];

    /**
     * Get all unique product names for autocomplete
     */
    getProductNames(): string[] {
        const uniqueNames = new Set(this.productPrices.map(p => p.productName));
        return Array.from(uniqueNames).sort();
    }

    /**
     * Search for stores selling a specific product
     */
    searchProduct(productName: string): StoreWithPrice[] {
        const normalizedQuery = productName.toLowerCase();

        // Find all matching products
        const matchingPrices = this.productPrices.filter(p =>
            p.productName.toLowerCase().includes(normalizedQuery)
        );

        // Group by store and get the most recent price
        const storeMap = new Map<string, ProductPrice>();
        matchingPrices.forEach(price => {
            const existing = storeMap.get(price.storeId);
            if (!existing || price.purchaseDate > existing.purchaseDate) {
                storeMap.set(price.storeId, price);
            }
        });

        // Combine with store information
        const results: StoreWithPrice[] = [];
        storeMap.forEach((price, storeId) => {
            const store = this.stores.find(s => s.id === storeId);
            if (store) {
                results.push({
                    store,
                    price: price.price,
                    lastPurchaseDate: price.purchaseDate
                });
            }
        });

        // Sort by price (cheapest first)
        return results.sort((a, b) => a.price - b.price);
    }

    /**
     * Calculate distance between two coordinates (Haversine formula)
     */
    calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
        const R = 6371; // Earth's radius in km
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

    /**
     * Add distance to search results based on user location
     */
    addDistanceToResults(results: StoreWithPrice[], userLat: number, userLon: number): StoreWithPrice[] {
        return results.map(result => ({
            ...result,
            distance: this.calculateDistance(userLat, userLon, result.store.latitude, result.store.longitude)
        }));
    }
}
