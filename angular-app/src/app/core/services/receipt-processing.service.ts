import { Injectable, computed, inject, signal } from '@angular/core';
import { ReceiptService } from './receipt.service';
import { ToastService } from './toast.service';
import { PointsService } from './points.service';
import { Receipt } from '../models/receipt.model';
import { Router } from '@angular/router';

export interface ProcessingItem {
    id: string; // Temporary ID or filename
    filename: string;
    status: 'uploading' | 'processing' | 'completed' | 'error';
    progress: number;
    error?: string;
    receipt?: Receipt;
    blob?: Blob;
}

export interface UploadEvent {
    type: 'success' | 'error' | 'first_upload';
    receipt?: Receipt;
    error?: string;
}

@Injectable({
    providedIn: 'root'
})
export class ReceiptProcessingService {
    private receiptService = inject(ReceiptService);
    private toastService = inject(ToastService);
    private pointsService = inject(PointsService);
    private router = inject(Router);

    // State
    private _activeUploads = signal<ProcessingItem[]>([]);
    private _uploadEvents = signal<UploadEvent | null>(null);

    // Public signals
    activeUploads = computed(() => this._activeUploads());
    isProcessing = computed(() => this._activeUploads().some(u => u.status === 'uploading' || u.status === 'processing'));
    uploadEvents$ = computed(() => this._uploadEvents());

    /**
     * Start processing a receipt image in the background
     */
    processReceipt(blob: Blob, filename: string): void {
        const tempId = `temp_${Date.now()}`;

        // Add to active uploads
        this.addUpload(tempId, filename, blob);

        // Show initial toast
        this.toastService.show(`Uploading ${filename}...`, 'info');

        this.startUpload(tempId, blob, filename);
    }

    private startUpload(id: string, blob: Blob, filename: string) {
        // Start upload
        this.receiptService.uploadReceipt(blob, filename).subscribe({
            next: (response) => {
                if (response.success && response.receipt) {
                    this.completeUpload(id, response.receipt);
                    this.toastService.show('Receipt processed successfully!', 'success');

                    // Refresh points balance after successful upload (with delay to ensure backend awarded points)
                    setTimeout(() => {
                        this.pointsService.refreshBalance();
                        this.checkForFirstUpload();
                    }, 1000);

                    // Redirect to receipt detail page for review and correction
                    setTimeout(() => {
                        this.router.navigate(['/receipt', response.receipt!.id], {
                            queryParams: { new: 'true' }
                        });
                    }, 500);
                }
            },
            error: (error) => {
                const errorMessage = error.error || 'Failed to upload receipt';
                this.failUpload(id, errorMessage);

                if (error.existingReceiptId) {
                    this.toastService.warning('Receipt already exists');
                    // Note: ToastService currently doesn't support actions based on the definition I saw.
                    // I will just show the warning for now.
                    // Ideally we could add action support to ToastService, but let's stick to existing capabilities.
                    setTimeout(() => this.router.navigate(['/purchased-items']), 1500);
                } else {
                    this.toastService.show(`Failed to process ${filename}`, 'error');
                }
            }
        });
    }

    /**
     * Retry a failed upload
     */
    retryUpload(id: string) {
        const item = this._activeUploads().find(u => u.id === id);
        if (item && item.status === 'error' && item.blob) {
            // Reset status
            this._activeUploads.update(uploads =>
                uploads.map(u => u.id === id ? { ...u, status: 'uploading', error: undefined, progress: 0 } : u)
            );

            // Retry
            this.startUpload(id, item.blob, item.filename);
        }
    }

    /**
     * Dismiss a failed upload card
     */
    dismissUpload(id: string) {
        this._activeUploads.update(uploads => uploads.filter(u => u.id !== id));
    }

    private addUpload(id: string, filename: string, blob: Blob) {
        this._activeUploads.update(uploads => [
            ...uploads,
            {
                id,
                filename,
                status: 'uploading',
                progress: 0,
                blob
            }
        ]);
    }

    private completeUpload(id: string, receipt: Receipt) {
        // Remove from active list
        this._activeUploads.update(uploads => uploads.filter(u => u.id !== id));
    }

    private failUpload(id: string, error: string) {
        // Update status to error instead of removing
        this._activeUploads.update(uploads =>
            uploads.map(u => u.id === id ? { ...u, status: 'error', error } : u)
        );
    }

    private checkForFirstUpload() {
        // Check if user has first_upload achievement
        this.pointsService.getAchievements().subscribe({
            next: (achievements) => {
                const hasFirstUpload = achievements.some(a => a.achievementType === 'first_upload');
                if (hasFirstUpload) {
                    // Emit event to show modal
                    this._uploadEvents.set({ type: 'first_upload' });
                    // Clear after a short time
                    setTimeout(() => this._uploadEvents.set(null), 100);
                }
            },
            error: (err) => {
                console.error('Failed to check achievements:', err);
            }
        });
    }
}
