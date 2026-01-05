import { Injectable } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import heic2any from 'heic2any';

// Dynamic import types for Capacitor Camera
type Camera = typeof import('@capacitor/camera').Camera;
type Photo = import('@capacitor/camera').Photo;
type CameraResultType = typeof import('@capacitor/camera').CameraResultType;
type CameraSource = typeof import('@capacitor/camera').CameraSource;

export interface CapturedImage {
  dataUrl: string;
  blob: Blob;
  filename: string;
}

@Injectable({
  providedIn: 'root'
})
export class CameraService {
  private isNative = Capacitor.isNativePlatform();
  
  /**
   * Take a photo using device camera
   */
  async takePhoto(): Promise<CapturedImage> {
    if (this.isNative) {
      return this.takePhotoNative();
    } else {
      return this.takePhotoWeb('camera');
    }
  }
  
  /**
   * Select image from gallery
   */
  async selectFromGallery(): Promise<CapturedImage> {
    if (this.isNative) {
      return this.selectFromGalleryNative();
    } else {
      return this.takePhotoWeb('gallery');
    }
  }

  /**
   * Take photo using Capacitor (native platforms)
   */
  private async takePhotoNative(): Promise<CapturedImage> {
    const { Camera, CameraResultType, CameraSource } = await import('@capacitor/camera');
    
    const image = await Camera.getPhoto({
      quality: 95,
      allowEditing: false,
      resultType: CameraResultType.DataUrl,
      source: CameraSource.Camera,
      width: 1920,
      correctOrientation: true
    });
    
    return this.processPhoto(image);
  }

  /**
   * Select from gallery using Capacitor (native platforms)
   */
  private async selectFromGalleryNative(): Promise<CapturedImage> {
    const { Camera, CameraResultType, CameraSource } = await import('@capacitor/camera');
    
    const image = await Camera.getPhoto({
      quality: 95,
      allowEditing: false,
      resultType: CameraResultType.DataUrl,
      source: CameraSource.Photos,
      width: 1920,
      correctOrientation: true
    });
    
    return this.processPhoto(image);
  }

  /**
   * Take photo using web browser (HTML5)
   */
  private async takePhotoWeb(mode: 'camera' | 'gallery'): Promise<CapturedImage> {
    return new Promise((resolve, reject) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      
      // Use camera on mobile web if available
      if (mode === 'camera') {
        input.capture = 'environment';
      }
      
      input.onchange = async (event: Event) => {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];
        
        if (!file) {
          reject(new Error('No file selected'));
          return;
        }
        
        try {
          let blob: Blob = file;
          let filename = file.name;
          
          // Convert HEIC if necessary
          if (file.type === 'image/heic' || file.type === 'image/heif' || 
              file.name.toLowerCase().endsWith('.heic') || file.name.toLowerCase().endsWith('.heif')) {
            console.log('HEIC image detected, converting to JPEG...');
            try {
              const convertedBlob = await heic2any({
                blob: file,
                toType: 'image/jpeg',
                quality: 0.95
              });
              
              blob = Array.isArray(convertedBlob) ? convertedBlob[0] : convertedBlob;
              filename = file.name.replace(/\.(heic|heif)$/i, '.jpg');
              console.log('HEIC conversion successful');
            } catch (error) {
              console.error('HEIC conversion failed:', error);
              throw new Error('Failed to convert HEIC image. Please try a different format.');
            }
          }
          
          const dataUrl = await this.blobToDataUrl(blob);
          
          resolve({
            dataUrl,
            blob,
            filename
          });
        } catch (error) {
          reject(error);
        }
      };
      
      input.onerror = () => reject(new Error('File selection cancelled'));
      input.click();
    });
  }
  
  /**
   * Process Capacitor photo into usable format
   */
  private async processPhoto(photo: Photo): Promise<CapturedImage> {
    const dataUrl = photo.dataUrl!;
    let blob = await this.dataUrlToBlob(dataUrl);
    let filename = `receipt_${Date.now()}.${photo.format || 'jpg'}`;
    
    // Convert HEIC to JPEG if necessary
    if (blob.type === 'image/heic' || blob.type === 'image/heif' || 
        photo.format?.toLowerCase() === 'heic' || photo.format?.toLowerCase() === 'heif') {
      console.log('HEIC image detected, converting to JPEG...');
      try {
        const convertedBlob = await heic2any({
          blob: blob,
          toType: 'image/jpeg',
          quality: 0.95
        });
        
        // heic2any can return Blob or Blob[]
        blob = Array.isArray(convertedBlob) ? convertedBlob[0] : convertedBlob;
        filename = `receipt_${Date.now()}.jpg`;
        console.log('HEIC conversion successful');
      } catch (error) {
        console.error('HEIC conversion failed:', error);
        throw new Error('Failed to convert HEIC image. Please try a different format.');
      }
    }
    
    return {
      dataUrl: await this.blobToDataUrl(blob),
      blob,
      filename
    };
  }
  
  /**
   * Convert data URL to Blob
   */
  private async dataUrlToBlob(dataUrl: string): Promise<Blob> {
    const response = await fetch(dataUrl);
    return response.blob();
  }
  
  /**
   * Convert Blob to data URL
   */
  private async blobToDataUrl(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }
  
  /**
   * Check if camera is available
   */
  async isCameraAvailable(): Promise<boolean> {
    if (this.isNative) {
      try {
        const { Camera } = await import('@capacitor/camera');
        const permissions = await Camera.checkPermissions();
        return permissions.camera !== 'denied';
      } catch {
        return false;
      }
    } else {
      // On web, check if getUserMedia is available
      return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }
  }
  
  /**
   * Request camera permissions
   */
  async requestPermissions(): Promise<boolean> {
    if (this.isNative) {
      try {
        const { Camera } = await import('@capacitor/camera');
        const permissions = await Camera.requestPermissions();
        return permissions.camera === 'granted';
      } catch {
        return false;
      }
    } else {
      // On web, permissions are handled by the browser when accessing camera
      return true;
    }
  }
}
