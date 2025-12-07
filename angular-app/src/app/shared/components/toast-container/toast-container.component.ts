import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toast toast-top toast-end z-50" style="margin-top: env(safe-area-inset-top)">
      @for (toast of toastService.toasts(); track toast.id) {
        <div 
          class="alert shadow-lg animate-slideIn"
          [class.alert-success]="toast.type === 'success'"
          [class.alert-error]="toast.type === 'error'"
          [class.alert-warning]="toast.type === 'warning'"
          [class.alert-info]="toast.type === 'info'">
          <div class="flex items-start gap-2 w-full">
            <span class="material-icons text-lg">
              {{ getIcon(toast.type) }}
            </span>
            <span class="flex-1">{{ toast.message }}</span>
            <button 
              class="btn btn-ghost btn-xs btn-circle" 
              (click)="toastService.remove(toast.id)">
              <span class="material-icons text-sm">close</span>
            </button>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    @keyframes slideIn {
      from {
        transform: translateX(100%);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }

    .animate-slideIn {
      animation: slideIn 0.3s ease-out;
    }

    .alert {
      min-width: 280px;
      max-width: 400px;
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
