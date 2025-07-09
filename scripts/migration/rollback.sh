#!/bin/bash
# Emergency rollback to SQLite databases
# This script quickly restores SQLite databases in case of critical issues

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/opt/jps/backups}"

# Fallback for development
if [ ! -d "$BACKUP_DIR" ]; then
    BACKUP_DIR="$PROJECT_ROOT/backups"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment if available
if [ -f "/opt/jps/.env.production" ]; then
    source /opt/jps/.env.production
elif [ -f "$PROJECT_ROOT/.env.production" ]; then
    source "$PROJECT_ROOT/.env.production"
fi

# Logging
ROLLBACK_LOG="$BACKUP_DIR/logs/rollback_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$BACKUP_DIR/logs"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$ROLLBACK_LOG"
}

# Display banner
clear
echo -e "${RED}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              EMERGENCY DATABASE ROLLBACK                  ║"
echo "║                                                          ║"
echo "║  WARNING: This will rollback to SQLite databases!       ║"
echo "║  All PostgreSQL data will be preserved but not used.    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Check if running as appropriate user
if [ "$EUID" -eq 0 ] && [ -z "$ALLOW_ROOT" ]; then 
   echo -e "${RED}ERROR: Do not run as root unless necessary${NC}"
   echo "If you must run as root, set ALLOW_ROOT=1"
   exit 1
fi

# Confirm rollback
echo -e "${YELLOW}This action will:${NC}"
echo "  1. Stop the application"
echo "  2. Create PostgreSQL backups (for safety)"
echo "  3. Restore SQLite databases from backup"
echo "  4. Update configuration to use SQLite"
echo "  5. Restart the application"
echo ""
echo -e "${RED}Type 'ROLLBACK' to confirm:${NC} "
read -r confirm

if [ "$confirm" != "ROLLBACK" ]; then
    echo -e "${YELLOW}Rollback cancelled${NC}"
    exit 0
fi

log "=== Starting emergency rollback ==="

# Step 1: Stop application
echo -e "\n${BLUE}Step 1: Stopping application...${NC}"
log "Stopping application services"

if command -v systemctl &> /dev/null; then
    sudo systemctl stop jps-aggregate 2>/dev/null || log "Note: systemctl stop failed"
else
    # Try to find and kill the process
    pkill -f "python.*run.py" || log "Note: No running application found"
fi

# Give processes time to stop
sleep 3

# Step 2: Create PostgreSQL backups (non-blocking)
echo -e "\n${BLUE}Step 2: Creating PostgreSQL backups...${NC}"
log "Creating PostgreSQL backups for safety"

POSTGRES_BACKUP_DIR="$BACKUP_DIR/rollback/postgres_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$POSTGRES_BACKUP_DIR"

# Backup in background to speed up rollback
(
    if [ -n "$DATABASE_URL" ]; then
        pg_dump "$DATABASE_URL" | gzip > "$POSTGRES_BACKUP_DIR/jps_aggregate.sql.gz" 2>/dev/null &&
        log "PostgreSQL business database backed up"
    fi
    
    if [ -n "$USER_DATABASE_URL" ]; then
        pg_dump "$USER_DATABASE_URL" | gzip > "$POSTGRES_BACKUP_DIR/jps_users.sql.gz" 2>/dev/null &&
        log "PostgreSQL user database backed up"
    fi
) &

BACKUP_PID=$!

# Step 3: Find latest SQLite backups
echo -e "\n${BLUE}Step 3: Finding SQLite backups...${NC}"
log "Searching for SQLite backups"

# Look in multiple locations
SQLITE_SEARCH_PATHS=(
    "$BACKUP_DIR/migration"
    "$PROJECT_ROOT/backups/migration"
    "$PROJECT_ROOT/data"
    "/opt/jps/backups/migration"
)

LATEST_BUSINESS_BACKUP=""
LATEST_USER_BACKUP=""

for search_path in "${SQLITE_SEARCH_PATHS[@]}"; do
    if [ -d "$search_path" ]; then
        # Find business database backup
        if [ -z "$LATEST_BUSINESS_BACKUP" ]; then
            LATEST_BUSINESS_BACKUP=$(ls -t "$search_path"/jps_aggregate*.db 2>/dev/null | grep -v ".db-" | head -1)
        fi
        
        # Find user database backup
        if [ -z "$LATEST_USER_BACKUP" ]; then
            LATEST_USER_BACKUP=$(ls -t "$search_path"/jps_users*.db 2>/dev/null | grep -v ".db-" | head -1)
        fi
    fi
done

# Verify backups found
if [ -z "$LATEST_BUSINESS_BACKUP" ] || [ -z "$LATEST_USER_BACKUP" ]; then
    echo -e "${RED}ERROR: SQLite backups not found!${NC}"
    log "ERROR: Could not find SQLite backups"
    echo ""
    echo "Searched in:"
    for path in "${SQLITE_SEARCH_PATHS[@]}"; do
        echo "  - $path"
    done
    
    # Wait for PostgreSQL backup to complete
    wait $BACKUP_PID
    
    echo ""
    echo -e "${YELLOW}PostgreSQL data has been preserved in: $POSTGRES_BACKUP_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}Found backups:${NC}"
echo "  Business: $LATEST_BUSINESS_BACKUP"
echo "  Users: $LATEST_USER_BACKUP"
log "Found business backup: $LATEST_BUSINESS_BACKUP"
log "Found user backup: $LATEST_USER_BACKUP"

# Step 4: Restore SQLite databases
echo -e "\n${BLUE}Step 4: Restoring SQLite databases...${NC}"
log "Restoring SQLite databases"

cd "$PROJECT_ROOT"

# Create data directory if it doesn't exist
mkdir -p data

# Backup current SQLite files if they exist
if [ -f "data/jps_aggregate.db" ]; then
    mv "data/jps_aggregate.db" "data/jps_aggregate.db.pre_rollback_$(date +%Y%m%d_%H%M%S)"
fi

if [ -f "data/jps_users.db" ]; then
    mv "data/jps_users.db" "data/jps_users.db.pre_rollback_$(date +%Y%m%d_%H%M%S)"
fi

# Copy backups
cp "$LATEST_BUSINESS_BACKUP" data/jps_aggregate.db
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Business database restored${NC}"
    log "Business database restored successfully"
else
    echo -e "${RED}✗ Failed to restore business database${NC}"
    log "ERROR: Failed to restore business database"
    exit 1
fi

cp "$LATEST_USER_BACKUP" data/jps_users.db
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ User database restored${NC}"
    log "User database restored successfully"
else
    echo -e "${RED}✗ Failed to restore user database${NC}"
    log "ERROR: Failed to restore user database"
    exit 1
fi

# Set proper permissions
chmod 644 data/*.db

# Step 5: Update configuration
echo -e "\n${BLUE}Step 5: Updating configuration...${NC}"
log "Updating configuration to use SQLite"

# Create SQLite configuration
cat > .env.sqlite << 'EOF'
# SQLite Database Configuration (Rollback)
DATABASE_URL=sqlite:///data/jps_aggregate.db
USER_DATABASE_URL=sqlite:///data/jps_users.db

# Copy other settings from production
EOF

# Append non-database settings from production env
if [ -f ".env.production" ]; then
    grep -v "DATABASE_URL\|POSTGRES_" .env.production >> .env.sqlite
fi

# Backup current .env and switch to SQLite
if [ -f ".env" ]; then
    cp .env .env.postgresql_backup
fi
cp .env.sqlite .env

echo -e "${GREEN}✓ Configuration updated${NC}"
log "Configuration switched to SQLite"

# Step 6: Update Alembic configuration
echo -e "\n${BLUE}Step 6: Updating Alembic configuration...${NC}"
if [ -f "alembic.ini" ]; then
    sed -i.backup 's|postgresql://.*|sqlite:///data/jps_aggregate.db|g' alembic.ini
    echo -e "${GREEN}✓ Alembic configuration updated${NC}"
    log "Alembic configuration updated for SQLite"
fi

# Step 7: Restart application
echo -e "\n${BLUE}Step 7: Starting application...${NC}"
log "Starting application with SQLite"

if command -v systemctl &> /dev/null; then
    sudo systemctl start jps-aggregate
    sleep 3
    
    if systemctl is-active --quiet jps-aggregate; then
        echo -e "${GREEN}✓ Application started successfully${NC}"
        log "Application started via systemctl"
    else
        echo -e "${YELLOW}⚠ Application did not start via systemctl${NC}"
        echo "Trying direct start..."
        
        cd "$PROJECT_ROOT"
        nohup python run.py > logs/app.log 2>&1 &
        echo $! > jps.pid
        
        sleep 3
        if ps -p $(cat jps.pid) > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Application started directly${NC}"
            log "Application started directly"
        else
            echo -e "${RED}✗ Failed to start application${NC}"
            log "ERROR: Failed to start application"
        fi
    fi
else
    # Direct start
    cd "$PROJECT_ROOT"
    nohup python run.py > logs/app.log 2>&1 &
    echo $! > jps.pid
    
    sleep 3
    if ps -p $(cat jps.pid) > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Application started${NC}"
        log "Application started directly"
    else
        echo -e "${RED}✗ Failed to start application${NC}"
        log "ERROR: Failed to start application"
    fi
fi

# Wait for PostgreSQL backup to complete
echo -e "\n${BLUE}Waiting for PostgreSQL backup to complete...${NC}"
wait $BACKUP_PID
echo -e "${GREEN}✓ PostgreSQL backup completed${NC}"

# Summary
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}         ROLLBACK COMPLETED SUCCESSFULLY${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "Summary:"
echo "  • Application: Running with SQLite"
echo "  • Business DB: $(du -h data/jps_aggregate.db | cut -f1)"
echo "  • User DB: $(du -h data/jps_users.db | cut -f1)"
echo "  • PostgreSQL backups: $POSTGRES_BACKUP_DIR"
echo "  • Rollback log: $ROLLBACK_LOG"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Verify application functionality"
echo "  2. Check logs: tail -f logs/app.log"
echo "  3. Investigate PostgreSQL issues"
echo "  4. Plan retry of PostgreSQL migration"
echo ""

log "=== Rollback completed successfully ==="

# Create rollback marker file
echo "Rolled back at: $(date)" > .rollback_marker
echo "From PostgreSQL to SQLite" >> .rollback_marker
echo "Log: $ROLLBACK_LOG" >> .rollback_marker

exit 0