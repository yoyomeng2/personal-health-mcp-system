-- Migration: Rename confirmatin column
-- Created: 2025-11-03
-- Purpose: Rename user profile column for tracking 30-day refresh prompts

-- Add date_last_updated to track profile validation
ALTER TABLE user_profile RENAME COLUMN date_last_updated TO date_last_confirmed;
