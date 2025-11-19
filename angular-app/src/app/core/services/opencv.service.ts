import { Injectable } from '@angular/core';

export interface Rectangle {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Point {
  x: number;
  y: number;
}

@Injectable({
  providedIn: 'root'
})
export class OpenCVService {
  private worker: Worker | null = null;
  private workerLoaded = false;
  private loadingPromise: Promise<void> | null = null;
  private messageIdCounter = 0;
  private pendingMessages = new Map<number, { resolve: (value: any) => void, reject: (reason: any) => void }>();

  constructor() {
    this.initWorker();
  }

  private initWorker() {
    if (typeof Worker !== 'undefined') {
      this.worker = new Worker(new URL('../workers/opencv.worker', import.meta.url));
      this.worker.onmessage = ({ data }) => {
        const { id, type, payload, error } = data;
        if (this.pendingMessages.has(id)) {
          const { resolve, reject } = this.pendingMessages.get(id)!;
          this.pendingMessages.delete(id);
          if (error) {
            reject(new Error(error));
          } else {
            resolve(payload);
          }
        }
      };
    } else {
      console.error('Web Workers are not supported in this environment.');
    }
  }

  private postMessage(type: string, payload: any = {}): Promise<any> {
    if (!this.worker) {
      return Promise.reject(new Error('Worker not initialized'));
    }
    const id = this.messageIdCounter++;
    return new Promise((resolve, reject) => {
      this.pendingMessages.set(id, { resolve, reject });
      this.worker!.postMessage({ id, type, payload });
    });
  }

  /**
   * Load OpenCV.js library in the worker
   */
  async loadOpenCV(): Promise<void> {
    if (this.workerLoaded) return;
    if (this.loadingPromise) return this.loadingPromise;

    this.loadingPromise = this.postMessage('LOAD').then(() => {
      this.workerLoaded = true;
      console.log('✓ OpenCV.js Worker initialized');
    });
    return this.loadingPromise;
  }

  /**
   * Detect receipt boundaries and crop automatically
   */
  async cropReceipt(blob: Blob): Promise<Blob> {
    await this.loadOpenCV();
    const result = await this.postMessage('CROP', { blob });
    return result.blob;
  }

  /**
   * Enhance image for better OCR results
   */
  async enhanceForOCR(blob: Blob): Promise<Blob> {
    await this.loadOpenCV();
    const result = await this.postMessage('ENHANCE', { blob });
    return result.blob;
  }

  /**
   * Optimize image size before upload
   */
  async optimizeImage(blob: Blob, maxWidth: number = 1024): Promise<Blob> {
    await this.loadOpenCV();
    const result = await this.postMessage('OPTIMIZE', { blob, maxWidth });
    return result.blob;
  }

  /**
   * Check if OpenCV is loaded
   */
  isLoaded(): boolean {
    return this.workerLoaded;
  }
}
