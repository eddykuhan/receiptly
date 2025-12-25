import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toast toast-top toast-center z-50" style="margin-top: env(safe-area-inset-top)">
      @for (toast of toastService.toasts(); track toast.id) {
        <div 
          class="alert shadow-2xl animate-slideDown"
          [class.alert-success]="toast.type === 'success'"
          [class.alert-error]="toast.type === 'error'"
          [class.alert-warning]="toast.type === 'warning'"
          [class.alert-info]="toast.type === 'info'">
          <div class="flex items-start gap-2 w-full">
            <span class="material-icons text-lg shrink-0 animate-iconPop">
              {{ getIcon(toast.type) }}
            </span>
            <span class="flex-1 break-words text-sm leading-tight">{{ toast.message }}</span>
            <button 
              class="btn btn-ghost btn-xs btn-circle shrink-0 hover:rotate-90 transition-transform duration-200" 
              (click)="toastService.remove(toast.id)">
              <span class="material-icons text-sm">close</span>
            </button>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    @keyframes slideDown {
      from {
        transform: translateY(-120%) scale(0.95);
        opacity: 0;
      }
      to {
        transform: translateY(0) scale(1);
        opacity: 1;
      }
    }

    @keyframes iconPop {
      0% {
        transform: scale(0);
        opacity: 0;
      }
      50% {
        transform: scale(1.2);
      }
      100% {
        transform: scale(1);
        opacity: 1;
      }
    }

    .animate-slideDown {
      animation: slideDown 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    .animate-iconPop {
      animation: iconPop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    .alert {
      min-width: 260px;
      max-width: min(90vw, 380px);
      word-wrap: break-word;
      overflow-wrap: break-word;
      hyphens: auto;
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.1);
    }

    @media (max-width: 640px) {
      .alert {
        min-width: 240px;
        font-size: 0.875rem;
      }
    }
  `]
})
export class ToastContainerComponent {
  toastService = inject(ToastService);

  getIcon(type: string): string {
    switch (type) {
      case 'success': return 'check_circle';
      case 'error': return 'error';
      case 'warning': return 'warning';
      case 'info': return 'info';
      default: return 'info';
    }
  }
}
