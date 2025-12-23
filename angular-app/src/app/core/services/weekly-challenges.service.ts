import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface WeeklyChallengeDto {
  id: string;
  title: string;
  description: string | null;
  challengeType: string;
  targetCount: number;
  pointsReward: number;
  weekStart: string;
  weekEnd: string;
  isActive: boolean;
}

export interface UserWeeklyProgressDto {
  id: string;
  challengeId: string;
  currentCount: number;
  targetCount: number;
  isCompleted: boolean;
  completedAt: string | null;
  weekStart: string;
}

export interface ChallengesDashboardDto {
  challenges: WeeklyChallengeDto[];
  userProgress: UserWeeklyProgressDto[];
  completedCount: number;
  totalCount: number;
}

@Injectable({
  providedIn: 'root'
})
export class WeeklyChallengesService {
  private readonly API_URL = `${environment.apiUrl}/challenges`;
  private challengesDashboard$ = new BehaviorSubject<ChallengesDashboardDto | null>(null);

  constructor(private http: HttpClient) {}

  /**
   * Get the current challenges dashboard (challenges + user progress)
   */
  getChallengesDashboard(): Observable<ChallengesDashboardDto> {
    return this.http.get<ChallengesDashboardDto>(`${this.API_URL}/dashboard`).pipe(
      tap(dashboard => this.challengesDashboard$.next(dashboard))
    );
  }

  /**
   * Get only active challenges
   */
  getActiveChallenges(): Observable<WeeklyChallengeDto[]> {
    return this.http.get<WeeklyChallengeDto[]>(`${this.API_URL}/active`);
  }

  /**
   * Get only user's progress
   */
  getUserProgress(): Observable<UserWeeklyProgressDto[]> {
    return this.http.get<UserWeeklyProgressDto[]>(`${this.API_URL}/progress`);
  }

  /**
   * Get cached dashboard
   */
  getCachedDashboard(): ChallengesDashboardDto | null {
    return this.challengesDashboard$.value;
  }

  /**
   * Get dashboard as observable for reactive updates
   */
  getDashboard$(): Observable<ChallengesDashboardDto | null> {
    return this.challengesDashboard$.asObservable();
  }

  /**
   * Refresh dashboard data
   */
  refreshDashboard(): Observable<ChallengesDashboardDto> {
    return this.getChallengesDashboard();
  }

  /**
   * Calculate progress percentage
   */
  getProgressPercentage(current: number, target: number): number {
    if (target === 0) return 0;
    return Math.min(Math.round((current / target) * 100), 100);
  }

  /**
   * Get display name for challenge type
   */
  getChallengeTypeName(type: string): string {
    const names: { [key: string]: string } = {
      'receipt_count': 'Receipts',
      'store_count': 'Stores',
      'total_amount': 'Total Spent',
      'city_count': 'Cities',
      'day_count': 'Days'
    };
    return names[type] || type;
  }
}
