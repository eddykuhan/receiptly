import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { CameraService } from '../../core/services/camera.service';
import { ReceiptService } from '../../core/services/receipt.service';
import { Receipt } from '../../core/models/receipt.model';

@Component({
  selector: 'app-camera',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatSnackBarModule
  ],
  templateUrl: './camera.component.html',
  styleUrl: './camera.component.scss'
})
export class CameraComponent {
  private cameraService = inject(CameraService);
  private receiptService = inject(ReceiptService);
  private snackBar = inject(MatSnackBar);
  
  // State signals
  capturedImage = signal<string | null>(null);
  isUploading = signal(false);
  uploadProgress = signal(0);
  processedReceipt = signal<Receipt | null>(null);
  
  async takePhoto() {
    try {
      const hasPermission = await this.cameraService.requestPermissions();
      if (!hasPermission) {
        this.showError('Camera permission denied');
        return;
      }
      
      const image = await this.cameraService.takePhoto();
      this.capturedImage.set(image.dataUrl);
      this.processedReceipt.set(null);
      
      // Auto-upload after capture
      await this.uploadImage(image.blob, image.filename);
    } catch (error: any) {
      console.error('Camera error:', error);
      this.showError(error.message || 'Failed to take photo');
    }
  }
  
  async selectFromGallery() {
    try {
      const image = await this.cameraService.selectFromGallery();
      this.capturedImage.set(image.dataUrl);
      this.processedReceipt.set(null);
      
      // Auto-upload after selection
      await this.uploadImage(image.blob, image.filename);
    } catch (error: any) {
      console.error('Gallery error:', error);
      this.showError(error.message || 'Failed to select image');
    }
  }
  
  private async uploadImage(blob: Blob, filename: string) {
    this.isUploading.set(true);
    this.uploadProgress.set(0);
    
    // Simulate progress (real progress tracking would need backend support)
    const progressInterval = setInterval(() => {
      const current = this.uploadProgress();
      if (current < 90) {
        this.uploadProgress.set(current + 10);
      }
    }, 200);
    
    this.receiptService.uploadReceipt(blob, filename).subscribe({
      next: (response) => {
        clearInterval(progressInterval);
        this.uploadProgress.set(100);
        this.isUploading.set(false);
        
        if (response.success && response.receipt) {
          this.processedReceipt.set(response.receipt);
          this.showSuccess('Receipt processed successfully!');
        }
      },
      error: (error) => {
        clearInterval(progressInterval);
        this.isUploading.set(false);
        this.uploadProgress.set(0);
        
        if (error.existingReceiptId) {
          this.showError('Duplicate receipt detected!');
        } else {
          this.showError(error.error || 'Failed to upload receipt');
        }
      }
    });
  }
  
  clearImage() {
    this.capturedImage.set(null);
    this.processedReceipt.set(null);
    this.uploadProgress.set(0);
  }
  
  private showSuccess(message: string) {
    this.snackBar.open(message, 'Close', {
      duration: 3000,
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
      panelClass: ['success-snackbar']
    });
  }
  
  private showError(message: string) {
    this.snackBar.open(message, 'Close', {
      duration: 5000,
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
      panelClass: ['error-snackbar']
    });
  }
}
