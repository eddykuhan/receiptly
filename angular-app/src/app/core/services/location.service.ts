import { Injectable, signal } from '@angular/core';
import { APP_CONSTANTS } from '../constants/app.constants';

export interface UserLocation {
    lat: number;
    lon: number;
}

@Injectable({
    providedIn: 'root'
})
export class LocationService {
    userLocation = signal<UserLocation | null>(null);
    isLoading = signal(false);
    error = signal<string | null>(null);

    /**
     * Request user's location with timeout and error handling
     * This should be called during app initialization (splash screen)
     */
    async requestLocation(): Promise<UserLocation | null> {
        if (!navigator.geolocation) {
            const errorMsg = 'Geolocation not supported by browser';
            console.error('❌', errorMsg);
            this.error.set(errorMsg);
            return null;
        }

        this.isLoading.set(true);
        this.error.set(null);

        return new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const location: UserLocation = {
                        lat: position.coords.latitude,
                        lon: position.coords.longitude
                    };
                    this.userLocation.set(location);
                    this.isLoading.set(false);
                    console.log('✅ Location obtained:', location);
                    resolve(location);
                },
                (error) => {
                    let errorMsg = 'Unable to get location';
                    if (error.code === 1) {
                        errorMsg = 'Location permission denied';
                        console.log('❌ User denied location permission');
                    } else if (error.code === 2) {
                        errorMsg = 'Location unavailable';
                        console.log('❌ Location unavailable');
                    } else if (error.code === 3) {
                        errorMsg = 'Location timeout';
                        console.log('❌ Location request timeout');
                    }
                    this.error.set(errorMsg);
                    this.isLoading.set(false);
                    resolve(null);
                },
                {
                    enableHighAccuracy: true,
                    timeout: APP_CONSTANTS.GEOLOCATION_TIMEOUT_MS,
                    maximumAge: APP_CONSTANTS.GEOLOCATION_MAX_AGE_MS
                }
            );
        });
    }

    /**
     * Get current location, or null if not available
     */
    getLocation(): UserLocation | null {
        return this.userLocation();
    }

    /**
     * Check if location is available
     */
    hasLocation(): boolean {
        return this.userLocation() !== null;
    }

    /**
     * Retry getting location (useful when user denies first time)
     */
    async retryLocation(): Promise<UserLocation | null> {
        return this.requestLocation();
    }
}
