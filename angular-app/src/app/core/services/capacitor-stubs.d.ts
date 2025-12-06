/**
 * Type stubs for Capacitor when not available
 * This helps TypeScript resolve types during web builds
 */

declare module '@capacitor/camera' {
  export interface Photo {
    dataUrl?: string;
    format?: string;
    path?: string;
    webPath?: string;
    exif?: any;
    saved: boolean;
  }

  export enum CameraResultType {
    Uri = 'uri',
    Base64 = 'base64',
    DataUrl = 'dataUrl'
  }

  export enum CameraSource {
    Prompt = 'PROMPT',
    Camera = 'CAMERA',
    Photos = 'PHOTOS'
  }

  export interface CameraOptions {
    quality?: number;
    allowEditing?: boolean;
    resultType?: CameraResultType;
    source?: CameraSource;
  }

  export interface PermissionStatus {
    camera: 'granted' | 'denied' | 'prompt';
    photos: 'granted' | 'denied' | 'prompt';
  }

  export const Camera: {
    getPhoto(options: CameraOptions): Promise<Photo>;
    checkPermissions(): Promise<PermissionStatus>;
    requestPermissions(): Promise<PermissionStatus>;
  };
}
