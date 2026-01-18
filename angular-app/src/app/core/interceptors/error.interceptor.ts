import { inject } from '@angular/core';
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { ToastService } from '../services/toast.service';
import { CloudWatchLoggerService } from '../services/cloudwatch-logger.service';

/**
 * HTTP error interceptor for handling API errors
 * - Shows toast notifications for connection errors
 * - Logs errors to CloudWatch
 */
export const errorInterceptorFn: HttpInterceptorFn = (req, next) => {
  const toastService = inject(ToastService);
  const logger = inject(CloudWatchLoggerService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let errorMessage = 'An unexpected error occurred';
      let shouldShowToast = true;

      if (error.error instanceof ErrorEvent) {
        // Client-side or network error
        errorMessage = 'Network error. Please check your connection.';
        logger.error('Network Error', {
          message: error.error.message,
          url: req.url,
          method: req.method
        });
      } else if (error.status === 0) {
        // Connection refused or API not reachable
        errorMessage = 'Cannot connect to server. Please try again later.';
        logger.error('API Connection Failed', {
          url: req.url,
          method: req.method,
          status: error.status
        });
      } else if (error.status === 401) {
        // Unauthorized - don't show toast for auth errors (handled by auth interceptor)
        shouldShowToast = false;
        logger.warn('Unauthorized Request', {
          url: req.url,
          method: req.method
        });
      } else if (error.status === 403) {
        errorMessage = 'Access denied';
        logger.warn('Forbidden Request', {
          url: req.url,
          method: req.method
        });
      } else if (error.status === 404) {
        errorMessage = 'Resource not found';
        logger.warn('Not Found', {
          url: req.url,
          method: req.method
        });
      } else if (error.status === 409) {
        // Conflict - usually handled by the calling service
        shouldShowToast = false;
        logger.info('Conflict', {
          url: req.url,
          method: req.method,
          message: error.error?.message
        });
      } else if (error.status >= 500) {
        errorMessage = 'Server error. Please try again later.';
        logger.error('Server Error', {
          url: req.url,
          method: req.method,
          status: error.status,
          message: error.error?.message || error.message
        });
      } else {
        // Other errors
        errorMessage = error.error?.message || error.message || errorMessage;
        logger.error('HTTP Error', {
          url: req.url,
          method: req.method,
          status: error.status,
          message: error.error?.message || error.message
        });
      }

      // Show toast notification
      if (shouldShowToast) {
        toastService.error(errorMessage);
      }

      return throwError(() => error);
    })
  );
};
