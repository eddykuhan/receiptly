import { Component, inject, ChangeDetectorRef, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PwaService } from '../../core/services/pwa.service';

@Component({
  selector: 'app-pwa-install-prompt',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (showPrompt && !dismissed) {
      <div class="fixed bottom-20 left-4 right-4 z-[10002] animate-[slideUp_0.3s_ease-out]">
        <div class="card bg-base-100 shadow-xl border border-base-200">
          <div class="card-body p-4 flex-row items-center gap-4">
            <div class="p-3 bg-primary/10 rounded-xl text-primary shrink-0">
              <span class="material-icons text-2xl">get_app</span>
            </div>
            <div class="flex-1">
              <h3 class="font-bold text-base">Install Cheapsy</h3>
              <p class="text-sm text-base-content/60">Install our app for a better experience</p>
            </div>
          </div>
          <div class="card-actions justify-end p-4 pt-0">
            <button class="btn btn-ghost btn-sm" (click)="dismiss()">
              Not now
            </button>
            <button class="btn btn-primary btn-sm" (click)="install()">
              Install
            </button>
          </div>
        </div>
      </div>
    }

    @if (showIosPrompt && !dismissed) {
      <div class="fixed bottom-4 left-4 right-4 z-[10002] animate-[slideUp_0.3s_ease-out]">
        <div class="alert bg-base-100 shadow-xl border border-base-200 items-start">
          <div class="p-2 bg-primary/10 rounded-lg text-primary shrink-0 mt-1">
            <span class="material-icons">ios_share</span>
          </div>
          <div class="flex-1">
            <h3 class="font-bold">Add to Home Screen</h3>
            <div class="text-sm text-base-content/60 mt-1">
              {{ pwaService.getIosInstallInstructions() }}
            </div>
          </div>
          <button class="btn btn-circle btn-ghost btn-sm" (click)="dismiss()">
            <span class="material-icons">close</span>
          </button>
        </div>
      </div>
    }
    
    @if (toastMessage()) {
      <div class="toast toast-bottom toast-center z-[10003]">
        <div class="alert alert-success">
          <span class="material-icons text-white">check_circle</span>
          <span class="text-white">{{ toastMessage() }}</span>
        </div>
      </div>
    }
  `,
  styles: [`
    @keyframes slideUp {
      from { transform: translateY(100%); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
  `]
})
export class PwaInstallPromptComponent implements OnInit {
  pwaService = inject(PwaService);
  private cdr = inject(ChangeDetectorRef);

  dismissed = false;
  showPrompt = false;
  showIosPrompt = false;

  toastMessage = signal<string | null>(null);

  ngOnInit() {
    // Check if previously dismissed
    const dismissedUntil = localStorage.getItem('pwa-install-dismissed');
    if (dismissedUntil && new Date(dismissedUntil) > new Date()) {
      this.dismissed = true;
      return;
    }

    // Wait for next tick to avoid ExpressionChangedAfterItHasBeenCheckedError
    setTimeout(() => {
      this.showPrompt = this.pwaService.canInstall;
      this.showIosPrompt = this.pwaService.isIos && !this.pwaService.isStandalone;
      this.cdr.detectChanges();
    }, 0);

    // Subscribe to canInstall changes
    this.pwaService.canInstall$Observable.subscribe(canInstall => {
      this.showPrompt = canInstall;
      this.cdr.detectChanges();
    });
  }

  async install() {
    const installed = await this.pwaService.installApp();

    if (installed) {
      this.showToast('App installed successfully!');
    }

    this.dismissed = true;
  }

  dismiss() {
    this.dismissed = true;
    // Store dismissal in localStorage to not show again for 7 days
    const dismissUntil = new Date();
    dismissUntil.setDate(dismissUntil.getDate() + 7);
    localStorage.setItem('pwa-install-dismissed', dismissUntil.toISOString());
  }

  private showToast(message: string) {
    this.toastMessage.set(message);
    setTimeout(() => this.toastMessage.set(null), 3000);
  }
}
