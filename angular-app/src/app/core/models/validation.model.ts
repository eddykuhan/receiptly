/**
 * Receipt validation models matching Python OCR service output
 */

export interface ReceiptValidation {
  isValidReceipt: boolean;
  confidenceLevel: ConfidenceLevel;
  overallConfidence: number;
  merchantConfidence: number;
  itemsConfidence: number;
  totalConfidence: number;
  issues: ValidationIssue[];
  warnings: string[];
  requiresManualReview: boolean;
  docType: string;
  processingTimeMs: number;
  sourcesUsed: string[];
  confidenceMessage: string;
  nextSteps?: string;
}

export enum ConfidenceLevel {
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  VERY_LOW = 'very_low'
}

export interface ValidationIssue {
  field: string;
  issueType: 'low_confidence' | 'missing' | 'suspicious';
  severity: 'warning' | 'error';
  message: string;
  confidence?: number;
  suggestedAction?: string;
}

export interface ProcessedReceipt {
  receipt: any; // Receipt from OCR
  validation: ReceiptValidation;
  debugSessionId?: string;
}

/**
 * Feedback submission models
 */
export interface SubmitCorrectionRequest {
  receiptId: string;
  fieldName: string;
  incorrectValue?: string;
  correctedValue: string;
  latitude?: number;
  longitude?: number;
}

export interface ReportIssueRequest {
  receiptId: string;
  issueType: string;
  severity: 'Low' | 'Medium' | 'High' | 'Critical';
  description?: string;
}

export interface FeedbackResponse {
  success: boolean;
  message: string;
  correctionId?: string;
}

/**
 * UI Helper interfaces
 */
export interface ConfidenceBadgeConfig {
  level: ConfidenceLevel;
  color: string;
  icon: string;
  label: string;
  description: string;
}

export const CONFIDENCE_CONFIGS: Record<ConfidenceLevel, ConfidenceBadgeConfig> = {
  [ConfidenceLevel.HIGH]: {
    level: ConfidenceLevel.HIGH,
    color: 'success',
    icon: '✓',
    label: 'High Confidence',
    description: 'OCR extraction is highly accurate'
  },
  [ConfidenceLevel.MEDIUM]: {
    level: ConfidenceLevel.MEDIUM,
    color: 'warning',
    icon: '⚠',
    label: 'Medium Confidence',
    description: 'Please review the extracted data'
  },
  [ConfidenceLevel.LOW]: {
    level: ConfidenceLevel.LOW,
    color: 'danger',
    icon: '!',
    label: 'Low Confidence',
    description: 'Manual review recommended'
  },
  [ConfidenceLevel.VERY_LOW]: {
    level: ConfidenceLevel.VERY_LOW,
    color: 'danger',
    icon: '✗',
    label: 'Very Low Confidence',
    description: 'Extraction may be inaccurate'
  }
};

export const ISSUE_TYPES = [
  { value: 'wrong_merchant', label: 'Wrong Store Name' },
  { value: 'wrong_total', label: 'Wrong Total Amount' },
  { value: 'wrong_items', label: 'Wrong Items' },
  { value: 'missing_items', label: 'Missing Items' },
  { value: 'duplicate_items', label: 'Duplicate Items' },
  { value: 'image_quality', label: 'Image Quality Issue' },
  { value: 'wrong_date', label: 'Wrong Date' },
  { value: 'other', label: 'Other Issue' }
];
