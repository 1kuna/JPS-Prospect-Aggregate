#!/bin/bash
set -e

# Function to create database if it doesn't exist
create_db() {
    local db=$1
    echo "Creating database ${db} if it doesn't exist..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        SELECT 'CREATE DATABASE ${db}'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${db}')\gexec
EOSQL
}

# Create both databases
create_db "jps_prospects"
create_db "jps_users"

echo "Databases initialized successfully!"