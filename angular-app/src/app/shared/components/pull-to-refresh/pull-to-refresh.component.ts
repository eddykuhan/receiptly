import { Component, Input, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-pull-to-refresh',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="relative" (touchstart)="onTouchStart($event)" (touchmove)="onTouchMove($event)" (touchend)="onTouchEnd($event)">
      <!-- Pull to Refresh Indicator -->
      <div 
        class="absolute top-0 left-0 right-0 flex justify-center items-center transition-all duration-300 overflow-hidden"
        [style.height.px]="pullDistance() > 0 ? Math.min(pullDistance(), 80) : 0"
        [style.opacity]="pullDistance() > 0 ? Math.min(pullDistance() / 80, 1) : 0">
        <div class="flex flex-col items-center gap-2 py-2">
          <span class="material-icons animate-spin text-primary" *ngIf="isRefreshing()">refresh</span>
          <span class="material-icons text-primary" *ngIf="!isRefreshing() && pullDistance() < triggerDistance">arrow_downward</span>
          <span class="material-icons text-primary" *ngIf="!isRefreshing() && pullDistance() >= triggerDistance">refresh</span>
          <span class="text-xs text-base-content/70" *ngIf="!isRefreshing() && pullDistance() < triggerDistance">Pull to refresh</span>
          <span class="text-xs text-primary font-semibold" *ngIf="!isRefreshing() && pullDistance() >= triggerDistance">Release to refresh</span>
          <span class="text-xs text-primary font-semibold" *ngIf="isRefreshing()">Refreshing...</span>
        </div>
      </div>
      
      <!-- Content -->
      <div [style.transform]="'translateY(' + (isRefreshing() ? 80 : Math.min(pullDistance(), 80)) + 'px)'" 
           class="transition-transform duration-300">
        <ng-content></ng-content>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      width: 100%;
    }
  `]
})
export class PullToRefreshComponent {
  @Input() disabled = false;
  @Output() refresh = new EventEmitter<void>();

  pullDistance = signal(0);
  isRefreshing = signal(false);
  
  private startY = 0;
  protected readonly triggerDistance = 80;
  protected readonly Math = Math;

  onTouchStart(event: TouchEvent): void {
    if (this.disabled || this.isRefreshing()) return;
    
    // Only activate if scrolled to top
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    if (scrollTop === 0) {
      this.startY = event.touches[0].clientY;
    }
  }

  onTouchMove(event: TouchEvent): void {
    if (this.disabled || this.isRefreshing() || this.startY === 0) return;

    const currentY = event.touches[0].clientY;
    const diff = currentY - this.startY;

    // Only pull down when at top of page
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    if (scrollTop === 0 && diff > 0) {
      event.preventDefault();
      // Use diminishing returns for pull distance
      this.pullDistance.set(Math.min(diff * 0.5, 120));
    }
  }

  onTouchEnd(event: TouchEvent): void {
    if (this.disabled || this.isRefreshing()) return;

    if (this.pullDistance() >= this.triggerDistance) {
      this.isRefreshing.set(true);
      this.refresh.emit();
      
      // Reset after refresh completes (managed externally)
      setTimeout(() => {
        this.isRefreshing.set(false);
        this.pullDistance.set(0);
      }, 2000);
    } else {
      this.pullDistance.set(0);
    }
    
    this.startY = 0;
  }

  /**
   * Call this method from parent component when refresh is complete
   */
  public completeRefresh(): void {
    this.isRefreshing.set(false);
    this.pullDistance.set(0);
  }
}
