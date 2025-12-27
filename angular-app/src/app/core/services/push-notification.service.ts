import { Injectable, inject, signal } from '@angular/core';
import type { IOneSignalOneSignal } from 'onesignal-ngx';
import { environment } from '../../../environments/environment';
import { ClerkAuthService } from './clerk-auth.service';
import { UserPreferencesService } from './user-preferences.service';

export interface NotificationPermissionState {
  permission: NotificationPermission;
  subscribed: boolean;
  playerId?: string;
}

@Injectable({
  providedIn: 'root'
})
export class PushNotificationService {
  private authService = inject(ClerkAuthService);
  private userPreferencesService = inject(UserPreferencesService);

  // Signal to track notification state
  notificationState = signal<NotificationPermissionState>({
    permission: 'default',
    subscribed: false
  });

  private initialized = false;
  private readonly STORAGE_KEY = 'receiptly_notification_preference';
  private initializationPromise: Promise<void> | null = null;

  private get oneSignal(): IOneSignalOneSignal | undefined {
    return window.OneSignal;
  }

  constructor() {
    // Load persisted preference from localStorage
    this.loadPersistedPreference();
    
    // Initialize immediately if user is already authenticated
    if (this.authService.getCurrentUser()) {
      this.initializeOneSignal();
    }
    
    // Also initialize after user is authenticated (for login flow)
    this.authService.isAuthenticated$.subscribe(isAuth => {
      if (isAuth && !this.initialized) {
        this.initializeOneSignal();
      }
    });
  }

  /**
   * Load persisted notification preference from localStorage
   */
  private loadPersistedPreference(): void {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const preference = JSON.parse(stored);
        this.notificationState.set({
          permission: preference.permission || 'default',
          subscribed: preference.subscribed || false,
          playerId: preference.playerId
        });
        console.log('Loaded persisted notification preference from localStorage:', preference);
      }
    } catch (error) {
      console.error('Error loading persisted notification preference:', error);
    }
  }

  /**
   * Persist notification preference to localStorage
   */
  private persistPreference(): void {
    try {
      const state = this.notificationState();
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(state));
      console.log('Persisted notification preference to localStorage:', state);
    } catch (error) {
      console.error('Error persisting notification preference:', error);
    }
  }

  /**
   * Initialize OneSignal SDK
   */
  private async initializeOneSignal(): Promise<void> {
    // Return existing promise if already initializing
    if (this.initializationPromise) {
      return this.initializationPromise;
    }

    this.initializationPromise = new Promise<void>((resolve, reject) => {
      try {
        if (!environment.oneSignalAppId) {
          console.warn('OneSignal App ID not configured');
          resolve();
          return;
        }

        // Wait for OneSignal to load
        window.OneSignalDeferred = window.OneSignalDeferred || [];
        window.OneSignalDeferred.push(async (OneSignal: IOneSignalOneSignal) => {
          try {
            await OneSignal.init({
              appId: environment.oneSignalAppId,
              allowLocalhostAsSecureOrigin: !environment.production,
              serviceWorkerParam: {
                scope: '/push/' // Separate scope to avoid conflict with Angular NGSW
              },
              serviceWorkerPath: 'push/OneSignalSDKWorker.js'
            });

            this.initialized = true;
            console.log('OneSignal initialized successfully');

            // Get the persisted preference
            const persistedState = this.notificationState();
            
            // Restore the subscription state from localStorage
            // Only if the user was previously subscribed
            if (persistedState.subscribed) {
              try {
                await OneSignal.User.PushSubscription.optIn();
                console.log('Restored push notification opt-in status from localStorage');
              } catch (err) {
                console.warn('Could not restore push notification state:', err);
              }
            }

            // Update notification state from OneSignal
            await this.updateNotificationState();

            // Tag user with Clerk ID for targeting
            const user = this.authService.getCurrentUser();
            if (user?.id) {
              OneSignal.User.addAlias('clerk_id', user.id);
              console.log('OneSignal external user ID set:', user.id);
            }

            // Listen for permission changes
            OneSignal.User.PushSubscription.addEventListener('change', (change: any) => {
              console.log('Subscription changed:', change);
              this.updateNotificationState();
            });

            // Listen for notification display
            OneSignal.Notifications.addEventListener('foregroundWillDisplay', (event: any) => {
              console.log('Notification displayed:', event);
            });

            resolve();
          } catch (error) {
            console.error('Error during OneSignal initialization:', error);
            reject(error);
          }
        });
      } catch (error) {
        console.error('Error initializing OneSignal:', error);
        reject(error);
      }
    });

    return this.initializationPromise;
  }

  /**
   * Wait for OneSignal to be ready
   */
  private async waitForOneSignal(timeoutMs: number = 10000): Promise<boolean> {
    if (this.oneSignal && this.initialized) {
      return true;
    }

    console.log('Waiting for OneSignal to initialize...');
    
    // Wait for initialization to complete with timeout
    if (this.initializationPromise) {
      try {
        await Promise.race([
          this.initializationPromise,
          new Promise((_, reject) => 
            setTimeout(() => reject(new Error('OneSignal initialization timeout')), timeoutMs)
          )
        ]);
        return this.oneSignal !== undefined;
      } catch (error) {
        console.error('OneSignal initialization failed or timed out:', error);
        return false;
      }
    }

    // If not initialized yet and user is authenticated, trigger initialization
    if (this.authService.getCurrentUser()) {
      try {
        await this.initializeOneSignal();
        return this.oneSignal !== undefined;
      } catch (error) {
        console.error('Failed to initialize OneSignal:', error);
        return false;
      }
    }

    return false;
  }

  /**
   * Request notification permission from user
   */
  async requestPermission(): Promise<boolean> {
    try {
      const ready = await this.waitForOneSignal();
      if (!ready || !this.oneSignal) {
        console.error('OneSignal not ready');
        return false;
      }
      const permission = await this.oneSignal.Notifications.requestPermission();
      await this.updateNotificationState();
      return permission;
    } catch (error) {
      console.error('Error requesting notification permission:', error);
      return false;
    }
  }

  /**
   * Subscribe user to push notifications
   */
  async subscribe(): Promise<boolean> {
    try {
      const ready = await this.waitForOneSignal();
      if (!ready || !this.oneSignal) {
        console.error('OneSignal not ready');
        return false;
      }
      await this.oneSignal.User.PushSubscription.optIn();
      await this.updateNotificationState();
      return true;
    } catch (error) {
      console.error('Error subscribing to notifications:', error);
      return false;
    }
  }

  /**
   * Unsubscribe user from push notifications
   */
  async unsubscribe(): Promise<boolean> {
    try {
      const ready = await this.waitForOneSignal();
      if (!ready || !this.oneSignal) {
        console.error('OneSignal not ready');
        return false;
      }
      await this.oneSignal.User.PushSubscription.optOut();
      await this.updateNotificationState();
      return true;
    } catch (error) {
      console.error('Error unsubscribing from notifications:', error);
      return false;
    }
  }

  /**
   * Update current notification state - uses OneSignal as source of truth
   * Falls back to persisted state if OneSignal is not ready
   */
  private async updateNotificationState(): Promise<void> {
    try {
      if (!this.oneSignal) {
        console.warn('OneSignal not available, keeping persisted state');
        return;
      }

      const permission = this.oneSignal.Notifications.permissionNative;
      const subscribed = this.oneSignal.User.PushSubscription.optedIn || false;
      const playerId = this.oneSignal.User.PushSubscription.id;

      const newState: NotificationPermissionState = {
        permission: permission as NotificationPermission,
        subscribed,
        playerId: playerId || undefined
      };

      this.notificationState.set(newState);

      // Persist the updated state
      this.persistPreference();
      console.log('Updated and persisted notification state:', newState);
    } catch (error) {
      console.error('Error updating notification state:', error);
    }
  }

  /**
   * Refresh notification state - public method to force refresh from browser/OneSignal
   */
  async refreshNotificationState(): Promise<void> {
    console.log('Manually refreshing notification state...');
    await this.updateNotificationState();
  }

  /**
   * Send custom tags to OneSignal for user segmentation
   */
  async setUserTags(tags: Record<string, string>): Promise<void> {
    try {
      if (!this.oneSignal) return;
      this.oneSignal.User.addTags(tags);
      console.log('OneSignal tags set:', tags);
    } catch (error) {
      console.error('Error setting OneSignal tags:', error);
    }
  }

  /**
   * Get current notification permission status
   */
  async getPermissionStatus(): Promise<NotificationPermission> {
    try {
      if (!this.oneSignal) return 'default';
      return this.oneSignal.Notifications.permissionNative as NotificationPermission;
    } catch (error) {
      console.error('Error getting permission status:', error);
      return 'default';
    }
  }

  /**
   * Check if user is subscribed
   */
  async isSubscribed(): Promise<boolean> {
    try {
      if (!this.oneSignal) return false;
      return this.oneSignal.User.PushSubscription.optedIn || false;
    } catch (error) {
      console.error('Error checking subscription status:', error);
      return false;
    }
  }

  /**
   * Get OneSignal player ID (for backend integration)
   */
  async getPlayerId(): Promise<string | null> {
    try {
      if (!this.oneSignal) return null;
      return this.oneSignal.User.PushSubscription.id || null;
    } catch (error) {
      console.error('Error getting player ID:', error);
      return null;
    }
  }
}
