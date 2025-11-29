import { Injectable, signal } from '@angular/core';
import { createWorker, Worker } from 'tesseract.js';

export interface ValidationResult {
    isValid: boolean;
    confidence: number;
    fields: {
        storeName: { detected: boolean; confidence: number; text?: string };
        location: { detected: boolean; confidence: number; text?: string };
        timestamp: { detected: boolean; confidence: number; text?: string };
    };
    suggestions: string[];
    rawText: string;
}

@Injectable({
    providedIn: 'root'
})
export class ReceiptValidatorService {
    private worker: Worker | null = null;
    private isInitialized = signal(false);
    private isProcessing = signal(false);

    constructor() { }

    /**
     * Initialize Tesseract worker
     */
    async initializeWorker(): Promise<void> {
        if (this.worker) {
            return; // Already initialized
        }

        try {
            this.worker = await createWorker('eng', 1, {
                logger: (m) => {
                    if (m.status === 'recognizing text') {
                        console.log(`OCR Progress: ${Math.round(m.progress * 100)}%`);
                    }
                }
            });
            this.isInitialized.set(true);
            console.log('Tesseract worker initialized');
        } catch (error) {
            console.error('Failed to initialize Tesseract worker:', error);
            throw error;
        }
    }

    /**
     * Terminate worker to free resources
     */
    async terminateWorker(): Promise<void> {
        if (this.worker) {
            await this.worker.terminate();
            this.worker = null;
            this.isInitialized.set(false);
            console.log('Tesseract worker terminated');
        }
    }

    /**
     * Pre-process image for better OCR results
     */
    async preprocessImage(imageData: string): Promise<string> {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d')!;

                // Resize if too large (max 1920px width for performance)
                const maxWidth = 1920;
                const scale = Math.min(1, maxWidth / img.width);
                canvas.width = img.width * scale;
                canvas.height = img.height * scale;

                // Draw image
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

                // Get image data for processing
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                const data = imageData.data;

                // Convert to grayscale and enhance contrast
                for (let i = 0; i < data.length; i += 4) {
                    const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
                    // Enhance contrast
                    const enhanced = gray < 128 ? gray * 0.8 : gray * 1.2;
                    data[i] = data[i + 1] = data[i + 2] = Math.min(255, Math.max(0, enhanced));
                }

                ctx.putImageData(imageData, 0, 0);
                resolve(canvas.toDataURL('image/jpeg', 0.9));
            };
            img.src = imageData;
        });
    }

    /**
     * Validate receipt image
     */
    async validateReceipt(imageData: string): Promise<ValidationResult> {
        if (!this.worker) {
            await this.initializeWorker();
        }

        this.isProcessing.set(true);

        try {
            // Pre-process image
            const processedImage = await this.preprocessImage(imageData);

            // Run OCR
            const { data } = await this.worker!.recognize(processedImage);
            const text = data.text;
            const confidence = data.confidence;

            console.log('OCR Text:', text);
            console.log('OCR Confidence:', confidence);

            // Validate required fields
            const validation = this.detectRequiredFields(text, (data as any).lines);

            // Calculate overall confidence
            const overallConfidence = (
                validation.storeName.confidence +
                validation.location.confidence +
                validation.timestamp.confidence
            ) / 3;

            // Determine if valid
            const isValid =
                validation.storeName.detected &&
                validation.location.detected &&
                validation.timestamp.detected &&
                overallConfidence >= 60;

            // Generate suggestions
            const suggestions = this.generateSuggestions(validation);

            return {
                isValid,
                confidence: overallConfidence,
                fields: validation,
                suggestions,
                rawText: text
            };
        } catch (error) {
            console.error('Validation error:', error);
            throw error;
        } finally {
            this.isProcessing.set(false);
        }
    }

    /**
     * Detect required fields in OCR text
     */
    private detectRequiredFields(text: string, lines: any[]): ValidationResult['fields'] {
        const textLower = text.toLowerCase();
        const textLines = text.split('\n').filter(line => line.trim());

        // Detect store name (usually in top 30% of receipt)
        const storeName = this.detectStoreName(textLines.slice(0, Math.ceil(textLines.length * 0.3)));

        // Detect location/address (usually in top 40%)
        const location = this.detectLocation(textLines.slice(0, Math.ceil(textLines.length * 0.4)));

        // Detect timestamp (can be top 50% or bottom 20%)
        const timestamp = this.detectTimestamp(text);

        return {
            storeName,
            location,
            timestamp
        };
    }

    /**
     * Detect store name
     */
    private detectStoreName(topLines: string[]): { detected: boolean; confidence: number; text?: string } {
        // Store names are usually in the first few lines and may contain common retail keywords
        const storeKeywords = ['mart', 'store', 'shop', 'market', 'supermarket', 'sdn', 'bhd', 'inc', 'ltd', 'co'];

        for (let i = 0; i < Math.min(5, topLines.length); i++) {
            const line = topLines[i].trim();
            if (line.length > 3) {
                const lineLower = line.toLowerCase();
                const hasKeyword = storeKeywords.some(keyword => lineLower.includes(keyword));
                const confidence = hasKeyword ? 85 : (line.length > 5 ? 70 : 50);

                if (confidence >= 50) {
                    return { detected: true, confidence, text: line };
                }
            }
        }

        return { detected: false, confidence: 0 };
    }

    /**
     * Detect location/address
     */
    private detectLocation(topLines: string[]): { detected: boolean; confidence: number; text?: string } {
        // Look for address patterns: street names, postal codes, city names
        const locationKeywords = ['jalan', 'jln', 'street', 'st', 'road', 'rd', 'avenue', 'ave', 'kuala lumpur', 'kl', 'selangor', 'penang', 'johor'];
        const postalCodePattern = /\b\d{5}\b/; // 5-digit postal code

        for (const line of topLines) {
            const lineLower = line.toLowerCase();
            const hasLocationKeyword = locationKeywords.some(keyword => lineLower.includes(keyword));
            const hasPostalCode = postalCodePattern.test(line);

            if (hasLocationKeyword || hasPostalCode) {
                const confidence = (hasLocationKeyword && hasPostalCode) ? 90 : (hasLocationKeyword ? 75 : 70);
                return { detected: true, confidence, text: line };
            }
        }

        return { detected: false, confidence: 0 };
    }

    /**
     * Detect timestamp/date
     */
    private detectTimestamp(text: string): { detected: boolean; confidence: number; text?: string } {
        // Common date patterns
        const datePatterns = [
            /\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}/,  // DD/MM/YYYY or MM/DD/YYYY
            /\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}/,    // YYYY/MM/DD
            /\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}/i,  // DD Month YYYY
        ];

        const timePattern = /\d{1,2}:\d{2}(:\d{2})?(\s*(am|pm))?/i;

        for (const pattern of datePatterns) {
            const match = text.match(pattern);
            if (match) {
                const hasTime = timePattern.test(text);
                const confidence = hasTime ? 90 : 75;
                return { detected: true, confidence, text: match[0] };
            }
        }

        return { detected: false, confidence: 0 };
    }

    /**
     * Generate suggestions for improving image quality
     */
    private generateSuggestions(fields: ValidationResult['fields']): string[] {
        const suggestions: string[] = [];

        if (!fields.storeName.detected) {
            suggestions.push('Ensure the store name at the top is clearly visible');
        }
        if (!fields.location.detected) {
            suggestions.push('Make sure the store address is in frame');
        }
        if (!fields.timestamp.detected) {
            suggestions.push('Capture the date and time on the receipt');
        }
        if (fields.storeName.confidence < 70 || fields.location.confidence < 70 || fields.timestamp.confidence < 70) {
            suggestions.push('Improve lighting and hold camera steady');
            suggestions.push('Ensure receipt is flat and not wrinkled');
        }

        return suggestions;
    }

    /**
     * Get processing status
     */
    getProcessingStatus() {
        return this.isProcessing();
    }

    /**
     * Get initialization status
     */
    getInitializationStatus() {
        return this.isInitialized();
    }
}
