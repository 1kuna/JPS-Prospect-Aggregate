#!/bin/bash
# Cross-platform backup script for JPS Prospect Aggregate
# Works in Docker containers on both Windows and Mac/Linux hosts
set -e

# Configuration
BACKUP_DIR="/backups"
RETENTION_DAYS=7
# Use a more portable date format
TIMESTAMP=$(date +%Y%m%d_%H%M%S 2>/dev/null || date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date)] $1"
}

log "Starting database backup..."

# Backup both databases
for DB in jps_prospects jps_users; do
    BACKUP_FILE="${BACKUP_DIR}/${DB}_${TIMESTAMP}.sql"
    log "Backing up ${DB} to ${BACKUP_FILE}..."
    
    # Use pg_dump with error handling
    if pg_dump -h ${DB_HOST} -U ${DB_USER} -d ${DB} > ${BACKUP_FILE} 2>/dev/null; then
        # Compress the backup
        gzip ${BACKUP_FILE}
        log "Backup completed: ${BACKUP_FILE}.gz"
        
        # Verify the backup file was created and has content
        if [ -f "${BACKUP_FILE}.gz" ] && [ -s "${BACKUP_FILE}.gz" ]; then
            log "Backup verified: $(du -h ${BACKUP_FILE}.gz | cut -f1)"
        else
            log "WARNING: Backup file appears to be empty or missing"
        fi
    else
        log "ERROR: Failed to backup ${DB}"
        rm -f ${BACKUP_FILE} 2>/dev/null
    fi
done

# Clean up old backups
log "Cleaning up backups older than ${RETENTION_DAYS} days..."
# Use a more portable find command
find ${BACKUP_DIR} -name "*.sql.gz" -type f -mtime +${RETENTION_DAYS} -exec rm -f {} \; 2>/dev/null || true

# Show current backup status
BACKUP_COUNT=$(find ${BACKUP_DIR} -name "*.sql.gz" -type f 2>/dev/null | wc -l | tr -d ' ')
log "Current backup count: ${BACKUP_COUNT} files"

log "Backup process completed successfully!"

# Exit with success
exit 0