import { Component, signal, inject, ViewChild, ElementRef, OnDestroy, OnInit, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CameraService } from '../../core/services/camera.service';
import { ReceiptService } from '../../core/services/receipt.service';
import { OpenCVService } from '../../core/services/opencv.service';
import { Receipt } from '../../core/models/receipt.model';
import { MyrPipe } from '../../core/pipes/myr.pipe';
import { ReceiptProcessingService } from '../../core/services/receipt-processing.service';
import { Router } from '@angular/router';
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
  private receiptProcessingService = inject(ReceiptProcessingService);
  private router = inject(Router);

  // State signals
  // State signals
  capturedImage = signal<string | null>(null);

  // Processing state from service
  activeUploads = this.receiptProcessingService.activeUploads;
  hasActiveUploads = computed(() => this.activeUploads().length > 0);

  // Local state
  isUploading = signal(false); // Deprecated, kept for backward compatibility if needed, but logic moved to service
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
  autoCrop = signal(true); // Auto crop enabled by default

  // Editing state
  isEditing = signal(false);
  editedReceipt: Partial<Receipt> = {};

  // Funny messages for upload progress
  private funnyMessages = [
    '🤔 Decoding your shopping secrets...',
    '📊 Converting pixels to prices...',
    '🎯 Teaching AI to read receipts...',
    '💰 Counting your beans (literally)...',
    '🔍 Finding those sneaky charges...',
    '📱 Asking ChatGPT for help...',
    '✨ Making sense of hieroglyphics...',
    '🎨 Translating receipt art...',
    '🧠 Exercising our AI brain...',
    '🎭 Deciphering merchant handwriting...',
    '🚀 Processing at light speed...',
    '💡 Calculating your regrets...',
    '🎪 Performing receipt magic...',
    '🌟 Turning receipts into wisdom...',
    '📜 Reading the scroll of expenses...'
  ];
  
  currentFunnyMessage = signal(0);
  private messageRotationInterval: ReturnType<typeof setInterval> | null = null;
  private messageTimer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    // Set up message rotation effect in constructor (proper injection context)
    effect(() => {
      if (this.hasActiveUploads()) {
        this.startMessageRotation();
      } else {
        this.stopMessageRotation();
      }
    });
  }

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

  // Get current funny message and rotate through them
  getFunnyMessage(): string {
    return this.funnyMessages[this.currentFunnyMessage()];
  }

  // Start rotating funny messages during upload
  private startMessageRotation() {
    // Clear any existing intervals
    if (this.messageRotationInterval) {
      clearInterval(this.messageRotationInterval);
      this.messageRotationInterval = null;
    }
    if (this.messageTimer) {
      clearInterval(this.messageTimer);
      this.messageTimer = null;
    }
    
    // Reset to first message when starting
    this.currentFunnyMessage.set(0);
    
    // Rotate through messages every 2.5 seconds
    this.messageTimer = setInterval(() => {
      const nextIndex = (this.currentFunnyMessage() + 1) % this.funnyMessages.length;
      this.currentFunnyMessage.set(nextIndex);
    }, 2500);
  }

  // Stop rotating messages
  private stopMessageRotation() {
    if (this.messageTimer) {
      clearInterval(this.messageTimer);
      this.messageTimer = null;
    }
    if (this.messageRotationInterval) {
      clearInterval(this.messageRotationInterval);
      this.messageRotationInterval = null;
    }
    // Reset to first message
    this.currentFunnyMessage.set(0);
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
    console.log('🚀 Starting background upload:', filename);

    // Delegate to processing service
    this.receiptProcessingService.processReceipt(blob, filename);

    // Clear local state immediately for next scan
    this.clearImage();

    // Provide immediate feedback to user
    // We rely on the service's toasts, but we can also do a redirect here if preferred.
    // For now, let's keep the user on the camera screen but reset it, 
    // effectively allowing them to "Navigate away" or generic use since it's non-blocking.

    // Optional: Redirect to history if that's the desired UX flow "After scan, go to history"
    // this.router.navigate(['/history']); 
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
