import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, timeout, tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { ClerkAuthService } from './clerk-auth.service';

export interface ChatRequest {
  question: string;
}

export interface ChatResponse {
  answer: string;
  timestamp: string;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(ClerkAuthService);
  private readonly apiUrl = `${environment.apiUrl}/chat`;
  private readonly requestTimeout = 60000; // 60 seconds for LLM processing

  /**
   * Ask AI a question about prices and grocery shopping
   * @param question The user's natural language question
   * @returns Observable of the AI-generated answer
   */
  askQuestion(question: string): Observable<ChatResponse> {
    const request: ChatRequest = { question };

    console.log('Sending request to:', `${this.apiUrl}/ask`);
    console.log('Request payload:', request);

    return this.http.post<ChatResponse>(`${this.apiUrl}/ask`, request, {
      headers: this.getHeaders()
    }).pipe(
      tap(response => console.log('Raw HTTP response:', response)),
      timeout(this.requestTimeout),
      catchError(error => {
        console.error('Chat service error:', error);
        console.error('Error status:', error.status);
        console.error('Error body:', error.error);
        
        if (error.name === 'TimeoutError') {
          return throwError(() => new Error('Request timed out. Please try again.'));
        }
        
        if (error.status === 429) {
          return throwError(() => new Error('Too many requests. Please wait a moment and try again.'));
        }
        
        if (error.status === 400) {
          return throwError(() => new Error(error.error?.error || 'Invalid question'));
        }
        
        if (error.status === 401) {
          return throwError(() => new Error('Please sign in to use Ask AI'));
        }
        
        return throwError(() => new Error('Failed to get answer. Please try again later.'));
      })
    );
  }

  private getHeaders(): HttpHeaders {
    const token = this.authService.getCurrentToken();
    let headers = new HttpHeaders({
      'Content-Type': 'application/json'
    });

    if (token) {
      headers = headers.set('Authorization', `Bearer ${token}`);
    }

    return headers;
  }
}
