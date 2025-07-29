#!/bin/bash
# Docker Migration Fix Script
# This script helps fix migration issues in Docker environments

echo "=== Docker Migration Fix Script ==="
echo "This script will help fix database migration issues"
echo

# Function to run commands in the web container
run_in_container() {
    docker-compose exec web "$@"
}

# Function to run psql commands
run_psql() {
    docker-compose exec db psql -U jps_user -d jps_prospects -c "$1"
}

echo "1. Checking current migration state..."
run_in_container flask db current || echo "No migration state found"

echo
echo "2. Checking if problematic columns already exist..."
COLUMNS_CHECK=$(run_psql "SELECT column_name FROM information_schema.columns WHERE table_name = 'prospects' AND column_name IN ('estimated_value_text', 'naics_description', 'naics_source');" 2>&1)

if echo "$COLUMNS_CHECK" | grep -q "estimated_value_text"; then
    echo "Found existing columns that are causing migration conflicts!"
    echo
    echo "3. Attempting to fix migration state..."
    
    # Check if alembic_version table exists
    if ! run_psql "SELECT 1 FROM alembic_version LIMIT 1;" 2>/dev/null; then
        echo "Creating alembic_version table..."
        run_psql "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));"
    fi
    
    # Stamp the problematic migration as completed
    echo "Marking migration fbc0e1fbf50d as completed..."
    run_in_container flask db stamp fbc0e1fbf50d
    
    echo
    echo "4. Running remaining migrations..."
    run_in_container flask db upgrade
    
    echo
    echo "5. Final migration state:"
    run_in_container flask db current
else
    echo "No conflicting columns found. Running normal migration..."
    run_in_container flask db upgrade
fi

echo
echo "Migration fix complete!"
echo
echo "To restart the application:"
echo "  docker-compose restart web"