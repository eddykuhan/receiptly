-- Migration: Fix User Corrections Table Schema
-- Description: Align user_corrections table with code model (field_name, incorrect_value, corrected_value)
-- Created: 2025-12-21

-- Drop old table and recreate with correct schema
DROP TABLE IF EXISTS user_corrections CASCADE;

-- User Corrections Table (Aligned with UserCorrection.cs model)
CREATE TABLE user_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id UUID NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    user_id VARCHAR(450) NOT NULL,
    
    -- Field-level correction
    field_name VARCHAR(100) NOT NULL,  -- "StoreName", "TotalAmount", "Items[0].Name"
    incorrect_value VARCHAR(1000),     -- What OCR extracted
    corrected_value VARCHAR(1000) NOT NULL,  -- What user corrected to
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better query performance
CREATE INDEX idx_user_corrections_user_id ON user_corrections(user_id);
CREATE INDEX idx_user_corrections_receipt_id ON user_corrections(receipt_id);
CREATE INDEX idx_user_corrections_created_at ON user_corrections(created_at DESC);
CREATE INDEX idx_user_corrections_receipt_field ON user_corrections(receipt_id, field_name);
