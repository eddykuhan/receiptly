import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs';
import { PwaInstallPromptComponent } from './shared/components/pwa-install-prompt.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, PwaInstallPromptComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  activeTabIndex = 0;
  currentRoute = signal('');

  constructor(private router: Router) {
    // Update active tab based on route
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event: NavigationEnd) => {
      // Update current route signal
      this.currentRoute.set(event.url);

      if (event.url.includes('/dashboard')) {
        this.activeTabIndex = 0;
      } else if (event.url.includes('/price-map')) {
        this.activeTabIndex = 1;
      } else {
        this.activeTabIndex = -1; // No active tab for other routes
      }
    });

    // Set initial route
    this.currentRoute.set(this.router.url);
  }

  onTabChange(index: number) {
    if (index === 0) {
      this.router.navigate(['/dashboard']);
    } else if (index === 1) {
      this.router.navigate(['/price-map']);
    }
  }

  onCameraClick() {
    this.router.navigate(['/camera']);
  }

  onAskAIClick() {
    this.router.navigate(['/ask-ai']);
  }

  onPriceMapClick() {
    this.router.navigate(['/price-map']);
  }

  onRewardsClick() {
    this.router.navigate(['/rewards']);
  }

  onProfileClick() {
    this.router.navigate(['/profile']);
  }

  isRouteActive(route: string): boolean {
    return this.currentRoute().includes(route);
  }
}
