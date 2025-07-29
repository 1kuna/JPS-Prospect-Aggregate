#!/bin/bash
set -e

echo "=== JPS Prospect Aggregate Docker Entrypoint ==="
echo "Starting JPS Prospect Aggregate application..."

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to wait for database
wait_for_db() {
    log "Waiting for database to be ready..."
    local max_attempts=30
    local attempt=1
    
    while ! nc -z db 5432; do
        if [ $attempt -eq $max_attempts ]; then
            log "ERROR: Database not ready after $max_attempts attempts"
            exit 1
        fi
        log "Database not ready, attempt $attempt/$max_attempts"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log "Database connection successful!"
}

# Function to check if migrations are stuck
check_migration_state() {
    log "Checking current migration state..."
    
    # Try to get current revision, handle failures gracefully
    if CURRENT_REV=$(flask db current 2>/dev/null | head -1); then
        if [ -z "$CURRENT_REV" ]; then
            CURRENT_REV="none (empty)"
        fi
    else
        log "flask db current failed, database may not be initialized"
        CURRENT_REV="error (database not initialized)"
    fi
    
    log "Current revision: $CURRENT_REV"
    
    # Check if we have a partial migration state
    if echo "$CURRENT_REV" | grep -q "fbc0e1fbf50d"; then
        log "WARNING: Found partially applied migration fbc0e1fbf50d"
        log "This migration has been updated to handle existing columns safely"
    elif echo "$CURRENT_REV" | grep -q "error"; then
        log "Migration state check failed - will attempt to initialize from scratch"
    fi
}

# Function to run migrations
run_migrations() {
    log "Running database migrations..."
    
    cd /app
    
    # Set environment variables for Flask
    export FLASK_APP=run.py
    export FLASK_ENV=production
    
    # Check if this is a completely fresh database
    log "Checking if database is initialized..."
    if ! python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.engine.execute('SELECT 1 FROM alembic_version LIMIT 1')" 2>/dev/null; then
        log "Fresh database detected - no alembic_version table exists"
        log "Will run full migration setup"
        FRESH_DB=true
    else
        log "Existing database detected - checking migration state"
        check_migration_state
        FRESH_DB=false
    fi
    
    # Run migrations with detailed logging
    log "Executing flask db upgrade..."
    MIGRATION_OUTPUT=$(flask db upgrade 2>&1)
    MIGRATION_EXIT_CODE=$?
    
    log "Migration command completed with exit code: $MIGRATION_EXIT_CODE"
    
    if [ $MIGRATION_EXIT_CODE -eq 0 ]; then
        log "Database migrations completed successfully"
        
        # Verify tables were created
        if python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.engine.execute('SELECT 1 FROM prospects LIMIT 1')" 2>/dev/null; then
            log "SUCCESS: prospects table exists and is accessible"
        else
            log "WARNING: Migration succeeded but prospects table not accessible"
        fi
        
        return 0
    else
        log "ERROR: Database migrations failed with exit code $MIGRATION_EXIT_CODE"
        echo "$MIGRATION_OUTPUT" | grep -A5 -B5 "ERROR\|CRITICAL\|Traceback"
        
        # Check for specific errors
        if echo "$MIGRATION_OUTPUT" | grep -q "DuplicateColumn"; then
            log "NOTICE: Duplicate column error detected - this is expected if the database already has the columns"
            log "The migration has been updated to handle this gracefully"
            log "Attempting to mark migration as completed..."
            
            # Check which column is causing the issue
            if echo "$MIGRATION_OUTPUT" | grep -q "ai_enhanced_title"; then
                log "ai_enhanced_title column already exists, stamping migration 5fb5cc7eff5b"
                flask db stamp 5fb5cc7eff5b 2>/dev/null || true
            elif echo "$MIGRATION_OUTPUT" | grep -q "estimated_value_text"; then
                log "estimated_value_text column already exists, stamping migration fbc0e1fbf50d"
                flask db stamp fbc0e1fbf50d 2>/dev/null || true
            fi
            
            # Try to continue with remaining migrations
            if flask db upgrade; then
                log "Successfully continued with remaining migrations"
                return 0
            fi
        fi
        
        log "Checking final migration status..."
        flask db current || true
        log "Checking migration heads..."
        flask db heads || true
        
        # Show more detailed error information
        log "Full migration output:"
        echo "$MIGRATION_OUTPUT"
        
        # Try to diagnose the issue
        log "Attempting to diagnose migration issues..."
        
        # Check if alembic_version table exists
        if python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.engine.execute('SELECT 1 FROM alembic_version LIMIT 1')" 2>/dev/null; then
            log "alembic_version table exists"
        else
            log "alembic_version table missing - creating it"
            python -c "from app import create_app, db; from sqlalchemy import text; app = create_app(); app.app_context().push(); db.engine.execute(text('CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))'))" 2>/dev/null || true
        fi
        
        # List available migrations
        log "Available migration files:"
        ls -la /app/migrations/versions/ | head -10
        
        # Try one more time with very verbose output
        log "Attempting migration retry with verbose output..."
        flask db upgrade --verbose 2>&1 || true
        
        # For now, exit with error to prevent app startup with broken migrations
        log "ERROR: Cannot continue with failed migrations"
        exit 1
    fi
}

# Main execution
log "Environment: ${FLASK_ENV:-production}"
log "Database URL configured: $(echo $DATABASE_URL | cut -d@ -f2 || echo not set)"

wait_for_db
run_migrations

log "Starting application with command: $@"
exec "$@"