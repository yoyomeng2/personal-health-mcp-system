-- Migration: Add profile staleness tracking
-- Created: 2025-11-03
-- Purpose: Track when user profile was last validated to enable 30-day refresh prompts

-- Add date_last_updated to track profile validation
ALTER TABLE user_profile ADD COLUMN date_last_updated TEXT DEFAULT (datetime('now'));
