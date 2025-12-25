import { Injectable, ApplicationRef, inject } from '@angular/core';
import { SwUpdate, VersionReadyEvent } from '@angular/service-worker';
import { filter, first, interval, concat } from 'rxjs';
import { ToastService } from './toast.service';

/**
 * Service to handle PWA updates automatically
 * Features:
 * - Checks for updates every 6 hours
 * - Prompts user when update is available
 * - Can auto-reload or require user confirmation
 */
@Injectable({
  providedIn: 'root'
})
export class PwaUpdateService {
  private swUpdate = inject(SwUpdate);
  private appRef = inject(ApplicationRef);
  private toastService = inject(ToastService);

  constructor() {
    if (!this.swUpdate.isEnabled) {
      console.log('Service Worker is not enabled');
      return;
    }

    // Listen for new versions available
    this.checkForUpdates();
    
    // Check for updates when app becomes stable and then every 6 hours
    this.scheduleUpdateChecks();
    
    // Handle unrecoverable errors
    this.handleUnrecoverableState();
  }

  /**
   * Listen for version updates and prompt user
   */
  private checkForUpdates(): void {
    this.swUpdate.versionUpdates
      .pipe(
        filter((evt): evt is VersionReadyEvent => evt.type === 'VERSION_READY')
      )
      .subscribe(evt => {
        console.log('New version available:', evt.latestVersion);
        this.promptUserToUpdate();
      });
  }

  /**
   * Schedule periodic update checks
   */
  private scheduleUpdateChecks(): void {
    // Wait for app to stabilize before first check
    const appIsStable$ = this.appRef.isStable.pipe(
      first(isStable => isStable === true)
    );

    // Check every 6 hours (21600000 ms)
    const everySixHours$ = interval(6 * 60 * 60 * 1000);

    // Combine: check when stable, then every 6 hours
    concat(appIsStable$, everySixHours$).subscribe(async () => {
      try {
        const updateAvailable = await this.swUpdate.checkForUpdate();
        if (updateAvailable) {
          console.log('Update check: new version found');
        } else {
          console.log('Update check: already on latest version');
        }
      } catch (err) {
        console.error('Failed to check for updates:', err);
      }
    });
  }

  /**
   * Handle unrecoverable service worker state
   */
  private handleUnrecoverableState(): void {
    this.swUpdate.unrecoverable.subscribe(event => {
      console.error('Unrecoverable service worker state:', event.reason);
      this.toastService.error(
        'App needs to reload due to an error. Please refresh the page.',
        { duration: 10000 }
      );
    });
  }

  /**
   * Prompt user to update the app
   * You can customize this to auto-reload or show a custom dialog
   */
  private promptUserToUpdate(): void {
    // Option 1: Auto-reload (uncomment to enable)
    // this.activateUpdate();

    // Option 2: Show toast with action button
    this.toastService.info(
      'New version available! Tap to update.',
      { 
        duration: 0, // Don't auto-hide
        action: {
          label: 'Update',
          handler: () => this.activateUpdate()
        }
      }
    );

    // Option 3: Native confirm dialog (simple fallback)
    // if (confirm('New version available! Load new version?')) {
    //   this.activateUpdate();
    // }
  }

  /**
   * Activate the update and reload the page
   */
  private async activateUpdate(): Promise<void> {
    try {
      await this.swUpdate.activateUpdate();
      console.log('Update activated, reloading...');
      document.location.reload();
    } catch (err) {
      console.error('Failed to activate update:', err);
      this.toastService.error('Failed to update. Please refresh manually.');
    }
  }

  /**
   * Manually check for updates (can be called from UI)
   */
  async checkNow(): Promise<void> {
    if (!this.swUpdate.isEnabled) {
      console.log('Service worker not enabled');
      return;
    }

    try {
      const updateAvailable = await this.swUpdate.checkForUpdate();
      if (!updateAvailable) {
        this.toastService.success('Already on the latest version!');
      }
    } catch (err) {
      console.error('Update check failed:', err);
      this.toastService.error('Failed to check for updates');
    }
  }
}
