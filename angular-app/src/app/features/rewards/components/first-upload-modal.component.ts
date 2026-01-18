import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-first-upload-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="modal modal-open">
      <div class="modal-box max-w-md relative">
        <button class="btn btn-sm btn-circle absolute right-2 top-2" (click)="close()">✕</button>
        
        <!-- Celebration Icon -->
        <div class="text-center mb-4">
          <div class="text-6xl mb-2">🎉</div>
          <h3 class="text-2xl font-bold text-primary">Congratulations!</h3>
        </div>
        
        <!-- Achievement Card -->
        <div class="card bg-gradient-to-r from-primary to-secondary text-primary-content shadow-xl mb-4">
          <div class="card-body text-center">
            <div class="text-4xl mb-2">🏆</div>
            <h4 class="card-title justify-center text-xl">First Upload Achievement</h4>
            <p class="text-lg font-semibold">+50 Bonus Points!</p>
          </div>
        </div>
        
        <!-- Points Breakdown -->
        <div class="bg-base-200 rounded-lg p-4 mb-4">
          <div class="flex justify-between items-center mb-2">
            <span class="text-sm">Receipt Upload</span>
            <span class="font-semibold">+10 pts</span>
          </div>
          <div class="flex justify-between items-center mb-2">
            <span class="text-sm">First Upload Bonus</span>
            <span class="font-semibold text-primary">+50 pts</span>
          </div>
          <div class="flex justify-between items-center mb-2" *ngIf="hasLocationBonus">
            <span class="text-sm">Location Bonus</span>
            <span class="font-semibold">+5 pts</span>
          </div>
          <div class="divider my-2"></div>
          <div class="flex justify-between items-center">
            <span class="font-bold">Total Earned</span>
            <span class="font-bold text-lg text-primary">+{{ totalPoints }} pts</span>
          </div>
        </div>
        
        <!-- Info -->
        <div class="alert alert-info">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <span class="text-sm">Keep uploading receipts to earn more points and unlock rewards!</span>
        </div>
        
        <!-- Action Button -->
        <div class="modal-action">
          <button class="btn btn-primary btn-block" (click)="close()">
            Awesome! Let's Continue
          </button>
        </div>
      </div>
    </div>
  `
})
export class FirstUploadModalComponent {
  @Output() closeModal = new EventEmitter<void>();
  hasLocationBonus = true; // Can be passed as @Input if needed
  
  get totalPoints(): number {
    return 60 + (this.hasLocationBonus ? 5 : 0);
  }

  close(): void {
    this.closeModal.emit();
  }
}
