import { inject } from '@angular/core';
import {
  HttpInterceptorFn,
  HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError, race, timer } from 'rxjs';
import { catchError, switchMap, map } from 'rxjs/operators';
import { ClerkAuthService } from '../services/clerk-auth.service';

/**
 * Functional HTTP interceptor for adding Clerk authentication tokens to requests
 */
export const clerkAuthInterceptorFn: HttpInterceptorFn = (req, next) => {
  const authService = inject(ClerkAuthService);

  // Race between getting a token and a timeout
  // This prevents requests from hanging if Clerk hasn't initialized
  return race(
    authService.sessionToken$.pipe(map(token => token)),
    timer(500).pipe(map(() => null))
  ).pipe(
    switchMap((token: string | null) => {
      let request = req;
      
      if (token) {
        request = req.clone({
          setHeaders: {
            Authorization: `Bearer ${token}`
          }
        });
        console.log('✅ Token added to request:', req.url, 'Token:', token.substring(0, 20) + '...');
      } else {
        console.warn('⚠️ No token available for request:', req.url, '- proceeding without token');
        console.log('Auth state:', {
          isAuthenticated: authService.isAuthenticated(),
          user: authService.getCurrentUser(),
          hasToken: !!authService.getCurrentToken()
        });
      }

      return next(request).pipe(
        catchError((error: HttpErrorResponse) => {
          if (error.status === 401) {
            console.log('Got 401 error, need to implement token refresh');
          }
          return throwError(() => error);
        })
      );
    })
  );
};
