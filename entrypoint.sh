#!/bin/bash
# Cross-platform entrypoint script for JPS Prospect Aggregate
# Works on both Windows (via Docker) and Mac/Linux
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
    
    # Use a more portable way to check database connectivity
    while ! pg_isready -h db -p 5432 -U jps_user >/dev/null 2>&1; do
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
    export FLASK_ENV=${FLASK_ENV:-production}
    
    # Check if this is a completely fresh database
    log "Checking if database is initialized..."
    # Use a more robust check that handles connection issues better
    FRESH_DB=false
    if python3 -c "
import sys
try:
    from app import create_app, db
    from sqlalchemy import text
    app = create_app()
    with app.app_context():
        db.session.execute(text('SELECT 1 FROM alembic_version LIMIT 1'))
        sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        log "Existing database detected - checking migration state"
        check_migration_state
    else
        log "Fresh database detected - no alembic_version table exists"
        log "Will run full migration setup"
        FRESH_DB=true
    fi
    
    # Run migrations with detailed logging
    log "Executing flask db upgrade..."
    MIGRATION_OUTPUT=$(flask db upgrade 2>&1)
    MIGRATION_EXIT_CODE=$?
    
    log "Migration command completed with exit code: $MIGRATION_EXIT_CODE"
    
    # Always show migration output for debugging
    if [ $MIGRATION_EXIT_CODE -ne 0 ]; then
        log "Migration failed! Full output:"
        echo "$MIGRATION_OUTPUT"
    fi
    
    if [ $MIGRATION_EXIT_CODE -eq 0 ]; then
        log "Database migrations completed successfully"
        
        # Verify tables were created and accessible
        log "Verifying database tables are accessible from Flask app context..."
        VERIFY_OUTPUT=$(python3 << 'PYTHON_SCRIPT'
import sys
import traceback

try:
    from app import create_app
    from app.database import db
    from app.database.models import Prospect, DataSource, ScraperStatus
    from sqlalchemy import text
    
    print('Creating Flask app...')
    app = create_app()
    
    with app.app_context():
        print('Testing database connectivity...')
        
        # Test prospects table
        result = db.session.execute(text('SELECT COUNT(*) FROM prospects')).fetchone()
        prospects_count = result[0] if result else 0
        print(f'SUCCESS: prospects table accessible, contains {prospects_count} records')
        
        # Test data_sources table  
        result = db.session.execute(text('SELECT COUNT(*) FROM data_sources')).fetchone()
        data_sources_count = result[0] if result else 0
        print(f'SUCCESS: data_sources table accessible, contains {data_sources_count} records')
        
        # Test scraper_status table
        result = db.session.execute(text('SELECT COUNT(*) FROM scraper_status')).fetchone()
        status_count = result[0] if result else 0
        print(f'SUCCESS: scraper_status table accessible, contains {status_count} records')
        
        # Test using ORM models
        prospects_orm_count = db.session.query(Prospect).count()
        print(f'SUCCESS: Prospect ORM model working, found {prospects_orm_count} records')
        
        print('VERIFICATION_SUCCESS: All tables accessible from Flask app context')
        
except Exception as e:
    print(f'VERIFICATION_ERROR: {e}')
    print('TRACEBACK:')
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT
)
        VERIFY_EXIT_CODE=$?
        
        if [ $VERIFY_EXIT_CODE -eq 0 ]; then
            log "Database tables verification successful"
            echo "$VERIFY_OUTPUT" | grep "SUCCESS:"
            echo "$VERIFY_OUTPUT" | grep "VERIFICATION_SUCCESS"
        else
            log "WARNING: Database tables verification failed"
            echo "$VERIFY_OUTPUT"
            log "This may cause issues with the web application accessing data"
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
        if python -c "from app import create_app, db; from sqlalchemy import text; app = create_app(); app.app_context().push(); db.session.execute(text('SELECT 1 FROM alembic_version LIMIT 1'))" 2>/dev/null; then
            log "alembic_version table exists"
        else
            log "alembic_version table missing - creating it"
            python -c "from app import create_app, db; from sqlalchemy import text; app = create_app(); app.app_context().push(); db.session.execute(text('CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))'))" 2>/dev/null || true
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

# Function to initialize user database
init_user_database() {
    log "Initializing user database..."
    
    cd /app
    
    # Set environment variables for Flask
    export FLASK_APP=run.py
    export FLASK_ENV=${FLASK_ENV:-production}
    
    # Run the dedicated user database initialization script
    USER_INIT_OUTPUT=$(python scripts/init_user_database.py 2>&1)
    USER_INIT_EXIT_CODE=$?
    
    log "User database initialization completed with exit code: $USER_INIT_EXIT_CODE"
    
    if [ $USER_INIT_EXIT_CODE -eq 0 ]; then
        log "User database initialized successfully"
        echo "$USER_INIT_OUTPUT" | grep -E "(SUCCESS|✅)"
        return 0
    else
        log "ERROR: User database initialization failed"
        echo "$USER_INIT_OUTPUT"
        
        # Check if it's just because tables already exist
        if echo "$USER_INIT_OUTPUT" | grep -q "already exists"; then
            log "NOTICE: User tables already exist, continuing..."
            return 0
        fi
        
        log "ERROR: Cannot continue with failed user database initialization"
        exit 1
    fi
}

# Function to create super admin
create_super_admin() {
    log "Creating super admin user..."
    
    cd /app
    
    # Set environment variables for Flask
    export FLASK_APP=run.py
    export FLASK_ENV=${FLASK_ENV:-production}
    
    # Run the super admin creation script
    SUPER_ADMIN_OUTPUT=$(python scripts/create_super_admin.py 2>&1)
    SUPER_ADMIN_EXIT_CODE=$?
    
    log "Super admin creation completed with exit code: $SUPER_ADMIN_EXIT_CODE"
    
    if [ $SUPER_ADMIN_EXIT_CODE -eq 0 ]; then
        log "Super admin user created/updated successfully"
        echo "$SUPER_ADMIN_OUTPUT" | grep -E "(SUCCESS|✅|already exists as super_admin)"
        return 0
    else
        log "WARNING: Super admin creation failed, but continuing startup"
        echo "$SUPER_ADMIN_OUTPUT"
        
        # Don't exit on failure - this is not critical for startup
        # The admin can be created manually later if needed
        log "Super admin can be created manually later using: python scripts/create_super_admin.py"
        return 0
    fi
}

# Main execution
log "Starting JPS Prospect Aggregate Container"
log "Environment: ${FLASK_ENV:-production}"
log "Database URL configured: $(echo $DATABASE_URL | sed 's/:[^:]*@/:****@/' || echo 'not set')"
log "Platform: $(uname -s)"

wait_for_db
run_migrations
init_user_database
create_super_admin

log "Starting application with command: $@"
exec "$@"