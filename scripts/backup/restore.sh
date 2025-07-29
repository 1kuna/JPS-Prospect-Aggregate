#!/bin/bash
# PostgreSQL Restore Script
# Safely restore database from backup with verification

# Load environment
if [ -f "/opt/jps/.env" ]; then
    source /opt/jps/.env
else
    # Fallback for development
    source .env 2>/dev/null || source .env 2>/dev/null
fi

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/opt/jps/backups}"
LOG_DIR="$BACKUP_DIR/logs"
mkdir -p "$LOG_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Usage function
usage() {
    echo "Usage: $0 -d database_name -f backup_file [-t target_db_url] [-n]"
    echo ""
    echo "Options:"
    echo "  -d  Database name (jps_aggregate or jps_users)"
    echo "  -f  Path to backup file (can be .sql or .sql.gz)"
    echo "  -t  Target database URL (optional, defaults to production)"
    echo "  -n  No safety backup (skip pre-restore backup)"
    echo ""
    echo "Examples:"
    echo "  $0 -d jps_aggregate -f /opt/jps/backups/daily/jps_aggregate_daily_20240315_020000.sql.gz"
    echo "  $0 -d jps_users -f backup.sql -t postgresql://user:pass@localhost:5432/testdb"
    exit 1
}

# Parse arguments
SKIP_SAFETY_BACKUP=false
while getopts "d:f:t:nh" opt; do
    case $opt in
        d) DB_NAME="$OPTARG" ;;
        f) BACKUP_FILE="$OPTARG" ;;
        t) TARGET_URL="$OPTARG" ;;
        n) SKIP_SAFETY_BACKUP=true ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Validate arguments
if [ -z "$DB_NAME" ] || [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}ERROR: Missing required arguments${NC}"
    usage
fi

# Validate backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}ERROR: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Set target URL if not provided
if [ -z "$TARGET_URL" ]; then
    if [ "$DB_NAME" = "jps_aggregate" ]; then
        TARGET_URL="$DATABASE_URL"
    elif [ "$DB_NAME" = "jps_users" ]; then
        TARGET_URL="$USER_DATABASE_URL"
    else
        echo -e "${RED}ERROR: Unknown database name: $DB_NAME${NC}"
        echo "Valid options: jps_aggregate, jps_users"
        exit 1
    fi
fi

# Create restore log
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/restore_${TIMESTAMP}.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Test database connection
test_connection() {
    log "Testing database connection..."
    if pg_isready -d "$TARGET_URL" >/dev/null 2>&1; then
        log "Connection test passed"
        return 0
    else
        log "ERROR: Cannot connect to database"
        return 1
    fi
}

# Get database size
get_db_size() {
    local size=$(psql "$TARGET_URL" -t -c "SELECT pg_size_pretty(pg_database_size(current_database()));" 2>/dev/null | xargs)
    echo "$size"
}

# Verify backup file
verify_backup() {
    log "Verifying backup file..."
    
    # Check if gzipped
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        if gzip -t "$BACKUP_FILE" 2>/dev/null; then
            log "Backup file verification passed (gzip format)"
            
            # Check content
            local lines=$(gunzip -c "$BACKUP_FILE" | wc -l)
            log "Backup contains $lines lines"
            
            # Check for essential PostgreSQL backup markers
            if gunzip -c "$BACKUP_FILE" | head -100 | grep -q "PostgreSQL database dump"; then
                log "Backup appears to be a valid PostgreSQL dump"
                return 0
            else
                log "WARNING: Backup may not be a valid PostgreSQL dump"
                return 1
            fi
        else
            log "ERROR: Backup file is corrupted (gzip verification failed)"
            return 1
        fi
    else
        # Plain SQL file
        local lines=$(wc -l < "$BACKUP_FILE")
        log "Backup contains $lines lines"
        
        if head -100 "$BACKUP_FILE" | grep -q "PostgreSQL database dump"; then
            log "Backup appears to be a valid PostgreSQL dump"
            return 0
        else
            log "WARNING: Backup may not be a valid PostgreSQL dump"
            return 1
        fi
    fi
}

# Create safety backup
create_safety_backup() {
    if [ "$SKIP_SAFETY_BACKUP" = true ]; then
        log "Skipping safety backup (--no-safety-backup flag)"
        return 0
    fi
    
    log "Creating safety backup before restore..."
    local safety_backup="$BACKUP_DIR/migration/pre_restore_${DB_NAME}_${TIMESTAMP}.sql.gz"
    mkdir -p "$BACKUP_DIR/migration"
    
    if pg_dump "$TARGET_URL" --verbose 2>>"$LOG_FILE" | gzip > "$safety_backup"; then
        local size=$(du -h "$safety_backup" | cut -f1)
        log "Safety backup created: $safety_backup (Size: $size)"
        SAFETY_BACKUP_PATH="$safety_backup"
        return 0
    else
        log "ERROR: Failed to create safety backup"
        return 1
    fi
}

# Perform restore
perform_restore() {
    log "Starting database restore..."
    
    # Drop existing connections (optional, requires superuser)
    log "Attempting to terminate existing connections..."
    psql "$TARGET_URL" -c "
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = current_database()
          AND pid <> pg_backend_pid();
    " >> "$LOG_FILE" 2>&1 || log "Note: Could not terminate connections (may require superuser)"
    
    # Perform restore based on file type
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        log "Restoring from compressed backup..."
        if gunzip -c "$BACKUP_FILE" | psql "$TARGET_URL" >> "$LOG_FILE" 2>&1; then
            log "Restore command executed successfully"
            return 0
        else
            log "ERROR: Restore command failed"
            return 1
        fi
    else
        log "Restoring from plain SQL backup..."
        if psql "$TARGET_URL" < "$BACKUP_FILE" >> "$LOG_FILE" 2>&1; then
            log "Restore command executed successfully"
            return 0
        else
            log "ERROR: Restore command failed"
            return 1
        fi
    fi
}

# Verify restore
verify_restore() {
    log "Verifying restored database..."
    
    # Check connection
    if ! test_connection; then
        return 1
    fi
    
    # Check basic tables exist
    local tables_check=$(psql "$TARGET_URL" -t -c "
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
          AND table_type = 'BASE TABLE';
    " 2>/dev/null | xargs)
    
    if [ -n "$tables_check" ] && [ "$tables_check" -gt 0 ]; then
        log "Found $tables_check tables in database"
        
        # Check row counts for main tables
        if [ "$DB_NAME" = "jps_aggregate" ]; then
            for table in prospects data_sources scraper_status decisions; do
                local count=$(psql "$TARGET_URL" -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | xargs)
                if [ -n "$count" ]; then
                    log "  Table $table: $count rows"
                fi
            done
        elif [ "$DB_NAME" = "jps_users" ]; then
            for table in users user_settings; do
                local count=$(psql "$TARGET_URL" -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | xargs)
                if [ -n "$count" ]; then
                    log "  Table $table: $count rows"
                fi
            done
        fi
        
        return 0
    else
        log "ERROR: No tables found in restored database"
        return 1
    fi
}

# Main restore process
main() {
    echo -e "${GREEN}=== PostgreSQL Database Restore ===${NC}"
    echo ""
    echo "Database: $DB_NAME"
    echo "Backup file: $BACKUP_FILE"
    echo "Target database: $(echo $TARGET_URL | sed 's/:[^:]*@/:****@/')"  # Hide password
    echo ""
    
    # Get current database size
    local current_size=$(get_db_size)
    if [ -n "$current_size" ]; then
        echo "Current database size: $current_size"
    fi
    
    # Confirm
    echo -e "${YELLOW}WARNING: This will overwrite the existing database!${NC}"
    read -p "Are you sure you want to continue? Type 'yes' to confirm: " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo -e "${YELLOW}Restore cancelled${NC}"
        exit 0
    fi
    
    log "=== Starting restore process ==="
    
    # Step 1: Test connection
    if ! test_connection; then
        echo -e "${RED}ERROR: Cannot connect to database${NC}"
        exit 1
    fi
    
    # Step 2: Verify backup
    if ! verify_backup; then
        echo -e "${YELLOW}WARNING: Backup verification failed${NC}"
        read -p "Continue anyway? (yes/no): " force
        if [ "$force" != "yes" ]; then
            log "Restore cancelled due to backup verification failure"
            exit 1
        fi
    fi
    
    # Step 3: Create safety backup
    if ! create_safety_backup; then
        echo -e "${RED}ERROR: Failed to create safety backup${NC}"
        read -p "Continue without safety backup? (yes/no): " force
        if [ "$force" != "yes" ]; then
            log "Restore cancelled due to safety backup failure"
            exit 1
        fi
    fi
    
    # Step 4: Perform restore
    echo ""
    echo "Performing restore (this may take several minutes)..."
    
    if perform_restore; then
        echo -e "${GREEN}Restore completed${NC}"
        
        # Step 5: Verify restore
        if verify_restore; then
            echo -e "${GREEN}Restore verification passed${NC}"
            
            # Show new database size
            local new_size=$(get_db_size)
            if [ -n "$new_size" ]; then
                log "New database size: $new_size"
            fi
            
            log "=== Restore completed successfully ==="
            echo ""
            echo -e "${GREEN}Success! Database restored from backup.${NC}"
            
            if [ -n "$SAFETY_BACKUP_PATH" ]; then
                echo ""
                echo "Safety backup available at:"
                echo "  $SAFETY_BACKUP_PATH"
            fi
        else
            echo -e "${RED}ERROR: Restore verification failed${NC}"
            log "=== Restore completed with verification errors ==="
            
            if [ -n "$SAFETY_BACKUP_PATH" ]; then
                echo ""
                echo "You can restore from the safety backup using:"
                echo "  $0 -d $DB_NAME -f $SAFETY_BACKUP_PATH"
            fi
            exit 1
        fi
    else
        echo -e "${RED}ERROR: Restore failed${NC}"
        log "=== Restore failed ==="
        
        if [ -n "$SAFETY_BACKUP_PATH" ]; then
            echo ""
            echo "You can restore from the safety backup using:"
            echo "  $0 -d $DB_NAME -f $SAFETY_BACKUP_PATH"
        fi
        exit 1
    fi
}

# Run main function
main