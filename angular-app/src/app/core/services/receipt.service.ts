import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, BehaviorSubject } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
import { Receipt, UploadReceiptResponse } from '../models/receipt.model';
import { environment } from '../../../environments/environment.development';

@Injectable({
  providedIn: 'root'
})
export class ReceiptService {
  private http = inject(HttpClient);
  private readonly API_URL = `${environment.apiUrl}/receipts`;
  private readonly USER_ID = 'default-user'; // TODO: Replace with actual user management
  
  // In-memory cache for current session
  private receiptsCache$ = new BehaviorSubject<Receipt[]>([]);
  public receipts$ = this.receiptsCache$.asObservable();
  
  constructor() {
    this.loadReceipts();
  }
  
  /**
   * Load all receipts for the current user
   */
  loadReceipts(): void {
    this.http.get<Receipt[]>(`${this.API_URL}/user/${this.USER_ID}`)
      .pipe(
        map(receipts => receipts.map(r => this.parseReceiptDates(r))),
        catchError(this.handleError)
      )
      .subscribe(receipts => {
        this.receiptsCache$.next(receipts);
      });
  }
  
  /**
   * Upload a receipt image for processing
   */
  uploadReceipt(imageFile: File | Blob, filename: string): Observable<UploadReceiptResponse> {
    const formData = new FormData();
    formData.append('file', imageFile, filename);
    
    return this.http.post<Receipt>(this.API_URL, formData).pipe(
      map(receipt => ({
        success: true,
        receipt: this.parseReceiptDates(receipt)
      })),
      tap(response => {
        if (response.receipt) {
          // Add to cache
          const currentReceipts = this.receiptsCache$.value;
          this.receiptsCache$.next([response.receipt, ...currentReceipts]);
        }
      }),
      catchError((error: HttpErrorResponse) => {
        if (error.status === 409) {
          // Duplicate receipt
          return throwError(() => ({
            success: false,
            error: 'Duplicate receipt detected',
            existingReceiptId: error.error?.existingReceiptId
          }));
        }
        return throwError(() => ({
          success: false,
          error: error.error?.message || 'Failed to upload receipt'
        }));
      })
    );
  }
  
  /**
   * Get a single receipt by ID
   */
  getReceipt(id: string): Observable<Receipt> {
    return this.http.get<Receipt>(`${this.API_URL}/${id}`).pipe(
      map(receipt => this.parseReceiptDates(receipt)),
      catchError(this.handleError)
    );
  }
  
  /**
   * Delete a receipt
   */
  deleteReceipt(id: string): Observable<void> {
    return this.http.delete<void>(`${this.API_URL}/${id}`).pipe(
      tap(() => {
        // Remove from cache
        const currentReceipts = this.receiptsCache$.value;
        this.receiptsCache$.next(currentReceipts.filter(r => r.id !== id));
      }),
      catchError(this.handleError)
    );
  }
  
  /**
   * Get receipts from cache (for immediate display)
   */
  getCachedReceipts(): Receipt[] {
    return this.receiptsCache$.value;
  }
  
  /**
   * Parse date strings to Date objects
   */
  private parseReceiptDates(receipt: any): Receipt {
    return {
      ...receipt,
      purchaseDate: new Date(receipt.purchaseDate),
      createdAt: new Date(receipt.createdAt),
      updatedAt: receipt.updatedAt ? new Date(receipt.updatedAt) : undefined,
      processedAt: receipt.processedAt ? new Date(receipt.processedAt) : undefined
    };
  }
  
  /**
   * Handle HTTP errors
   */
  private handleError(error: HttpErrorResponse) {
    console.error('API Error:', error);
    return throwError(() => new Error(error.error?.message || 'An error occurred'));
  }
}
