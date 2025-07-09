-- PostgreSQL initialization script for user database
-- This script runs when the container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create auth schema for better organization
CREATE SCHEMA IF NOT EXISTS auth;

-- Set search path to include auth schema
ALTER DATABASE jps_users SET search_path TO public, auth;

-- Optimize for authentication workload
ALTER SYSTEM SET shared_buffers = '128MB';
ALTER SYSTEM SET effective_cache_size = '512MB';
ALTER SYSTEM SET work_mem = '2MB';

-- Note: User tables will be created by the application
-- The schema is kept separate for security isolation