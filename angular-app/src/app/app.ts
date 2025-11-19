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
  isOnAskAIPage = signal(false);

  constructor(private router: Router) {
    // Update active tab based on route
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event: NavigationEnd) => {
      if (event.url.includes('/dashboard')) {
        this.activeTabIndex = 0;
      } else if (event.url.includes('/history')) {
        this.activeTabIndex = 1;
      }

      // Check if on Ask AI page
      this.isOnAskAIPage.set(event.url.includes('/ask-ai'));
    });
  }

  onTabChange(index: number) {
    const routes = ['/dashboard', '/history'];
    this.router.navigate([routes[index]]);
  }

  onCameraClick() {
    this.router.navigate(['/camera']);
  }

  onAskAIClick() {
    this.router.navigate(['/ask-ai']);
  }
}
