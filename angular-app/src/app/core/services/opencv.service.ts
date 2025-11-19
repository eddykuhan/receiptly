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
  private cv: any;
  private loaded = false;
  private loadingPromise: Promise<any> | null = null;

  /**
   * Load OpenCV.js library
   */
  async loadOpenCV(): Promise<any> {
    if (this.loaded) {
      return this.cv;
    }

    if (this.loadingPromise) {
      return this.loadingPromise;
    }

    this.loadingPromise = new Promise((resolve, reject) => {
      // Check if already loaded
      if ((window as any).cv && (window as any).cv.Mat) {
        this.cv = (window as any).cv;
        this.loaded = true;
        resolve(this.cv);
        return;
      }

      // Set a timeout to prevent indefinite hanging
      const timeout = setTimeout(() => {
        reject(new Error('OpenCV.js loading timeout after 30 seconds'));
      }, 30000);

      const script = document.createElement('script');
      script.src = 'https://docs.opencv.org/4.8.0/opencv.js';
      script.async = true;
      script.defer = true;

      script.onload = () => {
        if ((window as any).cv) {
          // Use a separate timeout for WASM initialization
          const initTimeout = setTimeout(() => {
            clearTimeout(timeout);
            reject(new Error('OpenCV WASM initialization timeout'));
          }, 20000);
          
          (window as any).cv['onRuntimeInitialized'] = () => {
            clearTimeout(timeout);
            clearTimeout(initTimeout);
            this.cv = (window as any).cv;
            this.loaded = true;
            console.log('✓ OpenCV.js WebAssembly initialized');
            resolve(this.cv);
          };
        } else {
          clearTimeout(timeout);
          reject(new Error('OpenCV failed to load'));
        }
      };

      script.onerror = () => {
        clearTimeout(timeout);
        reject(new Error('Failed to load OpenCV.js script'));
      };

      document.body.appendChild(script);
    });

    return this.loadingPromise;
  }  /**
   * Detect receipt boundaries and crop automatically
   */
  async cropReceipt(blob: Blob): Promise<Blob> {
    try {
      const cv = await this.loadOpenCV();
      const img = await this.blobToMat(blob);

      const gray = new cv.Mat();
      const blurred = new cv.Mat();
      const edges = new cv.Mat();

      // Convert to grayscale
      cv.cvtColor(img, gray, cv.COLOR_RGBA2GRAY);

      // Gaussian blur to reduce noise
      cv.GaussianBlur(gray, blurred, new cv.Size(5, 5), 0);

      // Canny edge detection
      cv.Canny(blurred, edges, 50, 150);

      // Dilate edges to close gaps
      const kernel = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(3, 3));
      cv.dilate(edges, edges, kernel);

      // Find contours
      const contours = new cv.MatVector();
      const hierarchy = new cv.Mat();
      cv.findContours(edges, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

      // Find largest rectangular contour
      let maxArea = 0;
      let maxContour = null;
      let receiptFound = false;

      for (let i = 0; i < contours.size(); i++) {
        const contour = contours.get(i);
        const area = cv.contourArea(contour);

        // Filter by minimum area (receipt should be significant portion of image)
        if (area > img.rows * img.cols * 0.1) {
          const peri = cv.arcLength(contour, true);
          const approx = new cv.Mat();
          cv.approxPolyDP(contour, approx, 0.02 * peri, true);

          // Check if it's a quadrilateral (4 corners)
          if (approx.rows === 4 && area > maxArea) {
            maxArea = area;
            maxContour = approx.clone();
            receiptFound = true;
          }

          approx.delete();
        }
      }

      let result: Blob;

      // Perform perspective transform if receipt found
      if (receiptFound && maxContour) {
        const srcPoints = this.orderPoints(maxContour);
        const width = 800;
        const height = Math.round(width * 1.4); // Standard receipt aspect ratio

        const dstPoints = cv.matFromArray(4, 1, cv.CV_32FC2, [
          0, 0,
          width, 0,
          width, height,
          0, height
        ]);

        const M = cv.getPerspectiveTransform(srcPoints, dstPoints);
        const warped = new cv.Mat();
        cv.warpPerspective(img, warped, M, new cv.Size(width, height));

        result = await this.matToBlob(warped);
        
        warped.delete();
        M.delete();
        dstPoints.delete();
        srcPoints.delete();
        maxContour.delete();
      } else {
        // No receipt detected, return original
        console.log('No receipt boundary detected, returning original image');
        result = blob;
      }

      // Cleanup
      img.delete();
      gray.delete();
      blurred.delete();
      edges.delete();
      kernel.delete();
      contours.delete();
      hierarchy.delete();

      return result;
    } catch (error) {
      console.error('Error cropping receipt:', error);
      return blob; // Return original on error
    }
  }

  /**
   * Enhance image for better OCR results
   */
  async enhanceForOCR(blob: Blob): Promise<Blob> {
    try {
      const cv = await this.loadOpenCV();
      const img = await this.blobToMat(blob);

      // Convert to grayscale
      const gray = new cv.Mat();
      cv.cvtColor(img, gray, cv.COLOR_RGBA2GRAY);

      // Adaptive threshold for better text contrast
      const thresh = new cv.Mat();
      cv.adaptiveThreshold(
        gray,
        thresh,
        255,
        cv.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv.THRESH_BINARY,
        11,
        2
      );

      // Remove noise with morphological operations
      const kernel = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(1, 1));
      cv.morphologyEx(thresh, thresh, cv.MORPH_CLOSE, kernel);

      // Optional: Denoise
      const denoised = new cv.Mat();
      cv.fastNlMeansDenoising(thresh, denoised, 10, 7, 21);

      const result = await this.matToBlob(denoised);

      // Cleanup
      img.delete();
      gray.delete();
      thresh.delete();
      kernel.delete();
      denoised.delete();

      return result;
    } catch (error) {
      console.error('Error enhancing image:', error);
      return blob;
    }
  }

  /**
   * Optimize image size before upload
   */
  async optimizeImage(blob: Blob, maxWidth: number = 1024): Promise<Blob> {
    try {
      const cv = await this.loadOpenCV();
      const img = await this.blobToMat(blob);

      // Calculate new dimensions maintaining aspect ratio
      let scale = 1;
      let newWidth = img.cols;
      let newHeight = img.rows;

      if (img.cols > maxWidth) {
        scale = maxWidth / img.cols;
        newWidth = maxWidth;
        newHeight = Math.round(img.rows * scale);
      }

      // Resize with high-quality interpolation
      const resized = new cv.Mat();
      cv.resize(img, resized, new cv.Size(newWidth, newHeight), 0, 0, cv.INTER_AREA);

      const result = await this.matToBlob(resized, 'image/jpeg', 0.85);

      // Cleanup
      img.delete();
      resized.delete();

      return result;
    } catch (error) {
      console.error('Error optimizing image:', error);
      return blob;
    }
  }

  /**
   * Detect receipt in real-time for camera preview
   */
  async detectReceiptContours(imageData: ImageData): Promise<Point[][]> {
    try {
      const cv = await this.loadOpenCV();
      const src = cv.matFromImageData(imageData);
      const gray = new cv.Mat();
      const blurred = new cv.Mat();
      const edges = new cv.Mat();

      // Convert to grayscale
      cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);

      // Blur
      cv.GaussianBlur(gray, blurred, new cv.Size(5, 5), 0);

      // Edge detection
      cv.Canny(blurred, edges, 50, 150);

      // Find contours
      const contours = new cv.MatVector();
      const hierarchy = new cv.Mat();
      cv.findContours(edges, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

      const detectedContours: Point[][] = [];

      for (let i = 0; i < contours.size(); i++) {
        const contour = contours.get(i);
        const area = cv.contourArea(contour);

        // Filter by size
        if (area > imageData.width * imageData.height * 0.1) {
          const peri = cv.arcLength(contour, true);
          const approx = new cv.Mat();
          cv.approxPolyDP(contour, approx, 0.02 * peri, true);

          // Get quadrilateral
          if (approx.rows === 4) {
            const points: Point[] = [];
            for (let j = 0; j < approx.rows; j++) {
              points.push({
                x: approx.data32S[j * 2],
                y: approx.data32S[j * 2 + 1]
              });
            }
            detectedContours.push(points);
          }

          approx.delete();
        }
      }

      // Cleanup
      src.delete();
      gray.delete();
      blurred.delete();
      edges.delete();
      contours.delete();
      hierarchy.delete();

      return detectedContours;
    } catch (error) {
      console.error('Error detecting contours:', error);
      return [];
    }
  }

  /**
   * Helper: Convert Blob to OpenCV Mat
   */
  private async blobToMat(blob: Blob): Promise<any> {
    const cv = await this.loadOpenCV();
    const img = await createImageBitmap(blob);
    const canvas = document.createElement('canvas');
    canvas.width = img.width;
    canvas.height = img.height;
    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(img, 0, 0);
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    return cv.matFromImageData(imageData);
  }

  /**
   * Helper: Convert OpenCV Mat to Blob
   */
  private async matToBlob(
    mat: any,
    type: string = 'image/png',
    quality: number = 1
  ): Promise<Blob> {
    return new Promise((resolve, reject) => {
      const canvas = document.createElement('canvas');
      this.cv.imshow(canvas, mat);
      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob);
          } else {
            reject(new Error('Failed to convert Mat to Blob'));
          }
        },
        type,
        quality
      );
    });
  }

  /**
   * Order points for perspective transform (top-left, top-right, bottom-right, bottom-left)
   */
  private orderPoints(points: any): any {
    const cv = this.cv;
    const rect = new Array(4);
    const pointsArray: Point[] = [];

    // Extract points from Mat
    for (let i = 0; i < points.rows; i++) {
      pointsArray.push({
        x: points.data32S[i * 2],
        y: points.data32S[i * 2 + 1]
      });
    }

    // Sort by y-coordinate to separate top and bottom points
    const sorted = pointsArray.sort((a, b) => a.y - b.y);

    // Top two points
    const topPoints = sorted.slice(0, 2).sort((a, b) => a.x - b.x);
    rect[0] = topPoints[0]; // top-left
    rect[1] = topPoints[1]; // top-right

    // Bottom two points
    const bottomPoints = sorted.slice(2, 4).sort((a, b) => a.x - b.x);
    rect[2] = bottomPoints[1]; // bottom-right
    rect[3] = bottomPoints[0]; // bottom-left

    return cv.matFromArray(4, 1, cv.CV_32FC2, [
      rect[0].x, rect[0].y,
      rect[1].x, rect[1].y,
      rect[2].x, rect[2].y,
      rect[3].x, rect[3].y
    ]);
  }

  /**
   * Check if OpenCV is loaded
   */
  isLoaded(): boolean {
    return this.loaded;
  }
}
