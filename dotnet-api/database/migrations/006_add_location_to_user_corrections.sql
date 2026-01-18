-- Migration: Add Location Fields to User Corrections
-- Description: Add latitude and longitude to track corrected store locations
-- Created: 2025-12-21

-- Add latitude and longitude columns for corrected locations
ALTER TABLE user_corrections 
ADD COLUMN latitude DOUBLE PRECISION,
ADD COLUMN longitude DOUBLE PRECISION;

-- Create spatial index for location queries (PostGIS-compatible syntax)
CREATE INDEX idx_user_corrections_location ON user_corrections(latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN user_corrections.latitude IS 'Latitude of corrected store location (WGS84)';
COMMENT ON COLUMN user_corrections.longitude IS 'Longitude of corrected store location (WGS84)';
