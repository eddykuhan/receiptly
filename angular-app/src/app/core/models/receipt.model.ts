export interface Receipt {
  id: string;
  userId: string;

  // Store information
  storeName: string;
  storeAddress: string;
  storePhoneNumber?: string;
  postalCode?: string;
  country?: string;

  // Receipt details
  purchaseDate: Date;
  totalAmount: number;
  subtotalAmount?: number;
  taxAmount?: number;
  tipAmount?: number;
  receiptType?: string;
  transactionId?: string;
  paymentMethod?: string;

  // Items
  items: ReceiptItem[];

  // Image and storage
  imageUrl?: string;
  originalFileName?: string;
  imageHash?: string;

  // Location data
  latitude?: number;
  longitude?: number;

  // OCR metadata
  ocrProvider?: string;
  ocrConfidence?: number;
  locationConfidence?: number;
  ocrStrategy?: string;

  // Validation fields (legacy)
  status: ReceiptStatus;
  validationConfidence?: number;
  validationMessage?: string;
  isValidReceipt: boolean;

  // Enhanced validation (from Python OCR service)
  validation?: any; // ReceiptValidation from validation.model.ts

  // Audit fields
  createdAt: Date;
  updatedAt?: Date;
  processedAt?: Date;
}

export interface ReceiptItem {
  id: string;
  name: string;
  canonicalName?: string;
  description?: string;
  price: number;
  quantity: number;
  unitPrice?: number;
  totalPrice?: number;
  category?: string;
  sku?: string;
  barcode?: string;
}

export enum ReceiptStatus {
  PendingValidation = 'PendingValidation',
  Validated = 'Validated',
  ValidationFailed = 'ValidationFailed',
  Processing = 'Processing',
  Failed = 'Failed'
}

export interface UploadReceiptResponse {
  success: boolean;
  receipt?: Receipt;
  error?: string;
  existingReceiptId?: string;
}
