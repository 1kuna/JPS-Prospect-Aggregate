-- Add indexes for improved search performance in SQLite
-- Run this script to add indexes to your SQLite database

-- Create index for title searches
CREATE INDEX IF NOT EXISTS idx_prospects_title 
ON prospects (title);

-- Create index for description searches  
CREATE INDEX IF NOT EXISTS idx_prospects_description 
ON prospects (description);

-- Create index for agency searches
CREATE INDEX IF NOT EXISTS idx_prospects_agency 
ON prospects (agency);

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

-- Create index for JSON queries (SQLite 3.38.0+)
-- This helps with searching alternate NAICS codes in the extra field
CREATE INDEX IF NOT EXISTS idx_prospects_extra_naics
ON prospects (json_extract(extra, '$.llm_classification.all_naics_codes'));

-- Note: SQLite doesn't support GIN indexes like PostgreSQL,
-- so we use regular B-tree indexes instead