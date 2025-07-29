#!/bin/bash
# Automated database maintenance script for PostgreSQL
# Performs VACUUM, ANALYZE, and other maintenance tasks

# Load environment
if [ -f "/opt/jps/.env" ]; then
    source /opt/jps/.env
else
    # Fallback for development
    source .env 2>/dev/null || source .env 2>/dev/null
fi

# Configuration
MAINTENANCE_DIR="${BACKUP_DIR:-/opt/jps/backups}/maintenance"
LOG_FILE="$MAINTENANCE_DIR/logs/maintenance_$(date +%Y%m%d_%H%M%S).log"
REPORT_FILE="$MAINTENANCE_DIR/reports/maintenance_report_$(date +%Y%m%d).html"

# Create directories
mkdir -p "$MAINTENANCE_DIR/logs" "$MAINTENANCE_DIR/reports"

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✓ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ✗ $1${NC}" | tee -a "$LOG_FILE"
}

# Database connection test
test_connection() {
    local db_url=$1
    local db_name=$2
    
    if psql "$db_url" -c "SELECT 1;" >/dev/null 2>&1; then
        log_success "Connected to $db_name database"
        return 0
    else
        log_error "Failed to connect to $db_name database"
        return 1
    fi
}

# Run VACUUM ANALYZE on all tables
run_vacuum() {
    local db_url=$1
    local db_name=$2
    
    log "Running VACUUM ANALYZE on $db_name database..."
    
    # Get list of tables that need vacuuming
    local tables_to_vacuum=$(psql "$db_url" -t -c "
        SELECT schemaname || '.' || tablename
        FROM pg_stat_user_tables
        WHERE n_dead_tup > 1000
        ORDER BY n_dead_tup DESC;
    ")
    
    if [ -z "$tables_to_vacuum" ]; then
        log "No tables need vacuuming in $db_name"
        return 0
    fi
    
    # Vacuum each table individually for better progress tracking
    echo "$tables_to_vacuum" | while read -r table; do
        if [ -n "$table" ]; then
            log "  Vacuuming table: $table"
            if psql "$db_url" -c "VACUUM ANALYZE $table;" >> "$LOG_FILE" 2>&1; then
                log_success "  Vacuumed $table"
            else
                log_error "  Failed to vacuum $table"
            fi
        fi
    done
    
    # Run a general VACUUM ANALYZE to catch anything missed
    log "Running general VACUUM ANALYZE..."
    if psql "$db_url" -c "VACUUM ANALYZE;" >> "$LOG_FILE" 2>&1; then
        log_success "VACUUM ANALYZE completed for $db_name"
    else
        log_error "VACUUM ANALYZE failed for $db_name"
    fi
}

# Reindex tables if needed
reindex_if_needed() {
    local db_url=$1
    local db_name=$2
    
    log "Checking for indexes that need reindexing in $db_name..."
    
    # Find bloated indexes (simplified check)
    local bloated_indexes=$(psql "$db_url" -t -c "
        SELECT indexname
        FROM pg_stat_user_indexes
        WHERE pg_relation_size(indexrelid) > 10485760  -- 10MB
          AND idx_scan > 0  -- Only reindex used indexes
        ORDER BY pg_relation_size(indexrelid) DESC
        LIMIT 5;
    ")
    
    if [ -n "$bloated_indexes" ]; then
        echo "$bloated_indexes" | while read -r index; do
            if [ -n "$index" ]; then
                log "  Reindexing: $index"
                if psql "$db_url" -c "REINDEX INDEX CONCURRENTLY $index;" >> "$LOG_FILE" 2>&1; then
                    log_success "  Reindexed $index"
                else
                    log_warning "  Could not reindex $index (may require downtime)"
                fi
            fi
        done
    else
        log "No indexes need reindexing"
    fi
}

# Update table statistics
update_statistics() {
    local db_url=$1
    local db_name=$2
    
    log "Updating statistics for $db_name..."
    
    if psql "$db_url" -c "ANALYZE;" >> "$LOG_FILE" 2>&1; then
        log_success "Statistics updated for $db_name"
    else
        log_error "Failed to update statistics for $db_name"
    fi
}

# Clean up old monitoring data
cleanup_old_logs() {
    log "Cleaning up old maintenance logs..."
    
    # Remove logs older than 30 days
    find "$MAINTENANCE_DIR/logs" -name "*.log" -mtime +30 -delete
    find "$MAINTENANCE_DIR/reports" -name "*.html" -mtime +30 -delete
    
    log_success "Old logs cleaned up"
}

# Generate maintenance report
generate_report() {
    local db_url=$1
    local db_name=$2
    local report_content=$3
    
    log "Generating maintenance report for $db_name..."
    
    # Get current database stats
    local db_stats=$(psql "$db_url" -H -c "
        SELECT 
            'Database Size' as metric,
            pg_size_pretty(pg_database_size(current_database())) as value
        UNION ALL
        SELECT 
            'Total Tables',
            COUNT(*)::text
        FROM pg_tables WHERE schemaname = 'public'
        UNION ALL
        SELECT 
            'Total Indexes',
            COUNT(*)::text
        FROM pg_indexes WHERE schemaname = 'public'
        UNION ALL
        SELECT 
            'Cache Hit Ratio',
            ROUND(100.0 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read)), 2)::text || '%'
        FROM pg_stat_database WHERE datname = current_database()
        UNION ALL
        SELECT 
            'Dead Tuples',
            SUM(n_dead_tup)::text
        FROM pg_stat_user_tables;
    ")
    
    # Get maintenance needs
    local maintenance_needs=$(psql "$db_url" -H -c "
        SELECT 
            tablename as \"Table\",
            n_dead_tup as \"Dead Tuples\",
            last_vacuum as \"Last Vacuum\",
            last_autovacuum as \"Last Auto-vacuum\"
        FROM pg_stat_user_tables
        WHERE n_dead_tup > 1000
        ORDER BY n_dead_tup DESC
        LIMIT 10;
    ")
    
    # Append to report
    cat >> "$REPORT_FILE" << EOF
<h2>$db_name Database</h2>
<h3>Database Statistics</h3>
$db_stats

<h3>Tables Needing Maintenance</h3>
$maintenance_needs

<hr>
EOF
    
    log_success "Report section generated for $db_name"
}

# Check for long-running queries and alert
check_long_queries() {
    local db_url=$1
    local db_name=$2
    local threshold_minutes=30
    
    log "Checking for long-running queries in $db_name..."
    
    local long_queries=$(psql "$db_url" -t -c "
        SELECT COUNT(*)
        FROM pg_stat_activity
        WHERE state != 'idle'
          AND query NOT LIKE '%pg_stat_activity%'
          AND now() - query_start > interval '$threshold_minutes minutes';
    ")
    
    if [ "$long_queries" -gt 0 ]; then
        log_warning "Found $long_queries queries running longer than $threshold_minutes minutes in $db_name"
        
        # Log details of long queries
        psql "$db_url" -c "
            SELECT 
                pid,
                usename,
                EXTRACT(EPOCH FROM (now() - query_start))/60 as minutes,
                LEFT(query, 100) as query
            FROM pg_stat_activity
            WHERE state != 'idle'
              AND query NOT LIKE '%pg_stat_activity%'
              AND now() - query_start > interval '$threshold_minutes minutes';
        " >> "$LOG_FILE"
    else
        log_success "No long-running queries found"
    fi
}

# Main maintenance routine
main() {
    log "=== Starting database maintenance ==="
    log "Maintenance directory: $MAINTENANCE_DIR"
    
    # Initialize HTML report
    cat > "$REPORT_FILE" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Database Maintenance Report - $(date +%Y-%m-%d)</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        h1, h2, h3 { color: #333; }
        .success { color: green; }
        .warning { color: orange; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>Database Maintenance Report</h1>
    <p>Generated: $(date)</p>
    <p>Log file: $LOG_FILE</p>
EOF
    
    # Test connections
    local all_connected=true
    if ! test_connection "$DATABASE_URL" "business"; then
        all_connected=false
    fi
    if ! test_connection "$USER_DATABASE_URL" "users"; then
        all_connected=false
    fi
    
    if [ "$all_connected" = false ]; then
        log_error "Database connection test failed. Aborting maintenance."
        echo "<p class='error'>Database connection failed. Maintenance aborted.</p>" >> "$REPORT_FILE"
        echo "</body></html>" >> "$REPORT_FILE"
        exit 1
    fi
    
    # Perform maintenance on each database
    for db_config in "business|$DATABASE_URL" "users|$USER_DATABASE_URL"; do
        IFS='|' read -r db_name db_url <<< "$db_config"
        
        log ""
        log "=== Processing $db_name database ==="
        
        # Check long-running queries first
        check_long_queries "$db_url" "$db_name"
        
        # Run maintenance tasks
        run_vacuum "$db_url" "$db_name"
        update_statistics "$db_url" "$db_name"
        reindex_if_needed "$db_url" "$db_name"
        
        # Generate report section
        generate_report "$db_url" "$db_name"
    done
    
    # Clean up old logs
    cleanup_old_logs
    
    # Check overall database health
    log ""
    log "=== Checking overall database health ==="
    
    # Run the health check script
    if [ -f "$(dirname "$0")/health_check.py" ]; then
        python3 "$(dirname "$0")/health_check.py" --format json --output "$MAINTENANCE_DIR/reports/health_$(date +%Y%m%d).json"
        log_success "Health check completed"
    fi
    
    # Close HTML report
    cat >> "$REPORT_FILE" << EOF
    <h2>Maintenance Summary</h2>
    <p>Maintenance completed at: $(date)</p>
    <p>Check the log file for detailed information.</p>
</body>
</html>
EOF
    
    log ""
    log_success "=== Maintenance completed successfully ==="
    log "Report saved to: $REPORT_FILE"
    
    # Optional: Send report via email
    # if command -v mail >/dev/null 2>&1; then
    #     mail -s "Database Maintenance Report - $(date +%Y-%m-%d)" admin@example.com < "$REPORT_FILE"
    # fi
}

# Run main function
main