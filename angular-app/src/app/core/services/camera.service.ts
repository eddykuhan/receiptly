import { Injectable } from '@angular/core';
import { Camera, CameraResultType, CameraSource, Photo } from '@capacitor/camera';
import heic2any from 'heic2any';

export interface CapturedImage {
  dataUrl: string;
  blob: Blob;
  filename: string;
}

@Injectable({
  providedIn: 'root'
})
export class CameraService {
  
  /**
   * Take a photo using device camera
   */
  async takePhoto(): Promise<CapturedImage> {
    const image = await Camera.getPhoto({
      quality: 90,
      allowEditing: false,
      resultType: CameraResultType.DataUrl,
      source: CameraSource.Camera
    });
    
    return this.processPhoto(image);
  }
  
  /**
   * Select image from gallery
   */
  async selectFromGallery(): Promise<CapturedImage> {
    const image = await Camera.getPhoto({
      quality: 90,
      allowEditing: false,
      resultType: CameraResultType.DataUrl,
      source: CameraSource.Photos
    });
    
    return this.processPhoto(image);
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
          quality: 0.9
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
    try {
      const permissions = await Camera.checkPermissions();
      return permissions.camera !== 'denied';
    } catch {
      return false;
    }
  }
  
  /**
   * Request camera permissions
   */
  async requestPermissions(): Promise<boolean> {
    try {
      const permissions = await Camera.requestPermissions();
      return permissions.camera === 'granted';
    } catch {
      return false;
    }
  }
}
