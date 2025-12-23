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
    isProcessing = computed(() => this._activeUploads().length > 0);
    uploadEvents$ = computed(() => this._uploadEvents());

    /**
     * Start processing a receipt image in the background
     */
    processReceipt(blob: Blob, filename: string): void {
        const tempId = `temp_${Date.now()}`;

        // Add to active uploads
        this.addUpload(tempId, filename);

        // Show initial toast
        this.toastService.show(`Uploading ${filename}...`, 'info');

        // Start upload
        this.receiptService.uploadReceipt(blob, filename).subscribe({
            next: (response) => {
                if (response.success && response.receipt) {
                    this.completeUpload(tempId, response.receipt);
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
                this.failUpload(tempId, errorMessage);

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

    private addUpload(id: string, filename: string) {
        this._activeUploads.update(uploads => [
            ...uploads,
            {
                id,
                filename,
                status: 'uploading',
                progress: 0
            }
        ]);
    }

    private completeUpload(id: string, receipt: Receipt) {
        // Remove from active list
        this._activeUploads.update(uploads => uploads.filter(u => u.id !== id));
    }

    private failUpload(id: string, error: string) {
        // Remove from active list (or keep with error state if we want to show a list of failures)
        // For now, removing and relying on toast
        this._activeUploads.update(uploads => uploads.filter(u => u.id !== id));
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
