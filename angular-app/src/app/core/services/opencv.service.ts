import { Injectable } from '@angular/core';

declare var cv: any;

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
  private cvLoaded = false;
  private loadingPromise: Promise<void> | null = null;

  constructor() { }

  /**
   * Load OpenCV.js library in the main thread
   */
  async loadOpenCV(): Promise<void> {
    if (this.cvLoaded) return;
    if (this.loadingPromise) return this.loadingPromise;

    this.loadingPromise = new Promise<void>((resolve, reject) => {
      // Check if already loaded globally
      if (typeof cv !== 'undefined') {
        this.cvLoaded = true;
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.src = '/opencv.js';
      script.async = true;
      script.type = 'text/javascript';

      script.onload = () => {
        // OpenCV.js is loaded, but we need to wait for initialization
        // The WASM build typically sets a global Module object or we wait for cv.onRuntimeInitialized
        if (typeof cv !== 'undefined' && cv.onRuntimeInitialized) {
          // It's already initialized or has a callback
          this.cvLoaded = true;
          console.log('✓ OpenCV.js loaded');
          resolve();
        } else {
          // Wait for the runtime to initialize
          cv['onRuntimeInitialized'] = () => {
            this.cvLoaded = true;
            console.log('✓ OpenCV.js initialized');
            resolve();
          };
        }
      };

      script.onerror = (err) => {
        console.error('Failed to load OpenCV.js', err);
        reject(err);
      };

      document.body.appendChild(script);
    });

    return this.loadingPromise;
  }

  /**
   * Detect receipt boundaries and crop automatically
   */
  async cropReceipt(blob: Blob): Promise<Blob> {
    await this.loadOpenCV();

    const img = await this.blobToMat(blob);
    const gray = new cv.Mat();
    const blurred = new cv.Mat();
    const edges = new cv.Mat();
    let resultBlob = blob;

    try {
      cv.cvtColor(img, gray, cv.COLOR_RGBA2GRAY);
      cv.GaussianBlur(gray, blurred, new cv.Size(5, 5), 0);

      // Adjusted thresholds for better edge detection
      cv.Canny(blurred, edges, 30, 100); // Lowered from 50, 150

      const kernel = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(3, 3));
      cv.dilate(edges, edges, kernel);

      const contours = new cv.MatVector();
      const hierarchy = new cv.Mat();
      cv.findContours(edges, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

      console.log(`Found ${contours.size()} contours`);

      let maxArea = 0;
      let maxContour = null;
      let receiptFound = false;
      const minArea = img.rows * img.cols * 0.05; // Lowered from 0.1 (10% -> 5%)

      for (let i = 0; i < contours.size(); i++) {
        const contour = contours.get(i);
        const area = cv.contourArea(contour);

        if (area > minArea) {
          const peri = cv.arcLength(contour, true);
          const approx = new cv.Mat();
          cv.approxPolyDP(contour, approx, 0.02 * peri, true);

          if (approx.rows === 4 && area > maxArea) {
            maxArea = area;
            if (maxContour) maxContour.delete(); // Clean up previous max
            maxContour = approx.clone();
            receiptFound = true;
          }
          approx.delete();
        }
      }

      if (receiptFound) {
        console.log('Receipt contour found with area:', maxArea);
      } else {
        console.warn('No receipt contour found. Max area was:', maxArea);
      }

      if (receiptFound && maxContour) {
        const srcPoints = this.orderPoints(maxContour);
        const width = 800;
        const height = Math.round(width * 1.4);

        const dstPoints = cv.matFromArray(4, 1, cv.CV_32FC2, [
          0, 0,
          width, 0,
          width, height,
          0, height
        ]);

        const M = cv.getPerspectiveTransform(srcPoints, dstPoints);
        const warped = new cv.Mat();
        cv.warpPerspective(img, warped, M, new cv.Size(width, height));

        resultBlob = await this.matToBlob(warped);

        warped.delete();
        M.delete();
        dstPoints.delete();
        srcPoints.delete();
        maxContour.delete();
      }

      contours.delete();
      hierarchy.delete();
      kernel.delete();
    } catch (e) {
      console.error('Error cropping', e);
    } finally {
      img.delete();
      gray.delete();
      blurred.delete();
      edges.delete();
    }

    return resultBlob;
  }



  /**
   * Check if OpenCV is loaded
   */
  isLoaded(): boolean {
    return this.cvLoaded;
  }

  // Helpers

  private async blobToMat(blob: Blob): Promise<any> {
    const imgBitmap = await createImageBitmap(blob);
    const canvas = document.createElement('canvas');
    canvas.width = imgBitmap.width;
    canvas.height = imgBitmap.height;
    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(imgBitmap, 0, 0);
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    return cv.matFromImageData(imageData);
  }

  private async matToBlob(mat: any, type: string = 'image/jpeg', quality: number = 0.95): Promise<Blob> {
    const canvas = document.createElement('canvas');
    canvas.width = mat.cols;
    canvas.height = mat.rows;
    cv.imshow(canvas, mat);

    return new Promise((resolve) => {
      canvas.toBlob((blob) => {
        resolve(blob!);
      }, type, quality);
    });
  }

  private orderPoints(points: any): any {
    const rect = new Array(4);
    const pointsArray = [];

    for (let i = 0; i < points.rows; i++) {
      pointsArray.push({
        x: points.data32S[i * 2],
        y: points.data32S[i * 2 + 1]
      });
    }

    const sorted = pointsArray.sort((a, b) => a.y - b.y);
    const topPoints = sorted.slice(0, 2).sort((a, b) => a.x - b.x);
    rect[0] = topPoints[0];
    rect[1] = topPoints[1];
    const bottomPoints = sorted.slice(2, 4).sort((a, b) => a.x - b.x);
    rect[2] = bottomPoints[1];
    rect[3] = bottomPoints[0];

    return cv.matFromArray(4, 1, cv.CV_32FC2, [
      rect[0].x, rect[0].y,
      rect[1].x, rect[1].y,
      rect[2].x, rect[2].y,
      rect[3].x, rect[3].y
    ]);
  }
}
