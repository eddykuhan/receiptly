import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class CurrencyService {
  private readonly currencySymbol = 'RM';
  private readonly currencyCode = 'MYR';
  private readonly locale = 'ms-MY'; // Malaysian locale

  /**
   * Format a number as Malaysian Ringgit currency
   * @param amount - The amount to format
   * @param showSymbol - Whether to show the RM symbol (default: true)
   * @returns Formatted currency string
   */
  format(amount: number, showSymbol: boolean = true): string {
    const formatted = amount.toFixed(2);
    return showSymbol ? `${this.currencySymbol} ${formatted}` : formatted;
  }

  /**
   * Format with full locale support
   * @param amount - The amount to format
   * @returns Formatted currency string with locale
   */
  formatLocale(amount: number): string {
    return new Intl.NumberFormat(this.locale, {
      style: 'currency',
      currency: this.currencyCode,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  }

  /**
   * Get the currency symbol
   */
  getSymbol(): string {
    return this.currencySymbol;
  }

  /**
   * Get the currency code
   */
  getCode(): string {
    return this.currencyCode;
  }
}
