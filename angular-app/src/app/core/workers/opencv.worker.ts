/// <reference lib="webworker" />

declare var cv: any;

addEventListener('message', async ({ data }) => {
    const { id, type, payload } = data;

    try {
        switch (type) {
            case 'LOAD':
                await loadOpenCV();
                postMessage({ id, type, payload: { success: true } });
                break;

            case 'CROP':
                if (!cvLoaded) throw new Error('OpenCV not loaded');
                const croppedBlob = await cropReceipt(payload.blob);
                postMessage({ id, type, payload: { blob: croppedBlob } });
                break;

            case 'ENHANCE':
                if (!cvLoaded) throw new Error('OpenCV not loaded');
                const enhancedBlob = await enhanceForOCR(payload.blob);
                postMessage({ id, type, payload: { blob: enhancedBlob } });
                break;

            case 'OPTIMIZE':
                if (!cvLoaded) throw new Error('OpenCV not loaded');
                const optimizedBlob = await optimizeImage(payload.blob, payload.maxWidth);
                postMessage({ id, type, payload: { blob: optimizedBlob } });
                break;

            default:
                throw new Error(`Unknown message type: ${type}`);
        }
    } catch (error: any) {
        postMessage({
            id,
            type: 'ERROR',
            error: error.message || 'Unknown worker error'
        });
    }
});

let cvLoaded = false;

async function loadOpenCV(): Promise<void> {
    if (cvLoaded) return;

    return new Promise((resolve, reject) => {
        // Define global Module object for OpenCV
        (self as any).Module = {
            onRuntimeInitialized: () => {
                cvLoaded = true;
                console.log('Worker: OpenCV.js initialized');
                resolve();
            },
            onError: (err: any) => {
                reject(err);
            }
        };

        // Import script
        try {
            importScripts('https://docs.opencv.org/4.8.0/opencv.js');
        } catch (e) {
            reject(e);
        }
    });
}

async function cropReceipt(blob: Blob): Promise<Blob> {
    const img = await blobToMat(blob);
    const gray = new cv.Mat();
    const blurred = new cv.Mat();
    const edges = new cv.Mat();
    let resultBlob = blob;

    try {
        cv.cvtColor(img, gray, cv.COLOR_RGBA2GRAY);
        cv.GaussianBlur(gray, blurred, new cv.Size(5, 5), 0);
        cv.Canny(blurred, edges, 50, 150);

        const kernel = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(3, 3));
        cv.dilate(edges, edges, kernel);

        const contours = new cv.MatVector();
        const hierarchy = new cv.Mat();
        cv.findContours(edges, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

        let maxArea = 0;
        let maxContour = null;
        let receiptFound = false;

        for (let i = 0; i < contours.size(); i++) {
            const contour = contours.get(i);
            const area = cv.contourArea(contour);

            if (area > img.rows * img.cols * 0.1) {
                const peri = cv.arcLength(contour, true);
                const approx = new cv.Mat();
                cv.approxPolyDP(contour, approx, 0.02 * peri, true);

                if (approx.rows === 4 && area > maxArea) {
                    maxArea = area;
                    maxContour = approx.clone();
                    receiptFound = true;
                }
                approx.delete();
            }
        }

        if (receiptFound && maxContour) {
            const srcPoints = orderPoints(maxContour);
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

            resultBlob = await matToBlob(warped);

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
        console.error('Worker: Error cropping', e);
    } finally {
        img.delete();
        gray.delete();
        blurred.delete();
        edges.delete();
    }

    return resultBlob;
}

async function enhanceForOCR(blob: Blob): Promise<Blob> {
    const img = await blobToMat(blob);
    const gray = new cv.Mat();
    const thresh = new cv.Mat();
    let resultBlob = blob;

    try {
        cv.cvtColor(img, gray, cv.COLOR_RGBA2GRAY);
        cv.adaptiveThreshold(gray, thresh, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2);

        const kernel = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(1, 1));
        cv.morphologyEx(thresh, thresh, cv.MORPH_CLOSE, kernel);

        const denoised = new cv.Mat();
        cv.fastNlMeansDenoising(thresh, denoised, 10, 7, 21);

        resultBlob = await matToBlob(denoised);

        denoised.delete();
        kernel.delete();
    } catch (e) {
        console.error('Worker: Error enhancing', e);
    } finally {
        img.delete();
        gray.delete();
        thresh.delete();
    }

    return resultBlob;
}

async function optimizeImage(blob: Blob, maxWidth: number = 1024): Promise<Blob> {
    const img = await blobToMat(blob);
    let resultBlob = blob;

    try {
        let scale = 1;
        let newWidth = img.cols;
        let newHeight = img.rows;

        if (img.cols > maxWidth) {
            scale = maxWidth / img.cols;
            newWidth = maxWidth;
            newHeight = Math.round(img.rows * scale);
        }

        const resized = new cv.Mat();
        cv.resize(img, resized, new cv.Size(newWidth, newHeight), 0, 0, cv.INTER_AREA);

        resultBlob = await matToBlob(resized, 'image/jpeg', 0.85);
        resized.delete();
    } catch (e) {
        console.error('Worker: Error optimizing', e);
    } finally {
        img.delete();
    }

    return resultBlob;
}

// Helpers

async function blobToMat(blob: Blob): Promise<any> {
    const imgBitmap = await createImageBitmap(blob);
    const canvas = new OffscreenCanvas(imgBitmap.width, imgBitmap.height);
    const ctx = canvas.getContext('2d') as OffscreenCanvasRenderingContext2D;
    ctx.drawImage(imgBitmap, 0, 0);
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    return cv.matFromImageData(imageData);
}

async function matToBlob(mat: any, type: string = 'image/png', quality: number = 1): Promise<Blob> {
    // Create an OffscreenCanvas
    const canvas = new OffscreenCanvas(mat.cols, mat.rows);

    // cv.imshow expects a DOM element or ID, but we can't use it in worker easily without DOM.
    // However, we can construct ImageData manually.
    const imgData = new ImageData(new Uint8ClampedArray(mat.data), mat.cols, mat.rows);
    const ctx = canvas.getContext('2d') as OffscreenCanvasRenderingContext2D;
    ctx.putImageData(imgData, 0, 0);

    return canvas.convertToBlob({ type, quality });
}

function orderPoints(points: any): any {
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
