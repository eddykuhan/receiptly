import { Component, Input, Output, EventEmitter, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { FeedbackService } from '../../core/services/feedback.service';
import {
  SubmitCorrectionRequest
} from '../../core/models/validation.model';
import { Receipt } from '../../core/models/receipt.model';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-feedback-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    @if (isOpen()) {
      <div class="modal-overlay" (click)="close()">
        <div class="modal-content" (click)="$event.stopPropagation()">
          <div class="modal-header">
            <h2>Edit Receipt</h2>
            <button class="close-btn" (click)="close()" aria-label="Close">&times;</button>
          </div>

          <div class="modal-body">
            <form (ngSubmit)="submitCorrection()" class="feedback-form">
              <div class="form-group">
                <label for="field-name">What field needs correction?</label>
                <select 
                  id="field-name" 
                  [(ngModel)]="correctionData.fieldName" 
                  name="fieldName"
                  required
                  class="form-control"
                  (change)="onFieldSelectionChange()">
                  <option value="">Select a field...</option>
                  <option value="StoreName">Store Name</option>
                  <option value="TotalAmount">Total Amount</option>
                  <option value="PurchaseDate">Purchase Date</option>
                  <option value="StoreAddress">Store Address</option>
                  @for (item of receipt.items; track item.id; let i = $index) {
                    <option [value]="'Items[' + i + '].Name'">Item {{ i + 1 }}: {{ item.name }}</option>
                    <option [value]="'Items[' + i + '].Price'">Item {{ i + 1 }} Price</option>
                  }
                </select>
              </div>

              @if (correctionData.incorrectValue) {
                <div class="form-group">
                  <label>Current value (extracted by OCR):</label>
                  <div class="current-value-display">
                    {{ correctionData.incorrectValue }}
                  </div>
                </div>
              }

              <div class="form-group">
                <label for="corrected-value">What should it be?</label>
                
                @if (correctionData.fieldName === 'PurchaseDate') {
                  <!-- Date Picker for PurchaseDate -->
                  <input 
                    type="date" 
                    id="corrected-value"
                    [(ngModel)]="correctionData.correctedValue" 
                    name="correctedValue"
                    required
                    class="form-control"
                    [max]="today">
                } @else if (correctionData.fieldName === 'TotalAmount' || correctionData.fieldName.includes('Price')) {
                  <!-- Number Input for amounts -->
                  <input 
                    type="number" 
                    id="corrected-value"
                    [(ngModel)]="correctionData.correctedValue" 
                    name="correctedValue"
                    required
                    step="0.01"
                    min="0"
                    class="form-control"
                    placeholder="0.00">
                } @else {
                  <!-- Text Input for other fields -->
                  <input 
                    type="text" 
                    id="corrected-value"
                    [(ngModel)]="correctionData.correctedValue" 
                    name="correctedValue"
                    required
                    class="form-control"
                    placeholder="The correct value"
                    (input)="onAddressInput($event)"
                    (focus)="onAddressFocus()"
                    (blur)="onAddressBlur()">
                }
                
                @if (showSuggestions() && suggestions().length > 0) {
                  <div class="suggestions-dropdown">
                    @for (suggestion of suggestions(); track suggestion.description) {
                      <div 
                        class="suggestion-item"
                        (mousedown)="selectSuggestion(suggestion)">
                        <span class="material-icons suggestion-icon">place</span>
                        <div class="suggestion-text">
                          <div class="suggestion-main">{{ suggestion.mainText }}</div>
                          <div class="suggestion-secondary">{{ suggestion.secondaryText }}</div>
                        </div>
                      </div>
                    }
                  </div>
                }
              </div>

              <div class="form-actions">
                <button type="button" class="btn btn-secondary" (click)="close()">Cancel</button>
                <button type="submit" class="btn btn-primary" [disabled]="isSubmitting()">
                  {{ isSubmitting() ? 'Submitting...' : 'Save Changes' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 1rem;
    }

    .modal-content {
      background: white;
      border-radius: 0.75rem;
      max-width: 600px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.5rem;
      border-bottom: 1px solid #eee;
    }

    .modal-header h2 {
      margin: 0;
      font-size: 1.5rem;
      color: #333;
    }

    .close-btn {
      background: none;
      border: none;
      font-size: 2rem;
      color: #999;
      cursor: pointer;
      padding: 0;
      width: 2rem;
      height: 2rem;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: color 0.2s;
    }

    .close-btn:hover {
      color: #333;
    }

    .modal-body {
      padding: 1.5rem;
    }

    .feedback-form {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .form-group label {
      font-weight: 500;
      color: #333;
      font-size: 0.95rem;
    }

    .form-control {
      padding: 0.625rem 0.75rem;
      border: 1px solid #ddd;
      border-radius: 0.375rem;
      font-size: 1rem;
      transition: border-color 0.2s;
      background-color: white;
      color: #333;
    }

    .form-control:focus {
      outline: none;
      border-color: #007bff;
      box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
    }

    input[type="date"].form-control,
    input[type="number"].form-control {
      appearance: auto;
      -webkit-appearance: auto;
      -moz-appearance: auto;
    }

    input[type="date"]::-webkit-calendar-picker-indicator {
      cursor: pointer;
      filter: invert(0.5);
    }

    input[type="date"]:hover::-webkit-calendar-picker-indicator {
      filter: invert(0.3);
    }

    select.form-control {
      color: #333;
    }

    select.form-control option {
      color: #333;
      background-color: white;
    }

    .form-actions {
      display: flex;
      gap: 0.75rem;
      justify-content: flex-end;
      margin-top: 0.5rem;
    }

    .btn {
      padding: 0.625rem 1.25rem;
      border-radius: 0.375rem;
      border: none;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
      font-size: 1rem;
    }

    .btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .btn-primary {
      background-color: #007bff;
      color: white;
    }

    .btn-primary:hover:not(:disabled) {
      background-color: #0056b3;
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(0, 123, 255, 0.3);
    }

    .btn-secondary {
      background-color: #6c757d;
      color: white;
    }

    .btn-secondary:hover {
      background-color: #5a6268;
    }

    .suggestions-dropdown {
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      background: white;
      border: 1px solid #ddd;
      border-radius: 0.375rem;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      max-height: 300px;
      overflow-y: auto;
      z-index: 1001;
      margin-top: 0.25rem;
    }

    .suggestion-item {
      display: flex;
      align-items: start;
      gap: 0.75rem;
      padding: 0.75rem;
      cursor: pointer;
      border-bottom: 1px solid #f0f0f0;
      transition: background-color 0.2s;
    }

    .suggestion-item:last-child {
      border-bottom: none;
    }

    .suggestion-item:hover {
      background-color: #f8f9fa;
    }

    .suggestion-icon {
      color: #007bff;
      font-size: 1.25rem;
      flex-shrink: 0;
    }

    .suggestion-text {
      flex: 1;
      min-width: 0;
    }

    .suggestion-main {
      font-weight: 500;
      color: #333;
      margin-bottom: 0.25rem;
    }

    .suggestion-secondary {
      font-size: 0.875rem;
      color: #666;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .form-group {
      position: relative;
    }

    .current-value-display {
      padding: 0.75rem;
      background-color: #f8f9fa;
      border: 1px solid #dee2e6;
      border-radius: 0.375rem;
      color: #495057;
      font-family: 'Courier New', monospace;
      font-size: 0.95rem;
      word-break: break-word;
    }
  `]
})
export class FeedbackModalComponent {
  @Input({ required: true }) receipt!: Receipt;
  @Output() closed = new EventEmitter<void>();
  @Output() correctionSubmitted = new EventEmitter<CorrectionData>();

  private feedbackService = inject(FeedbackService);
  private http = inject(HttpClient);
  private readonly PLACES_API_URL = `${environment.apiUrl}/places`;

  isOpen = signal(false);
  isSubmitting = signal(false);

  // Date picker max value (today)
  today = new Date().toISOString().split('T')[0];

  // Google Places autocomplete
  suggestions = signal<PlaceSuggestion[]>([]);
  showSuggestions = signal(false);
  private inputTimeout?: number;

  correctionData: SubmitCorrectionRequest = {
    receiptId: '',
    fieldName: '',
    incorrectValue: '',
    correctedValue: '',
    latitude: undefined,
    longitude: undefined
  };

  open() {
    this.isOpen.set(true);
    this.resetForms();
    this.correctionData.receiptId = this.receipt.id;
  }

  close() {
    this.isOpen.set(false);
    this.closed.emit();
  }

  openForLocationCorrection() {
    this.isOpen.set(true);
    this.correctionData.receiptId = this.receipt.id;
    this.correctionData.fieldName = 'StoreAddress';
    this.correctionData.incorrectValue = this.receipt.storeAddress || '';
    this.correctionData.correctedValue = this.receipt.storeAddress || '';
    this.correctionData.latitude = undefined;
    this.correctionData.longitude = undefined;
    this.suggestions.set([]);
    this.showSuggestions.set(false);

    // Trigger location search after a brief delay to ensure DOM is ready
    setTimeout(() => {
      if (this.correctionData.correctedValue) {
        this.fetchSuggestions(this.correctionData.correctedValue);
        this.showSuggestions.set(true);
      }
    }, 100);
  }

  submitCorrection() {
    if (!this.correctionData.fieldName || !this.correctionData.correctedValue) {
      return;
    }

    this.isSubmitting.set(true);
    this.feedbackService.submitCorrection(this.correctionData).subscribe({
      next: () => {
        // Emit the correction data so parent can update the receipt
        this.correctionSubmitted.emit({
          fieldName: this.correctionData.fieldName,
          correctedValue: this.correctionData.correctedValue,
          latitude: this.correctionData.latitude,
          longitude: this.correctionData.longitude
        });
        this.close();
      },
      error: () => {
        this.isSubmitting.set(false);
      },
      complete: () => {
        this.isSubmitting.set(false);
      }
    });
  }

  onAddressInput(event: Event) {
    const input = (event.target as HTMLInputElement).value;

    // Only show suggestions for StoreAddress field
    if (this.correctionData.fieldName !== 'StoreAddress') {
      this.showSuggestions.set(false);
      return;
    }

    if (input.length < 3) {
      this.suggestions.set([]);
      this.showSuggestions.set(false);
      return;
    }

    // Debounce API calls
    if (this.inputTimeout) {
      clearTimeout(this.inputTimeout);
    }

    this.inputTimeout = window.setTimeout(() => {
      this.fetchSuggestions(input);
    }, 300);
  }

  onAddressFocus() {
    if (this.correctionData.fieldName === 'StoreAddress' && this.suggestions().length > 0) {
      this.showSuggestions.set(true);
    }
  }

  onAddressBlur() {
    // Delay to allow click on suggestion
    setTimeout(() => {
      this.showSuggestions.set(false);
    }, 200);
  }

  selectSuggestion(suggestion: PlaceSuggestion) {
    this.correctionData.correctedValue = suggestion.description;
    this.correctionData.latitude = suggestion.latitude;
    this.correctionData.longitude = suggestion.longitude;
    this.suggestions.set([]);
    this.showSuggestions.set(false);
  }

  private fetchSuggestions(input: string) {
    this.http.get<PlacesAutocompleteResponse>(`${this.PLACES_API_URL}/autocomplete`, {
      params: { input, location: 'Malaysia' }
    }).subscribe({
      next: (response) => {
        if (response.success) {
          this.suggestions.set(response.suggestions);
          this.showSuggestions.set(true);
        }
      },
      error: (err) => {
        console.error('Error fetching address suggestions:', err);
        this.suggestions.set([]);
      }
    });
  }

  onFieldSelectionChange() {
    const fieldName = this.correctionData.fieldName;
    if (!fieldName) {
      this.correctionData.incorrectValue = '';
      return;
    }

    // Auto-populate incorrect value from current receipt data
    if (fieldName === 'StoreName') {
      this.correctionData.incorrectValue = this.receipt.storeName;
    } else if (fieldName === 'TotalAmount') {
      this.correctionData.incorrectValue = this.receipt.totalAmount.toString();
    } else if (fieldName === 'PurchaseDate') {
      const date = new Date(this.receipt.purchaseDate);
      // Format for display
      this.correctionData.incorrectValue = date.toLocaleDateString();
      // Set corrected value to ISO date format for date input (YYYY-MM-DD)
      this.correctionData.correctedValue = date.toISOString().split('T')[0];
    } else if (fieldName === 'StoreAddress') {
      this.correctionData.incorrectValue = this.receipt.storeAddress;
    } else if (fieldName.startsWith('Items[')) {
      // Parse item index and field: "Items[0].Name" or "Items[0].Price"
      const match = fieldName.match(/Items\[(\d+)\]\.(Name|Price)/);
      if (match) {
        const index = parseInt(match[1]);
        const field = match[2];
        const item = this.receipt.items[index];
        if (item) {
          this.correctionData.incorrectValue = field === 'Name' ? item.name : item.price.toString();
        }
      }
    }

    // Clear corrected value when field changes (except for PurchaseDate which we pre-populate)
    if (fieldName !== 'PurchaseDate') {
      this.correctionData.correctedValue = '';
    }
    this.correctionData.latitude = undefined;
    this.correctionData.longitude = undefined;
    this.suggestions.set([]);
    this.showSuggestions.set(false);
  }

  private resetForms() {
    this.correctionData = {
      receiptId: this.receipt.id,
      fieldName: '',
      incorrectValue: '',
      correctedValue: '',
      latitude: undefined,
      longitude: undefined
    };
    this.suggestions.set([]);
    this.showSuggestions.set(false);
  }
}

interface PlaceSuggestion {
  description: string;
  mainText: string;
  secondaryText: string;
  latitude?: number;
  longitude?: number;
}

interface PlacesAutocompleteResponse {
  success: boolean;
  suggestions: PlaceSuggestion[];
}

export interface CorrectionData {
  fieldName: string;
  correctedValue: string;
  latitude?: number;
  longitude?: number;
}
