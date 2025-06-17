-- Add indexes for improved search performance
-- Run this script to add indexes to your PostgreSQL database

-- Add text search indexes for frequently searched columns
-- These are GIN indexes which are optimal for full-text search

-- Create GIN index for title searches
CREATE INDEX IF NOT EXISTS idx_prospects_title_gin 
ON prospects USING GIN (to_tsvector('english', title));

-- Create GIN index for description searches  
CREATE INDEX IF NOT EXISTS idx_prospects_description_gin 
ON prospects USING GIN (to_tsvector('english', description));

-- Create GIN index for agency searches
CREATE INDEX IF NOT EXISTS idx_prospects_agency_gin 
ON prospects USING GIN (to_tsvector('english', agency));

-- Create GIN index for JSON extra field to support NAICS alternate codes search
CREATE INDEX IF NOT EXISTS idx_prospects_extra_gin 
ON prospects USING GIN (extra);

-- Create composite index for common filter combinations
CREATE INDEX IF NOT EXISTS idx_prospects_naics_ollama
ON prospects (naics, ollama_processed_at);

-- Create index for place-based searches
CREATE INDEX IF NOT EXISTS idx_prospects_place
ON prospects (place_state, place_city);

-- Create partial index for non-processed prospects (common filter)
CREATE INDEX IF NOT EXISTS idx_prospects_unprocessed 
ON prospects (id) 
WHERE ollama_processed_at IS NULL;

-- Additional B-tree indexes for exact matches (already added in models.py)
-- These will be created automatically by SQLAlchemy:
-- CREATE INDEX IF NOT EXISTS ix_prospects_title ON prospects (title);
-- CREATE INDEX IF NOT EXISTS ix_prospects_description ON prospects (description);
-- CREATE INDEX IF NOT EXISTS ix_prospects_agency ON prospects (agency);
-- CREATE INDEX IF NOT EXISTS ix_prospects_place_city ON prospects (place_city);
-- CREATE INDEX IF NOT EXISTS ix_prospects_place_state ON prospects (place_state);