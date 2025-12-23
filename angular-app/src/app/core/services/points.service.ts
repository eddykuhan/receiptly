import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface UserPoints {
  userId: string;
  totalPoints: number;
  availablePoints: number;
  lifetimePoints: number;
  lastUpdated: Date;
}

export interface PointTransaction {
  id: string;
  points: number;
  transactionType: string;
  description: string;
  referenceId?: string;
  earnedAt: Date;
  expiresAt: Date;
  isExpired: boolean;
}

export interface Achievement {
  id: string;
  achievementType: string;
  pointsAwarded: number;
  unlockedAt: Date;
}

@Injectable({
  providedIn: 'root'
})
export class PointsService {
  private apiUrl = `${environment.apiUrl}/points`;
  private pointsSubject = new BehaviorSubject<UserPoints | null>(null);
  public points$ = this.pointsSubject.asObservable();

  constructor(private http: HttpClient) {}

  /**
   * Get user's current points balance
   */
  getBalance(): Observable<UserPoints> {
    return this.http.get<UserPoints>(`${this.apiUrl}/balance`).pipe(
      tap(points => this.pointsSubject.next(points))
    );
  }

  /**
   * Get user's point transaction history
   */
  getTransactions(limit: number = 50): Observable<PointTransaction[]> {
    return this.http.get<PointTransaction[]>(`${this.apiUrl}/transactions`, {
      params: { limit: limit.toString() }
    });
  }

  /**
   * Get user's unlocked achievements
   */
  getAchievements(): Observable<Achievement[]> {
    return this.http.get<Achievement[]>(`${this.apiUrl}/achievements`);
  }

  /**
   * Refresh points balance (call after actions that may change points)
   */
  refreshBalance(): void {
    this.getBalance().subscribe();
  }

  /**
   * Get current cached points value
   */
  getCurrentPoints(): UserPoints | null {
    return this.pointsSubject.value;
  }
}
