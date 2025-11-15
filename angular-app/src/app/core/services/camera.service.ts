import { Injectable } from '@angular/core';
import { Camera, CameraResultType, CameraSource, Photo } from '@capacitor/camera';

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
    const blob = await this.dataUrlToBlob(dataUrl);
    const filename = `receipt_${Date.now()}.${photo.format || 'jpg'}`;
    
    return {
      dataUrl,
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
