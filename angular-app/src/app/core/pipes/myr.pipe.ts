import { Pipe, PipeTransform } from '@angular/core';
import { CurrencyService } from '../services/currency.service';

@Pipe({
  name: 'myr',
  standalone: true
})
export class MyrPipe implements PipeTransform {
  constructor(private currencyService: CurrencyService) {}

  transform(value: number | string | null | undefined, useLocale: boolean = false): string {
    if (value === null || value === undefined || value === '') {
      return 'RM 0.00';
    }

    const amount = typeof value === 'string' ? parseFloat(value) : value;

    if (isNaN(amount)) {
      return 'RM 0.00';
    }

    return useLocale 
      ? this.currencyService.formatLocale(amount)
      : this.currencyService.format(amount);
  }
}
