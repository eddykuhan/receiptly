import { Component, OnInit, inject, signal, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ReceiptService } from '../../core/services/receipt.service';
import { Receipt } from '../../core/models/receipt.model';
import { MyrPipe } from '../../core/pipes/myr.pipe';
import { ValidationBadgeComponent } from '../../shared/components/validation-badge.component';
import { FeedbackModalComponent } from '../../shared/components/feedback-modal.component';

@Component({
  selector: 'app-receipt-detail',
  standalone: true,
  imports: [
    CommonModule,
    MyrPipe,
    ValidationBadgeComponent,
    FeedbackModalComponent
  ],
  template: `
    <div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200 pb-24">
      @if (isLoading()) {
        <div class="flex items-center justify-center min-h-screen">
          <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
      } @else if (receipt()) {
        <!-- Header -->
        <header class="bg-gradient-to-r from-primary to-secondary p-6 shadow-lg">
          <div class="flex items-center gap-4 mb-4">
            <button (click)="goBack()" class="btn btn-circle btn-ghost text-white">
              <span class="material-icons">arrow_back</span>
            </button>
            <div>
              <h1 class="text-2xl font-bold text-white">Receipt Details</h1>
              <p class="text-white/90 text-sm">{{ receipt()!.purchaseDate | date:'MMMM d, yyyy' }}</p>
            </div>
          </div>

          @if (hasValidation()) {
            <div class="mt-4">
              <app-validation-badge [validation]="receipt()!.validation" />
            </div>
          }
        </header>

        <!-- Receipt Content -->
        <div class="p-4 space-y-4">
          <!-- Store Info Card -->
          <div class="card bg-base-100 shadow-md">
            <div class="card-body">
              <h2 class="card-title flex items-center gap-2">
                <span class="material-icons text-primary">store</span>
                Store Information
              </h2>
              <div class="space-y-3">
                <div class="field-with-confidence">
                  <div class="flex justify-between items-start">
                    <div>
                      <div class="text-sm text-base-content/60">Store Name</div>
                      <div class="font-semibold">{{ receipt()!.storeName }}</div>
                    </div>
                    @if (hasValidation()) {
                      <div class="confidence-indicator" [class]="getConfidenceClass(receipt()!.validation.merchantConfidence)">
                        {{ receipt()!.validation.merchantConfidence | percent:'1.0-0' }}
                      </div>
                    }
                  </div>
                </div>

                @if (receipt()!.storeAddress) {
                  <div>
                    <div class="text-sm text-base-content/60">Address</div>
                    <div>{{ receipt()!.storeAddress }}</div>
                  </div>
                }

                @if (receipt()!.storePhoneNumber) {
                  <div>
                    <div class="text-sm text-base-content/60">Phone</div>
                    <div>{{ receipt()!.storePhoneNumber }}</div>
                  </div>
                }
              </div>
            </div>
          </div>

          <!-- Total Amount Card -->
          <div class="card bg-base-100 shadow-md">
            <div class="card-body">
              <h2 class="card-title flex items-center gap-2">
                <span class="material-icons text-primary">receipt</span>
                Receipt Total
              </h2>
              <div class="space-y-2">
                <div class="field-with-confidence">
                  <div class="flex justify-between items-center">
                    <div>
                      <div class="text-sm text-base-content/60">Total Amount</div>
                      <div class="text-3xl font-bold font-mono">{{ receipt()!.totalAmount | myr }}</div>
                    </div>
                    @if (hasValidation()) {
                      <div class="confidence-indicator" [class]="getConfidenceClass(receipt()!.validation.totalConfidence)">
                        {{ receipt()!.validation.totalConfidence | percent:'1.0-0' }}
                      </div>
                    }
                  </div>
                </div>

                @if (receipt()!.subtotalAmount) {
                  <div class="flex justify-between">
                    <span class="text-base-content/60">Subtotal</span>
                    <span class="font-mono">{{ receipt()!.subtotalAmount | myr }}</span>
                  </div>
                }

                @if (receipt()!.taxAmount) {
                  <div class="flex justify-between">
                    <span class="text-base-content/60">Tax</span>
                    <span class="font-mono">{{ receipt()!.taxAmount | myr }}</span>
                  </div>
                }
              </div>
            </div>
          </div>

          <!-- Items Card -->
          <div class="card bg-base-100 shadow-md">
            <div class="card-body">
              <h2 class="card-title flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="material-icons text-primary">shopping_basket</span>
                  Items ({{ receipt()!.items.length }})
                </div>
                @if (hasValidation()) {
                  <div class="confidence-indicator" [class]="getConfidenceClass(receipt()!.validation.itemsConfidence)">
                    {{ receipt()!.validation.itemsConfidence | percent:'1.0-0' }}
                  </div>
                }
              </h2>
              <div class="space-y-2">
                @for (item of receipt()!.items; track item.id) {
                  <div class="flex justify-between items-center py-2 border-b border-base-200 last:border-0">
                    <div class="flex-1">
                      <div class="font-medium">{{ item.name }}</div>
                      @if (item.description) {
                        <div class="text-sm text-base-content/60">{{ item.description }}</div>
                      }
                      <div class="text-xs text-base-content/50">Qty: {{ item.quantity }}</div>
                    </div>
                    <div class="text-right">
                      <div class="font-mono font-bold">{{ item.price | myr }}</div>
                      @if (item.unitPrice && item.unitPrice !== item.price) {
                        <div class="text-xs text-base-content/60">{{ item.unitPrice | myr }} each</div>
                      }
                    </div>
                  </div>
                }
              </div>
            </div>
          </div>

          <!-- Validation Issues Card -->
          @if (hasValidation() && receipt()!.validation.issues.length > 0) {
            <div class="card bg-base-100 shadow-md border-l-4 border-warning">
              <div class="card-body">
                <h2 class="card-title flex items-center gap-2 text-warning">
                  <span class="material-icons">warning</span>
                  Validation Issues
                </h2>
                <div class="space-y-2">
                  @for (issue of receipt()!.validation.issues; track issue.field) {
                    <div class="alert" [class]="'alert-' + (issue.severity === 'error' ? 'error' : 'warning')">
                      <span class="material-icons">{{ issue.severity === 'error' ? 'error' : 'warning' }}</span>
                      <div>
                        <div class="font-medium">{{ issue.field }}</div>
                        <div class="text-sm">{{ issue.message }}</div>
                        @if (issue.suggestedAction) {
                          <div class="text-xs mt-1 opacity-80">Suggested: {{ issue.suggestedAction }}</div>
                        }
                      </div>
                    </div>
                  }
                </div>
              </div>
            </div>
          }

          <!-- Actions -->
          <div class="card bg-base-100 shadow-md">
            <div class="card-body">
              <div class="flex flex-wrap gap-2">
                <button class="btn btn-primary flex-1" (click)="openFeedbackModal()">
                  <span class="material-icons">edit</span>
                  Edit
                </button>
              </div>
            </div>
          </div>

          <!-- Meta Info -->
          @if (hasValidation()) {
            <div class="card bg-base-100 shadow-md">
              <div class="card-body">
                <h2 class="card-title text-sm">Processing Information</h2>
                <div class="text-xs space-y-1 text-base-content/60">
                  <div>Sources: {{ receipt()!.validation.sourcesUsed.join(', ') }}</div>
                  <div>Processing Time: {{ receipt()!.validation.processingTimeMs }}ms</div>
                  <div>Document Type: {{ receipt()!.validation.docType }}</div>
                </div>
              </div>
            </div>
          }
        </div>

        <!-- Feedback Modal -->
        <app-feedback-modal 
          [receipt]="receipt()!" 
          (closed)="closeFeedbackModal()"
          (correctionSubmitted)="onCorrectionSubmitted($event)" 
          #feedbackModal />
      } @else {
        <div class="flex flex-col items-center justify-center min-h-screen">
          <span class="material-icons text-6xl text-base-content/20 mb-4">receipt_long</span>
          <p class="text-xl font-semibold">Receipt not found</p>
          <button class="btn btn-primary mt-4" (click)="goBack()">Go Back</button>
        </div>
      }
    </div>
  `,
  styles: [`
    .field-with-confidence {
      position: relative;
    }

    .confidence-indicator {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0.25rem 0.5rem;
      border-radius: 0.5rem;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .confidence-high {
      background-color: #d4edda;
      color: #155724;
    }

    .confidence-medium {
      background-color: #fff3cd;
      color: #856404;
    }

    .confidence-low {
      background-color: #f8d7da;
      color: #721c24;
    }
  `]
})
export class ReceiptDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private receiptService = inject(ReceiptService);

  @ViewChild('feedbackModal') feedbackModal?: FeedbackModalComponent;

  receipt = signal<Receipt | null>(null);
  isLoading = signal(true);

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    const isNewUpload = this.route.snapshot.queryParamMap.get('new') === 'true';
    
    if (id) {
      this.loadReceipt(id);
      
      // Auto-open feedback modal for new uploads after a short delay
      if (isNewUpload) {
        setTimeout(() => {
          this.openFeedbackModal();
        }, 800);
      }
    } else {
      this.isLoading.set(false);
    }
  }

  loadReceipt(id: string) {
    this.receiptService.receipts$.subscribe(receipts => {
      const receipt = receipts.find(r => r.id === id);
      this.receipt.set(receipt || null);
      this.isLoading.set(false);
    });
  }

  goBack() {
    this.router.navigate(['/profile']);
  }

  hasValidation(): boolean {
    return this.receipt()?.validation != null;
  }

  getConfidenceClass(confidence: number): string {
    if (confidence >= 0.85) return 'confidence-high';
    if (confidence >= 0.7) return 'confidence-medium';
    return 'confidence-low';
  }

  openFeedbackModal() {
    this.feedbackModal?.open();
  }

  closeFeedbackModal() {
    // Modal closed
  }

  onCorrectionSubmitted(correction: any) {
    const currentReceipt = this.receipt();
    if (!currentReceipt) return;

    // Update the receipt data immediately with the corrected value
    const updatedReceipt = { ...currentReceipt };
    
    if (correction.fieldName === 'StoreName') {
      updatedReceipt.storeName = correction.correctedValue;
    } else if (correction.fieldName === 'TotalAmount') {
      updatedReceipt.totalAmount = parseFloat(correction.correctedValue);
    } else if (correction.fieldName === 'PurchaseDate') {
      updatedReceipt.purchaseDate = new Date(correction.correctedValue);
    } else if (correction.fieldName === 'StoreAddress') {
      updatedReceipt.storeAddress = correction.correctedValue;
      if (correction.latitude && correction.longitude) {
        updatedReceipt.latitude = correction.latitude;
        updatedReceipt.longitude = correction.longitude;
      }
    } else if (correction.fieldName.startsWith('Items[')) {
      // Parse item index and field: "Items[0].Name" or "Items[0].Price"
      const match = correction.fieldName.match(/Items\[(\d+)\]\.(Name|Price)/);
      if (match) {
        const index = parseInt(match[1]);
        const field = match[2];
        if (updatedReceipt.items[index]) {
          updatedReceipt.items = [...updatedReceipt.items];
          updatedReceipt.items[index] = { ...updatedReceipt.items[index] };
          if (field === 'Name') {
            updatedReceipt.items[index].name = correction.correctedValue;
          } else if (field === 'Price') {
            updatedReceipt.items[index].price = parseFloat(correction.correctedValue);
          }
        }
      }
    }

    // Update the signal to trigger UI refresh
    this.receipt.set(updatedReceipt);
    
    // Update the receipt service cache
    this.receiptService.updateLocalReceipt(updatedReceipt);
  }
}
