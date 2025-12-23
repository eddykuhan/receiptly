import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WeeklyChallengesService, ChallengesDashboardDto, WeeklyChallengeDto, UserWeeklyProgressDto } from '../../core/services/weekly-challenges.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-weekly-challenges',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './weekly-challenges.component.html',
  styleUrls: ['./weekly-challenges.component.scss']
})
export class WeeklyChallengesComponent implements OnInit, OnDestroy {
  dashboard: ChallengesDashboardDto | null = null;
  totalPossiblePoints = 0;
  earnedPoints = 0;
  isLoading = true;
  error: string | null = null;
  private destroy$ = new Subject<void>();

  constructor(private challengesService: WeeklyChallengesService) {}

  ngOnInit() {
    this.loadChallenges();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadChallenges() {
    this.isLoading = true;
    this.error = null;
    
    this.challengesService.getChallengesDashboard()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (dashboard) => {
          this.dashboard = dashboard;
          this.calculatePoints();
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Failed to load challenges:', error);
          this.error = 'Failed to load challenges. Please try again.';
          this.isLoading = false;
        }
      });
  }

  calculatePoints() {
    if (!this.dashboard) return;

    this.totalPossiblePoints = this.dashboard.challenges.reduce(
      (sum, challenge) => sum + challenge.pointsReward,
      0
    );

    this.earnedPoints = this.dashboard.challenges.reduce((sum, challenge) => {
      const progress = this.dashboard!.userProgress.find(p => p.challengeId === challenge.id);
      return progress && progress.completedAt ? sum + challenge.pointsReward : sum;
    }, 0);
  }

  isChallengeCompleted(challengeId: string): boolean {
    if (!this.dashboard) return false;
    return this.dashboard.userProgress.some(p => p.challengeId === challengeId && p.isCompleted);
  }

  isRewardClaimed(challengeId: string): boolean {
    if (!this.dashboard) return false;
    const progress = this.dashboard.userProgress.find(p => p.challengeId === challengeId);
    return progress ? !!progress.completedAt : false;
  }

  getUserProgress(challengeId: string): UserWeeklyProgressDto | undefined {
    if (!this.dashboard) return undefined;
    return this.dashboard.userProgress.find(p => p.challengeId === challengeId);
  }

  getCurrentProgress(challengeId: string): number {
    const progress = this.getUserProgress(challengeId);
    return progress ? progress.currentCount : 0;
  }

  getProgressPercentage(current: number, target: number): number {
    return this.challengesService.getProgressPercentage(current, target);
  }

  getChallengeTypeName(type: string): string {
    return this.challengesService.getChallengeTypeName(type);
  }

  getChallengeIcon(type: string): string {
    const icons: { [key: string]: string } = {
      'receipt_count': '🧾',
      'store_count': '🏪',
      'total_amount': '💰',
      'city_count': '🌆',
      'day_count': '📅'
    };
    return icons[type] || '🎯';
  }
}
