import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  ConfidenceLevel,
  ReceiptValidation,
  CONFIDENCE_CONFIGS
} from '../../core/models/validation.model';

@Component({
  selector: 'app-validation-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="validation-badge" [class]="'badge-' + config.color" [title]="tooltipText">
      <span class="badge-icon">{{ config.icon }}</span>
      <span class="badge-label">{{ config.label }}</span>
      <span class="badge-percentage">{{ validation.overallConfidence | percent:'1.0-0' }}</span>
      
      @if (showTooltip) {
        <div class="tooltip-content">
          <div class="tooltip-header">
            <strong>{{ config.label }}</strong>
            <span class="confidence-score">{{ validation.overallConfidence | percent:'1.0-0' }} confidence</span>
          </div>
          
          <div class="confidence-breakdown">
            <div class="breakdown-item">
              <span class="label">Store Name:</span>
              <span class="value" [class.low]="validation.merchantConfidence < 0.7">
                {{ validation.merchantConfidence | percent:'1.0-0' }}
              </span>
            </div>
            <div class="breakdown-item">
              <span class="label">Items:</span>
              <span class="value" [class.low]="validation.itemsConfidence < 0.7">
                {{ validation.itemsConfidence | percent:'1.0-0' }}
              </span>
            </div>
            <div class="breakdown-item">
              <span class="label">Total:</span>
              <span class="value" [class.low]="validation.totalConfidence < 0.7">
                {{ validation.totalConfidence | percent:'1.0-0' }}
              </span>
            </div>
          </div>

          @if (validation.issues.length > 0) {
            <div class="issues-section">
              <div class="section-title">Issues Found:</div>
              @for (issue of validation.issues; track issue.field) {
                <div class="issue-item" [class]="'severity-' + issue.severity">
                  <span class="issue-icon">{{ issue.severity === 'error' ? '✗' : '⚠' }}</span>
                  <span class="issue-message">{{ issue.message }}</span>
                </div>
              }
            </div>
          }

          @if (validation.warnings.length > 0) {
            <div class="warnings-section">
              <div class="section-title">Warnings:</div>
              @for (warning of validation.warnings; track warning) {
                <div class="warning-item">{{ warning }}</div>
              }
            </div>
          }

          @if (validation.nextSteps) {
            <div class="next-steps">
              <strong>Suggested Action:</strong> {{ validation.nextSteps }}
            </div>
          }

          <div class="meta-info">
            <small>Processed in {{ validation.processingTimeMs }}ms using {{ validation.sourcesUsed.join(', ') }}</small>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .validation-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.375rem 0.75rem;
      border-radius: 1rem;
      font-size: 0.875rem;
      font-weight: 500;
      position: relative;
      cursor: help;
      transition: all 0.2s ease;
    }

    .validation-badge:hover {
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }

    .badge-success {
      background-color: #d4edda;
      color: #155724;
      border: 1px solid #c3e6cb;
    }

    .badge-warning {
      background-color: #fff3cd;
      color: #856404;
      border: 1px solid #ffeaa7;
    }

    .badge-danger {
      background-color: #f8d7da;
      color: #721c24;
      border: 1px solid #f5c6cb;
    }

    .badge-icon {
      font-size: 1rem;
    }

    .badge-label {
      display: none;
    }

    @media (min-width: 640px) {
      .badge-label {
        display: inline;
      }
    }

    .badge-percentage {
      font-weight: 600;
    }

    /* Tooltip */
    .validation-badge:hover .tooltip-content {
      display: block;
    }

    .tooltip-content {
      display: none;
      position: absolute;
      top: calc(100% + 0.5rem);
      left: 0;
      min-width: 300px;
      max-width: 400px;
      background: white;
      border: 1px solid #ddd;
      border-radius: 0.5rem;
      padding: 1rem;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      z-index: 1000;
      font-size: 0.875rem;
    }

    .tooltip-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
      padding-bottom: 0.5rem;
      border-bottom: 1px solid #eee;
    }

    .confidence-score {
      color: #666;
      font-size: 0.8rem;
    }

    .confidence-breakdown {
      margin-bottom: 0.75rem;
    }

    .breakdown-item {
      display: flex;
      justify-content: space-between;
      padding: 0.25rem 0;
    }

    .breakdown-item .label {
      color: #666;
    }

    .breakdown-item .value {
      font-weight: 600;
      color: #28a745;
    }

    .breakdown-item .value.low {
      color: #dc3545;
    }

    .issues-section,
    .warnings-section {
      margin-top: 0.75rem;
    }

    .section-title {
      font-weight: 600;
      margin-bottom: 0.5rem;
      font-size: 0.8rem;
      text-transform: uppercase;
      color: #666;
    }

    .issue-item {
      display: flex;
      align-items: start;
      gap: 0.5rem;
      padding: 0.375rem;
      margin-bottom: 0.25rem;
      border-radius: 0.25rem;
    }

    .severity-error {
      background-color: #f8d7da;
      color: #721c24;
    }

    .severity-warning {
      background-color: #fff3cd;
      color: #856404;
    }

    .issue-icon {
      flex-shrink: 0;
    }

    .issue-message {
      flex: 1;
      font-size: 0.85rem;
    }

    .warning-item {
      padding: 0.25rem 0;
      font-size: 0.85rem;
      color: #856404;
    }

    .next-steps {
      margin-top: 0.75rem;
      padding: 0.5rem;
      background-color: #e7f3ff;
      border-left: 3px solid #007bff;
      border-radius: 0.25rem;
      font-size: 0.85rem;
    }

    .meta-info {
      margin-top: 0.75rem;
      padding-top: 0.5rem;
      border-top: 1px solid #eee;
      color: #999;
    }
  `]
})
export class ValidationBadgeComponent {
  @Input({ required: true }) validation!: ReceiptValidation;
  @Input() showTooltip = true;

  get config() {
    return CONFIDENCE_CONFIGS[this.validation.confidenceLevel];
  }

  get tooltipText(): string {
    return `${this.config.description} - ${Math.round(this.validation.overallConfidence * 100)}% confidence`;
  }
}
