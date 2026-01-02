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
    private permissionRequested = false;

    /**
     * Detect if running on iOS
     */
    private isIOS(): boolean {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
               (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    }

    /**
     * Request user's location with timeout and error handling
     * On iOS, this MUST be called in response to a user interaction (e.g., button click)
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
        this.permissionRequested = true;

        const isIOS = this.isIOS();
        const timeout = isIOS ? 30000 : APP_CONSTANTS.GEOLOCATION_TIMEOUT_MS; // iOS needs more time

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
                    let userFriendlyMsg = '';
                    
                    if (error.code === 1) {
                        errorMsg = 'Location permission denied';
                        if (isIOS) {
                            userFriendlyMsg = 'Please enable location in Settings > Safari > Location';
                        } else {
                            userFriendlyMsg = 'Please enable location permission in your browser settings';
                        }
                        console.log('❌ User denied location permission');
                    } else if (error.code === 2) {
                        errorMsg = 'Location unavailable';
                        userFriendlyMsg = 'Location services unavailable. Please check your device settings.';
                        console.log('❌ Location unavailable');
                    } else if (error.code === 3) {
                        errorMsg = 'Location timeout';
                        userFriendlyMsg = 'Location request timed out. Please try again.';
                        console.log('❌ Location request timeout');
                    }
                    
                    this.error.set(userFriendlyMsg || errorMsg);
                    this.isLoading.set(false);
                    resolve(null);
                },
                {
                    enableHighAccuracy: !isIOS, // iOS performs better with false
                    timeout: timeout,
                    maximumAge: isIOS ? 0 : APP_CONSTANTS.GEOLOCATION_MAX_AGE_MS // iOS needs fresh location
                }
            );
        });
    }

    /**
     * Check if permission has been requested
     */
    wasPermissionRequested(): boolean {
        return this.permissionRequested;
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
     * Watch for location changes (continuous updates)
     * Returns a function to stop watching
     */
    watchLocation(callback: (location: UserLocation) => void): () => void {
        if (!navigator.geolocation) {
            console.error('Geolocation not supported');
            return () => {};
        }

        const watchId = navigator.geolocation.watchPosition(
            (position) => {
                const location: UserLocation = {
                    lat: position.coords.latitude,
                    lon: position.coords.longitude
                };
                this.userLocation.set(location);
                callback(location);
            },
            (error) => {
                console.error('Location watch error:', error);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 30000 // Accept cached location up to 30 seconds old
            }
        );

        // Return cleanup function
        return () => navigator.geolocation.clearWatch(watchId);
    }

    /**
     * Check if geolocation permission is granted
     */
    async checkPermission(): Promise<boolean> {
        if (!navigator.permissions) return false;

        try {
            const result = await navigator.permissions.query({ name: 'geolocation' });
            return result.state === 'granted';
        } catch {
            return false;
        }
    }

    /**
     * Get fresh location if permission is already granted
     */
    async getFreshLocation(): Promise<UserLocation | null> {
        const hasPermission = await this.checkPermission();
        if (!hasPermission) {
            return null; // Don't request if no permission
        }

        return this.requestLocation();
    }

    /**
     * Retry getting location (useful when user denies first time)
     * Alias for requestLocation for backward compatibility
     */
    async retryLocation(): Promise<UserLocation | null> {
        return this.requestLocation();
    }
}
