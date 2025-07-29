#!/bin/bash
set -e

echo "Starting database initialization..."

# Function to create database if it doesn't exist
create_db() {
    local db=$1
    echo "Creating database '${db}' if it doesn't exist..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="postgres" <<-EOSQL
        SELECT 'CREATE DATABASE ${db}'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${db}')\gexec
EOSQL
    echo "✓ Database '${db}' ready"
}

# Verify POSTGRES_USER is set
if [ -z "$POSTGRES_USER" ]; then
    echo "ERROR: POSTGRES_USER environment variable is not set"
    exit 1
fi

# Create both databases
create_db "jps_prospects" 
create_db "jps_users"

echo "✓ All databases initialized successfully!"