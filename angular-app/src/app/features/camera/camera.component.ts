import { Component, signal, inject, ViewChild, ElementRef, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CameraService } from '../../core/services/camera.service';
import { ReceiptService } from '../../core/services/receipt.service';
import { OpenCVService } from '../../core/services/opencv.service';
import { Receipt } from '../../core/models/receipt.model';
import { MyrPipe } from '../../core/pipes/myr.pipe';
import { CameraOverlayComponent } from './components/camera-overlay.component';

@Component({
  selector: 'app-camera',
  standalone: true,
  imports: [
    CommonModule,
    MyrPipe,
    FormsModule,
    CameraOverlayComponent
  ],
  templateUrl: './camera.component.html',
  styleUrl: './camera.component.scss'
})
export class CameraComponent {
  private cameraService = inject(CameraService);
  private receiptService = inject(ReceiptService);
  private opencvService = inject(OpenCVService);

  // State signals
  capturedImage = signal<string | null>(null);
  isUploading = signal(false);
  uploadProgress = signal(0);
  processedReceipt = signal<Receipt | null>(null);
  isProcessing = signal(false);
  opencvLoaded = signal(false);
  opencvLoading = signal(false);

  // Camera State
  showCamera = signal(false);
  stream: MediaStream | null = null;
  @ViewChild('videoElement') videoElement!: ElementRef<HTMLVideoElement>;

  // Toast state
  toastMessage = signal<string | null>(null);
  toastType = signal<'success' | 'error'>('success');

  // Processing options
  autoCrop = signal(false);

  // Editing state
  isEditing = signal(false);
  editedReceipt: Partial<Receipt> = {};

  startEditing() {
    const receipt = this.processedReceipt();
    if (receipt) {
      this.editedReceipt = { ...receipt };
      this.isEditing.set(true);
    }
  }

  cancelEditing() {
    this.isEditing.set(false);
    this.editedReceipt = {};
  }

  saveEditing() {
    if (this.processedReceipt() && this.editedReceipt) {
      const updatedReceipt = { ...this.processedReceipt()!, ...this.editedReceipt } as Receipt;

      this.receiptService.updateReceipt(updatedReceipt).subscribe({
        next: (receipt) => {
          this.processedReceipt.set(receipt);
          this.isEditing.set(false);
          this.showSuccess('Receipt updated successfully');
        },
        error: (error) => {
          console.error('Update error:', error);
          this.showError('Failed to update receipt');
        }
      });
    }
  }

  async ngOnInit() {
    // OpenCV.js is loaded after a short delay
    setTimeout(() => {
      this.loadOpenCV();
    }, 1000);
  }

  private async loadOpenCV() {
    try {
      this.opencvLoading.set(true);
      console.log('Loading OpenCV.js in background...');

      await this.opencvService.loadOpenCV();

      this.opencvLoaded.set(true);
      this.opencvLoading.set(false);

      // Enable processing options by default after loading
      this.autoCrop.set(true);

      console.log('✓ OpenCV.js ready for image processing');
    } catch (error) {
      console.error('Failed to load OpenCV.js:', error);
      this.opencvLoaded.set(false);
      this.opencvLoading.set(false);
      console.log('Continuing without OpenCV - images will be uploaded directly');
    }
  }

  ngOnDestroy() {
    this.stopCamera();
  }

  // ... (keep existing OpenCV methods) ...

  async startCamera() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        }
      });
      this.showCamera.set(true);

      // Allow UI to update before accessing video element
      setTimeout(() => {
        if (this.videoElement) {
          this.videoElement.nativeElement.srcObject = this.stream;
        }
      }, 100);
    } catch (error) {
      console.error('Camera error:', error);
      this.showError('Failed to access camera. Please check permissions.');
      // Fallback to native camera
      this.takePhotoNative();
    }
  }

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.showCamera.set(false);
  }

  async processImage(blob: Blob, filename: string) {
    this.isProcessing.set(true);
    this.processedReceipt.set(null);

    try {
      // Auto-Crop (if enabled and OpenCV loaded)
      let processedBlob = blob;
      if (this.opencvLoaded() && this.autoCrop()) {
        console.log('Auto-cropping receipt...');
        try {
          const croppedBlob = await this.opencvService.cropReceipt(blob);
          if (croppedBlob.size > 0) {
            processedBlob = croppedBlob;
            console.log('Auto-crop successful');
          }
        } catch (cropError) {
          console.warn('Auto-crop failed, using original image:', cropError);
        }
      }

      // Update preview with processed image
      const dataUrl = await this.blobToDataUrl(processedBlob);
      this.capturedImage.set(dataUrl);
      this.isProcessing.set(false);

      // Upload directly to backend
      await this.uploadImage(processedBlob, filename);
    } catch (error) {
      console.error('Processing error:', error);
      this.showError('Failed to process image');
      this.isProcessing.set(false);
    }
  }

  async capturePhoto() {
    if (!this.videoElement) return;

    const video = this.videoElement.nativeElement;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(video, 0, 0);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
    this.stopCamera();

    const blob = await (await fetch(dataUrl)).blob();
    await this.processImage(blob, `receipt_${Date.now()}.jpg`);
  }

  async takePhotoNative() {
    try {
      const image = await this.cameraService.takePhoto();
      await this.processImage(image.blob, image.filename);
    } catch (error: any) {
      // Ignore user cancellation
      if (error.message?.includes('User cancelled') || error.message?.includes('cancelled')) {
        return;
      }
      console.error('Camera error:', error);
      this.showError(error.message || 'Failed to take photo');
    }
  }

  async selectFromGallery() {
    try {
      const image = await this.cameraService.selectFromGallery();
      await this.processImage(image.blob, image.filename);
    } catch (error: any) {
      // Ignore user cancellation
      if (error.message?.includes('User cancelled') || error.message?.includes('cancelled')) {
        return;
      }
      console.error('Gallery error:', error);
      this.showError(error.message || 'Failed to select image');
    }
  }



  /**
   * Convert Blob to Data URL for preview
   */
  private blobToDataUrl(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
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
    this.toastMessage.set(message);
    this.toastType.set('success');
    setTimeout(() => this.toastMessage.set(null), 3000);
  }

  private showError(message: string) {
    this.toastMessage.set(message);
    this.toastType.set('error');
    setTimeout(() => this.toastMessage.set(null), 5000);
  }
}
