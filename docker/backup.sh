#!/bin/bash
set -e

# Configuration
BACKUP_DIR="/backups"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

echo "[$(date)] Starting database backup..."

# Backup both databases
for DB in jps_prospects jps_users; do
    BACKUP_FILE="${BACKUP_DIR}/${DB}_${TIMESTAMP}.sql"
    echo "Backing up ${DB} to ${BACKUP_FILE}..."
    
    pg_dump -h ${DB_HOST} -U ${DB_USER} -d ${DB} > ${BACKUP_FILE}
    
    # Compress the backup
    gzip ${BACKUP_FILE}
    echo "Backup completed: ${BACKUP_FILE}.gz"
done

# Clean up old backups
echo "Cleaning up backups older than ${RETENTION_DAYS} days..."
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup process completed successfully!"