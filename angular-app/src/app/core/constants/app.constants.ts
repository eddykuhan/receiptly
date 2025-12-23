/**
 * Application-wide constants
 * These values can be overridden by user preferences in the future
 */
export const APP_CONSTANTS = {
    /**
     * Default search radius in kilometers for nearby items and deals
     * Future: This will be configurable via user preferences
     */
    DEFAULT_SEARCH_RADIUS_KM: 10,

    /**
     * Default time window in days for filtering recent purchases
     */
    DEFAULT_DAYS_FILTER: 7,

    /**
     * Maximum number of deals to show in the hot deals carousel
     */
    MAX_HOT_DEALS_COUNT: 10,

    /**
     * Geolocation timeout in milliseconds
     */
    GEOLOCATION_TIMEOUT_MS: 10000,

    /**
     * Maximum age of cached location in milliseconds (5 minutes)
     */
    GEOLOCATION_MAX_AGE_MS: 300000
} as const;
