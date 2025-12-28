-- Migration: Allow scraped data in purchase_analytics_gold
-- Description: Makes User/Receipt specific columns nullable and adds Source column

-- 1. Make columns nullable
ALTER TABLE purchase_analytics_gold ALTER COLUMN "ReceiptId" DROP NOT NULL;
ALTER TABLE purchase_analytics_gold ALTER COLUMN "UserId" DROP NOT NULL;
ALTER TABLE purchase_analytics_gold ALTER COLUMN "TransactionId" DROP NOT NULL;
ALTER TABLE purchase_analytics_gold ALTER COLUMN "PaymentMethod" DROP NOT NULL;

-- 2. Add Source column to track origin (default to UserReceipt for existing data)
ALTER TABLE purchase_analytics_gold ADD COLUMN IF NOT EXISTS "Source" text DEFAULT 'UserReceipt';

-- 3. Update existing scraped records if any (optional cleanup, but good practice)
-- UPDATE purchase_analytics_gold SET "Source" = 'Scraper' WHERE "ReceiptId" IS NULL;
