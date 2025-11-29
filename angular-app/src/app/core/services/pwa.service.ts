import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class PwaService {
  private promptEvent: any;
  private isStandalone$ = new BehaviorSubject<boolean>(false);
  private canInstall$ = new BehaviorSubject<boolean>(false);

  constructor() {
    this.checkStandalone();
    this.listenForInstallPrompt();
    this.listenForAppInstalled();
  }

  /**
   * Check if app is running in standalone mode (installed)
   */
  private checkStandalone(): void {
    const isStandalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      (window.navigator as any).standalone ||
      document.referrer.includes('android-app://');

    this.isStandalone$.next(isStandalone);
  }

  /**
   * Listen for the beforeinstallprompt event
   */
  private listenForInstallPrompt(): void {
    window.addEventListener('beforeinstallprompt', (event: Event) => {
      event.preventDefault();
      this.promptEvent = event;
      this.canInstall$.next(true);
      console.log('PWA: Install prompt available');
    });
  }

  /**
   * Listen for app installed event
   */
  private listenForAppInstalled(): void {
    window.addEventListener('appinstalled', () => {
      this.canInstall$.next(false);
      this.isStandalone$.next(true);
      console.log('PWA: App installed successfully');
    });
  }

  /**
   * Prompt user to install the app
   */
  async installApp(): Promise<boolean> {
    if (!this.promptEvent) {
      console.warn('PWA: Install prompt not available');
      return false;
    }

    try {
      this.promptEvent.prompt();
      const { outcome } = await this.promptEvent.userChoice;

      if (outcome === 'accepted') {
        console.log('PWA: User accepted install');
        this.canInstall$.next(false);
        return true;
      } else {
        console.log('PWA: User dismissed install');
        return false;
      }
    } catch (error) {
      console.error('PWA: Error during install:', error);
      return false;
    } finally {
      this.promptEvent = null;
    }
  }

  /**
   * Check if app can be installed
   */
  get canInstall(): boolean {
    return this.canInstall$.value;
  }

  /**
   * Observable for install availability
   */
  get canInstall$Observable() {
    return this.canInstall$.asObservable();
  }

  /**
   * Check if app is installed
   */
  get isStandalone(): boolean {
    return this.isStandalone$.value;
  }

  /**
   * Observable for standalone mode
   */
  get isStandalone$Observable() {
    return this.isStandalone$.asObservable();
  }

  /**
   * Check if device is iOS
   */
  get isIos(): boolean {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
  }

  /**
   * Check if device is Android
   */
  get isAndroid(): boolean {
    return /android/i.test(navigator.userAgent);
  }

  /**
   * Get install instructions for iOS
   */
  getIosInstallInstructions(): string {
    return 'Tap the Share button, then tap "Add to Home Screen"';
  }
}
