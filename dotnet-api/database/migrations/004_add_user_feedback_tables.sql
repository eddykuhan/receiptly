-- Migration: Add User Feedback and Validation Tables
-- Description: Adds tables for user corrections, issue reports, and debug sessions
-- Created: 2025-12-20

-- User Corrections Table
-- Stores user corrections to OCR results for ML training
CREATE TABLE user_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id UUID NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    image_hash VARCHAR(64),
    
    -- Original data (what OCR extracted)
    original_merchant VARCHAR(255),
    original_total DECIMAL(10,2),
    original_items JSONB,
    
    -- Corrected data (what user says is correct)
    corrected_merchant VARCHAR(255),
    corrected_total DECIMAL(10,2),
    corrected_items JSONB,
    
    -- Metadata
    correction_type VARCHAR(50) NOT NULL CHECK (correction_type IN ('merchant', 'items', 'total', 'multiple')),
    failed_source VARCHAR(50),  -- Which OCR source made the error (azure, llm_vision, etc.)
    notes TEXT,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Issue Reports Table
-- Stores user-reported issues with OCR results
CREATE TABLE issue_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id UUID NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    
    issue_type VARCHAR(50) NOT NULL CHECK (issue_type IN ('wrong_merchant', 'wrong_total', 'wrong_items', 'image_quality', 'other')),
    description TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high')),
    
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'investigating', 'resolved', 'closed')),
    resolution_notes TEXT,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- User Debug Sessions Table
-- Temporary debug mode activation per user
CREATE TABLE user_debug_sessions (
    user_id VARCHAR(255) PRIMARY KEY,
    enabled_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    remaining_requests INT NOT NULL DEFAULT 5,
    reason VARCHAR(255)
);

-- Indexes for better query performance
CREATE INDEX idx_user_corrections_user_id ON user_corrections(user_id);
CREATE INDEX idx_user_corrections_receipt_id ON user_corrections(receipt_id);
CREATE INDEX idx_user_corrections_created_at ON user_corrections(created_at DESC);
CREATE INDEX idx_user_corrections_correction_type ON user_corrections(correction_type);

CREATE INDEX idx_issue_reports_user_id ON issue_reports(user_id);
CREATE INDEX idx_issue_reports_receipt_id ON issue_reports(receipt_id);
CREATE INDEX idx_issue_reports_status ON issue_reports(status);
CREATE INDEX idx_issue_reports_severity ON issue_reports(severity);
CREATE INDEX idx_issue_reports_created_at ON issue_reports(created_at DESC);

CREATE INDEX idx_user_debug_sessions_expires_at ON user_debug_sessions(expires_at);

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for issue_reports updated_at
CREATE TRIGGER update_issue_reports_updated_at
    BEFORE UPDATE ON issue_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE user_corrections IS 'Stores user corrections to OCR results for ML training and accuracy tracking';
COMMENT ON TABLE issue_reports IS 'Stores user-reported issues with receipt processing';
COMMENT ON TABLE user_debug_sessions IS 'Temporary debug mode activation for specific users';

COMMENT ON COLUMN user_corrections.failed_source IS 'Which OCR source made the error: azure, llm_vision, tesseract, etc.';
COMMENT ON COLUMN user_corrections.correction_type IS 'Type of correction: merchant, items, total, or multiple fields';
COMMENT ON COLUMN issue_reports.severity IS 'Issue severity: low (minor), medium (needs review), high (urgent)';
COMMENT ON COLUMN issue_reports.status IS 'Issue status: open, investigating, resolved, or closed';
