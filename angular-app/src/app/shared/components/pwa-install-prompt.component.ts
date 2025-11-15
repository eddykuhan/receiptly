import { Component, inject, ChangeDetectorRef, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { PwaService } from '../../core/services/pwa.service';

@Component({
  selector: 'app-pwa-install-prompt',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatSnackBarModule],
  template: `
    @if (showPrompt && !dismissed) {
      <div class="install-prompt">
        <div class="install-content">
          <div class="install-icon">
            <mat-icon>get_app</mat-icon>
          </div>
          <div class="install-text">
            <h3>Install Receiptly</h3>
            <p>Install our app for a better experience</p>
          </div>
        </div>
        <div class="install-actions">
          <button mat-button (click)="dismiss()">
            Not now
          </button>
          <button mat-raised-button color="primary" (click)="install()">
            Install
          </button>
        </div>
      </div>
    }

    @if (showIosPrompt && !dismissed) {
      <div class="install-prompt ios-prompt">
        <div class="install-content">
          <div class="install-icon">
            <mat-icon>ios_share</mat-icon>
          </div>
          <div class="install-text">
            <h3>Add to Home Screen</h3>
            <p>{{ pwaService.getIosInstallInstructions() }}</p>
          </div>
        </div>
        <button mat-icon-button (click)="dismiss()" class="close-btn">
          <mat-icon>close</mat-icon>
        </button>
      </div>
    }
  `,
  styles: [`
    .install-prompt {
      position: fixed;
      bottom: 80px;
      left: 16px;
      right: 16px;
      background: white;
      border-radius: 16px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
      padding: 20px;
      z-index: 1000;
      animation: slideUp 0.3s ease-out;

      &.ios-prompt {
        bottom: 16px;
        display: flex;
        align-items: flex-start;
        justify-content: space-between;

        .close-btn {
          flex-shrink: 0;
          margin-left: 8px;
        }
      }
    }

    @keyframes slideUp {
      from {
        transform: translateY(100%);
        opacity: 0;
      }
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }

    .install-content {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;

      .ios-prompt & {
        margin-bottom: 0;
        flex: 1;
      }
    }

    .install-icon {
      width: 48px;
      height: 48px;
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;

      mat-icon {
        color: #6366f1;
        font-size: 28px;
        width: 28px;
        height: 28px;
      }
    }

    .install-text {
      flex: 1;

      h3 {
        margin: 0 0 4px;
        font-size: 16px;
        font-weight: 600;
        color: #111827;
      }

      p {
        margin: 0;
        font-size: 13px;
        color: #6b7280;
        line-height: 1.4;
      }
    }

    .install-actions {
      display: flex;
      gap: 12px;
      justify-content: flex-end;

      button {
        font-weight: 600;
        border-radius: 8px;
      }
    }
  `]
})
export class PwaInstallPromptComponent implements OnInit {
  pwaService = inject(PwaService);
  private snackBar = inject(MatSnackBar);
  private cdr = inject(ChangeDetectorRef);
  
  dismissed = false;
  showPrompt = false;
  showIosPrompt = false;

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
      this.snackBar.open('App installed successfully!', 'Close', {
        duration: 3000,
        horizontalPosition: 'center',
        verticalPosition: 'bottom'
      });
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
}
