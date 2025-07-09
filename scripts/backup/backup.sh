#!/bin/bash
# PostgreSQL Backup Script with Local Storage
# This script performs automated backups with retention policies

# Load environment variables
if [ -f "/opt/jps/.env.production" ]; then
    source /opt/jps/.env.production
else
    # Fallback for development
    source .env.production 2>/dev/null || source .env 2>/dev/null
fi

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/opt/jps/backups}"
DATE=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)
DAY_OF_MONTH=$(date +%d)

# Retention settings (with defaults)
BACKUP_RETENTION_DAILY=${BACKUP_RETENTION_DAILY:-7}
BACKUP_RETENTION_WEEKLY=${BACKUP_RETENTION_WEEKLY:-4}
BACKUP_RETENTION_MONTHLY=${BACKUP_RETENTION_MONTHLY:-12}

# Logging
LOG_FILE="$BACKUP_DIR/logs/backup_${DATE}.log"
mkdir -p "$BACKUP_DIR/logs" "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly" "$BACKUP_DIR/monthly"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Backup function
backup_database() {
    local db_name=$1
    local db_url=$2
    local backup_type=$3
    local backup_file="$BACKUP_DIR/$backup_type/${db_name}_${backup_type}_${DATE}.sql.gz"
    
    log "Starting $backup_type backup for $db_name"
    
    # Create backup with progress indicator
    if pg_dump "$db_url" --verbose 2>>"$LOG_FILE" | gzip > "$backup_file"; then
        # Get backup size
        local size=$(du -h "$backup_file" | cut -f1)
        log "Backup successful: $backup_file (Size: $size)"
        
        # Verify backup integrity
        if gzip -t "$backup_file" 2>/dev/null; then
            log "Backup verification passed"
            
            # Calculate and log checksums
            local checksum=$(sha256sum "$backup_file" | cut -d' ' -f1)
            echo "$checksum  $backup_file" >> "$BACKUP_DIR/logs/checksums.txt"
            log "Checksum: $checksum"
            
            return 0
        else
            log "ERROR: Backup verification failed for $backup_file"
            rm -f "$backup_file"
            return 1
        fi
    else
        log "ERROR: Backup failed for $db_name"
        return 1
    fi
}

# Test database connection
test_connection() {
    local db_url=$1
    local db_name=$2
    
    if pg_isready -d "$db_url" >/dev/null 2>&1; then
        log "Connection test passed for $db_name"
        return 0
    else
        log "ERROR: Cannot connect to $db_name"
        return 1
    fi
}

# Main backup process
main() {
    log "=== Starting backup process ==="
    log "Backup directory: $BACKUP_DIR"
    log "Retention: Daily=$BACKUP_RETENTION_DAILY, Weekly=$BACKUP_RETENTION_WEEKLY, Monthly=$BACKUP_RETENTION_MONTHLY"
    
    # Test connections first
    local all_connected=true
    if ! test_connection "$DATABASE_URL" "jps_aggregate"; then
        all_connected=false
    fi
    if ! test_connection "$USER_DATABASE_URL" "jps_users"; then
        all_connected=false
    fi
    
    if [ "$all_connected" = false ]; then
        log "ERROR: Database connection test failed. Aborting backup."
        exit 1
    fi
    
    # Track backup success
    local backup_failed=false
    
    # Daily backups (always run)
    if ! backup_database "jps_aggregate" "$DATABASE_URL" "daily"; then
        backup_failed=true
    fi
    if ! backup_database "jps_users" "$USER_DATABASE_URL" "daily"; then
        backup_failed=true
    fi
    
    # Weekly backups (on Sunday)
    if [ "$DAY_OF_WEEK" -eq 7 ]; then
        log "Performing weekly backups"
        if ! backup_database "jps_aggregate" "$DATABASE_URL" "weekly"; then
            backup_failed=true
        fi
        if ! backup_database "jps_users" "$USER_DATABASE_URL" "weekly"; then
            backup_failed=true
        fi
    fi
    
    # Monthly backups (on 1st of month)
    if [ "$DAY_OF_MONTH" -eq 1 ]; then
        log "Performing monthly backups"
        if ! backup_database "jps_aggregate" "$DATABASE_URL" "monthly"; then
            backup_failed=true
        fi
        if ! backup_database "jps_users" "$USER_DATABASE_URL" "monthly"; then
            backup_failed=true
        fi
    fi
    
    # Cleanup old backups
    log "Starting cleanup process"
    
    # Daily cleanup
    local daily_deleted=$(find "$BACKUP_DIR/daily" -name "*.sql.gz" -mtime +${BACKUP_RETENTION_DAILY} -print -delete | wc -l)
    if [ "$daily_deleted" -gt 0 ]; then
        log "Deleted $daily_deleted old daily backups"
    fi
    
    # Weekly cleanup
    local weekly_deleted=$(find "$BACKUP_DIR/weekly" -name "*.sql.gz" -mtime +$((BACKUP_RETENTION_WEEKLY * 7)) -print -delete | wc -l)
    if [ "$weekly_deleted" -gt 0 ]; then
        log "Deleted $weekly_deleted old weekly backups"
    fi
    
    # Monthly cleanup
    local monthly_deleted=$(find "$BACKUP_DIR/monthly" -name "*.sql.gz" -mtime +$((BACKUP_RETENTION_MONTHLY * 30)) -print -delete | wc -l)
    if [ "$monthly_deleted" -gt 0 ]; then
        log "Deleted $monthly_deleted old monthly backups"
    fi
    
    # Report disk usage
    local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    log "Total backup directory size: $total_size"
    
    # Log backup inventory
    log "Current backup inventory:"
    log "  Daily: $(find "$BACKUP_DIR/daily" -name "*.sql.gz" | wc -l) backups"
    log "  Weekly: $(find "$BACKUP_DIR/weekly" -name "*.sql.gz" | wc -l) backups"
    log "  Monthly: $(find "$BACKUP_DIR/monthly" -name "*.sql.gz" | wc -l) backups"
    
    if [ "$backup_failed" = true ]; then
        log "=== Backup process completed with errors ==="
        exit 1
    else
        log "=== Backup process completed successfully ==="
        exit 0
    fi
}

# Run main function
main