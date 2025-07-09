-- PostgreSQL initialization script for business database
-- This script runs when the container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For fuzzy text matching

-- Set optimal configuration for the database
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';

-- Create indexes for better performance (after migration)
-- Note: These will be created by Alembic migrations, but included here for reference
-- CREATE INDEX idx_prospects_agency ON prospects(agency);
-- CREATE INDEX idx_prospects_source_id ON prospects(source_id);
-- CREATE INDEX idx_prospects_posted_date ON prospects(posted_date);
-- CREATE INDEX idx_prospects_dollar_value ON prospects(dollar_value);
-- CREATE INDEX idx_prospects_llm_processed ON prospects(llm_processed);
-- CREATE INDEX idx_decisions_prospect_id ON decisions(prospect_id);
-- CREATE INDEX idx_decisions_user_id ON decisions(user_id);