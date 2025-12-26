import { Injectable, signal } from '@angular/core';
import { APP_CONSTANTS } from '../constants/app.constants';

export interface UserPreferences {
    searchRadiusKm: number;
    theme: 'light' | 'dark';
    language: string;
    currency: string;
    dateFormat: string;
}

@Injectable({
    providedIn: 'root'
})
export class UserPreferencesService {
    private readonly STORAGE_KEY = 'receiptly_user_preferences';
    
    // Default preferences
    private defaultPreferences: UserPreferences = {
        searchRadiusKm: APP_CONSTANTS.DEFAULT_SEARCH_RADIUS_KM,
        theme: 'light',
        language: 'en',
        currency: 'MYR',
        dateFormat: 'DD/MM/YYYY'
    };

    // Signal to track current preferences
    preferences = signal<UserPreferences>(this.loadPreferences());

    constructor() {
        // Load preferences from localStorage on init
        this.preferences.set(this.loadPreferences());
    }

    /**
     * Load preferences from localStorage
     */
    private loadPreferences(): UserPreferences {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            if (stored) {
                const parsed = JSON.parse(stored);
                // Merge with defaults to ensure all fields exist
                return { ...this.defaultPreferences, ...parsed };
            }
        } catch (error) {
            console.error('Error loading user preferences:', error);
        }
        return this.defaultPreferences;
    }

    /**
     * Save preferences to localStorage
     */
    private savePreferences(preferences: UserPreferences): void {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(preferences));
        } catch (error) {
            console.error('Error saving user preferences:', error);
        }
    }

    /**
     * Update search radius preference
     */
    updateSearchRadius(radiusKm: number): void {
        const updated = { ...this.preferences(), searchRadiusKm: radiusKm };
        this.preferences.set(updated);
        this.savePreferences(updated);
    }

    /**
     * Update theme preference
     */
    updateTheme(theme: 'light' | 'dark'): void {
        const updated = { ...this.preferences(), theme };
        this.preferences.set(updated);
        this.savePreferences(updated);
    }

    /**
     * Get current search radius
     */
    getSearchRadius(): number {
        return this.preferences().searchRadiusKm;
    }

    /**
     * Reset preferences to defaults
     */
    resetToDefaults(): void {
        this.preferences.set(this.defaultPreferences);
        this.savePreferences(this.defaultPreferences);
    }
}
