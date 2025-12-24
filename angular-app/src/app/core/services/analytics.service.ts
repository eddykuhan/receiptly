import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface PriceHistoryPoint {
  purchaseDate: string;
  unitPrice: number;
  storeName: string;
  itemId: string;
}

export interface PriceStatistics {
  minPrice: number;
  maxPrice: number;
  averagePrice: number;
  currentPrice: number;
  cheapestStore: string;
  mostExpensiveStore: string;
}

export interface PriceHistoryResponse {
  canonicalName: string;
  pricePoints: PriceHistoryPoint[];
  statistics: PriceStatistics;
}

export interface SavingsOpportunity {
  canonicalName: string;
  purchasedAt: string;
  paidPrice: number;
  cheaperAt: string;
  cheaperPrice: number;
  potentialSaving: number;
  quantity: number;
  purchaseDate: string;
}

export interface SavingsReportResponse {
  totalSpent: number;
  potentialSavings: number;
  savingsPercentage: number;
  opportunities: SavingsOpportunity[];
  startDate: string;
  endDate: string;
}

export interface StoreStats {
  storeName: string;
  purchaseCount: number;
  totalSpent: number;
  averageTransactionValue: number;
  priceIndex: number;
  uniqueItemsCount: number;
  latitude?: number;
  longitude?: number;
  topItems: string[];
}

export interface StoreComparisonResponse {
  stores: StoreStats[];
  startDate: string;
  endDate: string;
  totalPurchases: number;
  totalSpent: number;
}

@Injectable({
  providedIn: 'root'
})
export class AnalyticsService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/analytics`;

  getPriceHistory(userId: string, canonicalName: string, days: number = 30): Observable<PriceHistoryResponse> {
    const params = new HttpParams()
      .set('userId', userId)
      .set('canonicalName', canonicalName)
      .set('days', days.toString());

    return this.http.get<PriceHistoryResponse>(`${this.apiUrl}/price-history`, { params });
  }

  getSavingsReport(userId: string, days: number = 7): Observable<SavingsReportResponse> {
    const params = new HttpParams()
      .set('userId', userId)
      .set('days', days.toString());

    return this.http.get<SavingsReportResponse>(`${this.apiUrl}/savings-report`, { params });
  }

  getStoreComparison(userId: string, days: number = 30): Observable<StoreComparisonResponse> {
    const params = new HttpParams()
      .set('userId', userId)
      .set('days', days.toString());

    return this.http.get<StoreComparisonResponse>(`${this.apiUrl}/store-comparison`, { params });
  }
}
