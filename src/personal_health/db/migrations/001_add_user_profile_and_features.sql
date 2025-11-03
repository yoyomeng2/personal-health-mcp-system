-- Migration: Add user profile and meal/alcohol feature columns
-- Created: 2025-11-03
-- Purpose: Support Phase 8 - ingredient feature storage and hybrid extraction

-- Create user_profile table for dietary preferences
CREATE TABLE IF NOT EXISTS user_profile (
    id TEXT PRIMARY KEY DEFAULT 'default_user',
    dietary_restrictions TEXT DEFAULT '[]',  -- JSON array: ["gluten-free", "vegan", etc.]
    allergies TEXT DEFAULT '[]',             -- JSON array: ["peanuts", "shellfish", etc.]
    preferences TEXT DEFAULT '{}',           -- JSON object: {"milk_type": "oat", "tortilla_type": "flour"}
    habits TEXT DEFAULT '{}',                -- JSON object: {"typical_breakfast": "cereal with oat milk"}
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Add binary feature columns to entries table (nullable integers: 0, 1, or NULL)
-- Meal features
ALTER TABLE entries ADD COLUMN has_beans INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN has_rice INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN has_pasta INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN has_tofu INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN has_nuts INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN has_peanut INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN is_gluten_free INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN has_dairy INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN is_spicy INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN is_fried INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN is_raw INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN has_coffee INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN has_greens INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN has_corn INTEGER DEFAULT NULL;

-- Alcohol features
ALTER TABLE entries ADD COLUMN has_alcohol INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN is_beer INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN is_wine INTEGER DEFAULT NULL;
ALTER TABLE entries ADD COLUMN is_multiple_drinks INTEGER DEFAULT NULL;

-- Substance features
ALTER TABLE entries ADD COLUMN has_thc INTEGER DEFAULT NULL;
