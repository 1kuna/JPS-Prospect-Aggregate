#!/bin/bash
# Test restore script - Verifies backups without destroying data
# This script creates temporary databases to test restore procedures

# Load environment
if [ -f "/opt/jps/.env" ]; then
    source /opt/jps/.env
else
    # Fallback for development
    source .env 2>/dev/null || source .env 2>/dev/null
fi

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/opt/jps/backups}"
LOG_FILE="$BACKUP_DIR/logs/test_restore_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$BACKUP_DIR/logs"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Find latest backup
find_latest_backup() {
    local db_name=$1
    local backup_type=$2
    
    local latest=$(ls -t "$BACKUP_DIR/$backup_type/${db_name}_${backup_type}_"*.sql.gz 2>/dev/null | head -1)
    echo "$latest"
}

# Test single backup
test_backup() {
    local backup_file=$1
    local db_name=$2
    local test_db_name="${db_name}_test_$(date +%s)"
    
    log "Testing backup: $backup_file"
    log "Creating test database: $test_db_name"
    
    # Get connection parameters from original database URL
    local original_url=""
    if [ "$db_name" = "jps_aggregate" ]; then
        original_url="$DATABASE_URL"
    else
        original_url="$USER_DATABASE_URL"
    fi
    
    # Parse connection parameters
    local host=$(echo "$original_url" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    local port=$(echo "$original_url" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    local user=$(echo "$original_url" | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    local password=$(echo "$original_url" | sed -n 's/.*\/\/[^:]*:\([^@]*\)@.*/\1/p')
    
    # Create test database
    if PGPASSWORD="$password" createdb -h "$host" -p "$port" -U "$user" "$test_db_name" >> "$LOG_FILE" 2>&1; then
        log "Test database created successfully"
        
        # Construct test database URL
        local test_url="postgresql://${user}:${password}@${host}:${port}/${test_db_name}"
        
        # Restore to test database
        log "Restoring backup to test database..."
        if gunzip -c "$backup_file" | PGPASSWORD="$password" psql -h "$host" -p "$port" -U "$user" -d "$test_db_name" >> "$LOG_FILE" 2>&1; then
            log "Restore successful"
            
            # Verify restore
            log "Verifying restored data..."
            
            # Check table counts
            if [ "$db_name" = "jps_aggregate" ]; then
                local tables="prospects data_sources scraper_status decisions"
            else
                local tables="users user_settings"
            fi
            
            local all_good=true
            for table in $tables; do
                local count=$(PGPASSWORD="$password" psql -h "$host" -p "$port" -U "$user" -d "$test_db_name" -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | xargs)
                if [ -n "$count" ] && [ "$count" -ge 0 ]; then
                    log "  ✓ Table $table: $count rows"
                else
                    log "  ✗ Table $table: Failed to count rows"
                    all_good=false
                fi
            done
            
            # Clean up test database
            log "Cleaning up test database..."
            PGPASSWORD="$password" dropdb -h "$host" -p "$port" -U "$user" "$test_db_name" >> "$LOG_FILE" 2>&1
            
            if [ "$all_good" = true ]; then
                return 0
            else
                return 1
            fi
        else
            log "ERROR: Restore failed"
            # Clean up test database
            PGPASSWORD="$password" dropdb -h "$host" -p "$port" -U "$user" "$test_db_name" >> "$LOG_FILE" 2>&1
            return 1
        fi
    else
        log "ERROR: Failed to create test database"
        return 1
    fi
}

# Main test routine
main() {
    log "=== Starting backup test restore process ==="
    
    local overall_status=0
    
    # Test latest daily backups
    echo -e "${YELLOW}Testing daily backups...${NC}"
    
    for db_name in "jps_aggregate" "jps_users"; do
        local latest_backup=$(find_latest_backup "$db_name" "daily")
        
        if [ -n "$latest_backup" ]; then
            if test_backup "$latest_backup" "$db_name"; then
                echo -e "${GREEN}✓ $db_name daily backup test passed${NC}"
                log "SUCCESS: $db_name daily backup test passed"
            else
                echo -e "${RED}✗ $db_name daily backup test failed${NC}"
                log "FAILED: $db_name daily backup test failed"
                overall_status=1
            fi
        else
            echo -e "${YELLOW}⚠ No daily backup found for $db_name${NC}"
            log "WARNING: No daily backup found for $db_name"
        fi
    done
    
    # Test latest weekly backups (if it's Sunday or we have weekly backups)
    if [ -d "$BACKUP_DIR/weekly" ] && [ "$(ls -A $BACKUP_DIR/weekly 2>/dev/null)" ]; then
        echo ""
        echo -e "${YELLOW}Testing weekly backups...${NC}"
        
        for db_name in "jps_aggregate" "jps_users"; do
            local latest_backup=$(find_latest_backup "$db_name" "weekly")
            
            if [ -n "$latest_backup" ]; then
                if test_backup "$latest_backup" "$db_name"; then
                    echo -e "${GREEN}✓ $db_name weekly backup test passed${NC}"
                    log "SUCCESS: $db_name weekly backup test passed"
                else
                    echo -e "${RED}✗ $db_name weekly backup test failed${NC}"
                    log "FAILED: $db_name weekly backup test failed"
                    overall_status=1
                fi
            fi
        done
    fi
    
    # Summary
    echo ""
    if [ $overall_status -eq 0 ]; then
        echo -e "${GREEN}=== All backup tests passed ===${NC}"
        log "=== All backup tests passed ==="
    else
        echo -e "${RED}=== Some backup tests failed ===${NC}"
        log "=== Some backup tests failed ==="
        
        # Send alert (add your alerting mechanism here)
        # Example: mail -s "JPS Backup Test Failed" admin@example.com < "$LOG_FILE"
    fi
    
    log "Test results saved to: $LOG_FILE"
    exit $overall_status
}

# Run main function
main