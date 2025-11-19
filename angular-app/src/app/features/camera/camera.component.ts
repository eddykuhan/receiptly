import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CameraService } from '../../core/services/camera.service';
import { ReceiptService } from '../../core/services/receipt.service';
import { OpenCVService } from '../../core/services/opencv.service';
import { Receipt } from '../../core/models/receipt.model';
import { MyrPipe } from '../../core/pipes/myr.pipe';

@Component({
  selector: 'app-camera',
  standalone: true,
  imports: [
    CommonModule,
    MyrPipe
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

  // Toast state
  toastMessage = signal<string | null>(null);
  toastType = signal<'success' | 'error'>('success');

  // Processing options (disabled by default - OpenCV is optional)
  autoCrop = signal(false);
  enhanceImage = signal(false);
  optimizeSize = signal(false);

  async ngOnInit() {
    // OpenCV.js is disabled by default to prevent UI freezing
    // Uncomment below to enable client-side image processing

    // setTimeout(() => {
    //   this.loadOpenCV();
    // }, 1000);
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
      this.enhanceImage.set(true);
      this.optimizeSize.set(true);

      console.log('✓ OpenCV.js ready for image processing');
    } catch (error) {
      console.error('Failed to load OpenCV.js:', error);
      this.opencvLoaded.set(false);
      this.opencvLoading.set(false);
      console.log('Continuing without OpenCV - images will be uploaded directly');
    }
  }

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

      // Process and upload
      await this.processAndUpload(image.blob, image.filename);
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

      // Process and upload
      await this.processAndUpload(image.blob, image.filename);
    } catch (error: any) {
      console.error('Gallery error:', error);
      this.showError(error.message || 'Failed to select image');
    }
  }

  /**
   * Process image with OpenCV before upload
   */
  private async processAndUpload(blob: Blob, filename: string) {
    let processedBlob = blob;

    // Apply OpenCV processing if enabled and loaded
    if (this.opencvLoaded()) {
      this.isProcessing.set(true);

      try {
        // Step 1: Auto-crop receipt
        if (this.autoCrop()) {
          console.log('Cropping receipt...');
          const croppedBlob = await this.opencvService.cropReceipt(blob);
          if (croppedBlob.size > 0) {
            processedBlob = croppedBlob;

            // Update preview with cropped image
            const dataUrl = await this.blobToDataUrl(processedBlob);
            this.capturedImage.set(dataUrl);
          }
        }

        // Step 2: Enhance for OCR
        if (this.enhanceImage()) {
          console.log('Enhancing image for OCR...');
          processedBlob = await this.opencvService.enhanceForOCR(processedBlob);
        }

        // Step 3: Optimize size
        if (this.optimizeSize()) {
          console.log('Optimizing image size...');
          const originalSize = processedBlob.size;
          processedBlob = await this.opencvService.optimizeImage(processedBlob, 1024);
          const newSize = processedBlob.size;
          console.log(`Image size reduced: ${(originalSize / 1024).toFixed(1)}KB → ${(newSize / 1024).toFixed(1)}KB`);
        }
      } catch (error) {
        console.error('Image processing error:', error);
        this.showError('Image processing failed, uploading original');
        processedBlob = blob; // Fallback to original
      } finally {
        this.isProcessing.set(false);
      }
    }

    // Upload processed image
    await this.uploadImage(processedBlob, filename);
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
