import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import {
  SubmitCorrectionRequest,
  ReportIssueRequest,
  FeedbackResponse
} from '../models/validation.model';
import { CloudWatchLoggerService } from './cloudwatch-logger.service';
import { ToastService } from './toast.service';

@Injectable({
  providedIn: 'root'
})
export class FeedbackService {
  private http = inject(HttpClient);
  private logger = inject(CloudWatchLoggerService);
  private toast = inject(ToastService);
  private readonly API_URL = `${environment.apiUrl}/feedback`;

  /**
   * Submit a correction for an OCR extraction error
   */
  submitCorrection(request: SubmitCorrectionRequest): Observable<FeedbackResponse> {
    this.logger.info('Submitting correction', { request });

    return this.http.post<FeedbackResponse>(`${this.API_URL}/correction`, request)
      .pipe(
        tap(response => {
          if (response.success) {
            this.toast.show('Thank you! Your correction helps improve accuracy.', 'success');
            this.logger.info('Correction submitted successfully', { correctionId: response.correctionId });
          }
        }),
        catchError(error => {
          this.logger.error('Failed to submit correction', error);
          this.toast.show('Failed to submit correction. Please try again.', 'error');
          return throwError(() => error);
        })
      );
  }

  /**
   * Report an issue with OCR processing
   */
  reportIssue(request: ReportIssueRequest): Observable<FeedbackResponse> {
    this.logger.info('Reporting issue', { request });

    return this.http.post<FeedbackResponse>(`${this.API_URL}/issue`, request)
      .pipe(
        tap(response => {
          if (response.success) {
            this.toast.show(response.message, 'success');
            this.logger.info('Issue reported successfully');
          }
        }),
        catchError(error => {
          this.logger.error('Failed to report issue', error);
          this.toast.show('Failed to report issue. Please try again.', 'error');
          return throwError(() => error);
        })
      );
  }

  /**
   * Get correction history for the current user
   */
  getCorrectionHistory(): Observable<any[]> {
    return this.http.get<any[]>(`${this.API_URL}/corrections`)
      .pipe(
        catchError(error => {
          this.logger.error('Failed to get correction history', error);
          return throwError(() => error);
        })
      );
  }
}
