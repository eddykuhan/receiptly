import { Component } from '@angular/core';
import { RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { filter } from 'rxjs';
import { PwaInstallPromptComponent } from './shared/components/pwa-install-prompt.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, MatTabsModule, MatIconModule, PwaInstallPromptComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  activeTabIndex = 0;
  
  constructor(private router: Router) {
    // Update active tab based on route
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event: NavigationEnd) => {
      if (event.url.includes('/camera')) {
        this.activeTabIndex = 0;
      } else if (event.url.includes('/history')) {
        this.activeTabIndex = 1;
      } else if (event.url.includes('/dashboard')) {
        this.activeTabIndex = 2;
      }
    });
  }
  
  onTabChange(index: number) {
    const routes = ['/camera', '/history', '/dashboard'];
    this.router.navigate([routes[index]]);
  }
}
