-- Backfill script for purchase_analytics_gold table
-- This script populates the gold layer from existing receipts and items data
-- Run this after applying the AddPurchaseAnalyticsGoldLayer migration

-- Insert all existing items with their receipt context into gold layer
INSERT INTO purchase_analytics_gold (
    "Id",
    "ItemId",
    "ReceiptId",
    "UserId",
    "ItemName",
    "CanonicalName",
    "UnitPrice",
    "TotalPrice",
    "Quantity",
    "PurchaseDate",
    "StoreName",
    "StoreAddress",
    "StorePhoneNumber",
    "Latitude",
    "Longitude",
    "LocationConfidence",
    "ReceiptType",
    "TransactionId",
    "PaymentMethod",
    "ReceiptStatus",
    "IsCorrected",
    "CorrectedAt",
    "CreatedAt"
)
SELECT 
    gen_random_uuid() AS "Id",
    i."Id" AS "ItemId",
    r."Id" AS "ReceiptId",
    r."UserId" AS "UserId",
    i."Name" AS "ItemName",
    -- Use canonical name from cache if available, otherwise use raw name
    COALESCE(cc."CanonicalName", i."CanonicalName", i."Name") AS "CanonicalName",
    COALESCE(i."UnitPrice", i."Price") AS "UnitPrice",
    COALESCE(i."TotalPrice", COALESCE(i."UnitPrice", i."Price") * i."Quantity") AS "TotalPrice",
    i."Quantity" AS "Quantity",
    r."PurchaseDate" AS "PurchaseDate",
    r."StoreName" AS "StoreName",
    r."StoreAddress" AS "StoreAddress",
    r."StorePhoneNumber" AS "StorePhoneNumber",
    r."Latitude" AS "Latitude",
    r."Longitude" AS "Longitude",
    r."LocationConfidence" AS "LocationConfidence",
    r."ReceiptType" AS "ReceiptType",
    r."TransactionId" AS "TransactionId",
    r."PaymentMethod" AS "PaymentMethod",
    r."Status" AS "ReceiptStatus",
    -- Mark as corrected if canonical name came from cache
    CASE WHEN cc."CanonicalName" IS NOT NULL THEN true ELSE false END AS "IsCorrected",
    -- Set corrected_at to cache created_at if corrected
    CASE WHEN cc."CanonicalName" IS NOT NULL THEN cc."CreatedAt" ELSE NULL END AS "CorrectedAt",
    i."CreatedAt" AS "CreatedAt"
FROM items i
INNER JOIN receipts r ON i."ReceiptId" = r."Id"
LEFT JOIN canonical_cache cc ON i."Name" = cc."RawName"
WHERE r."Id" IS NOT NULL;

-- Display summary
SELECT 
    COUNT(*) AS total_records_inserted,
    COUNT(DISTINCT "ReceiptId") AS unique_receipts,
    COUNT(DISTINCT "UserId") AS unique_users,
    SUM(CASE WHEN "IsCorrected" THEN 1 ELSE 0 END) AS corrected_records,
    SUM(CASE WHEN "Latitude" IS NOT NULL AND "Longitude" IS NOT NULL THEN 1 ELSE 0 END) AS records_with_location
FROM purchase_analytics_gold;
