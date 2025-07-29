# Multi-stage build for smaller image
FROM node:18-slim as frontend-builder

# Build React frontend
WORKDIR /app/frontend-react
COPY frontend-react/package*.json ./
RUN npm ci

COPY frontend-react/ ./

# Ensure src/lib directory exists and has utils.ts
RUN mkdir -p src/lib && \
    if [ ! -f src/lib/utils.ts ]; then \
        echo "Creating missing utils.ts file" && \
        printf 'import { clsx, type ClassValue } from "clsx"\nimport { twMerge } from "tailwind-merge"\n\nexport function cn(...inputs: ClassValue[]) {\n  return twMerge(clsx(inputs));\n}\n' > src/lib/utils.ts; \
    fi

RUN npm run build

# Python dependencies builder
FROM python:3.11-slim as python-builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

# Install runtime dependencies including Node.js for any runtime needs
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    netcat-traditional \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxss1 \
    libgtk-3-0 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=python-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
WORKDIR /app
COPY . .

# Copy built frontend from frontend builder
COPY --from=frontend-builder /app/frontend-react/dist ./frontend-react/dist

# Create entrypoint script inline to avoid copy issues
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "=== JPS Prospect Aggregate Docker Entrypoint ==="\n\
echo "Starting JPS Prospect Aggregate application..."\n\
\n\
# Function to log with timestamp\n\
log() {\n\
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] $1"\n\
}\n\
\n\
# Function to wait for database\n\
wait_for_db() {\n\
    log "Waiting for database to be ready..."\n\
    local max_attempts=30\n\
    local attempt=1\n\
    \n\
    while ! nc -z db 5432; do\n\
        if [ $attempt -eq $max_attempts ]; then\n\
            log "ERROR: Database not ready after $max_attempts attempts"\n\
            exit 1\n\
        fi\n\
        log "Database not ready, attempt $attempt/$max_attempts"\n\
        sleep 2\n\
        attempt=$((attempt + 1))\n\
    done\n\
    \n\
    log "Database connection successful!"\n\
}\n\
\n\
# Function to check if migrations are stuck\n\
check_migration_state() {\n\
    log "Checking current migration state..."\n\
    \n\
    # Try to get current revision, handle failures gracefully\n\
    if CURRENT_REV=$(flask db current 2>/dev/null | head -1); then\n\
        if [ -z "$CURRENT_REV" ]; then\n\
            CURRENT_REV="none (empty)"\n\
        fi\n\
    else\n\
        log "flask db current failed, database may not be initialized"\n\
        CURRENT_REV="error (database not initialized)"\n\
    fi\n\
    \n\
    log "Current revision: $CURRENT_REV"\n\
    \n\
    # Check if we have a partial migration state\n\
    if echo "$CURRENT_REV" | grep -q "fbc0e1fbf50d"; then\n\
        log "WARNING: Found partially applied migration fbc0e1fbf50d"\n\
        log "This migration has been updated to handle existing columns safely"\n\
    elif echo "$CURRENT_REV" | grep -q "error"; then\n\
        log "Migration state check failed - will attempt to initialize from scratch"\n\
    fi\n\
}\n\
\n\
# Function to run migrations\n\
run_migrations() {\n\
    log "Running database migrations..."\n\
    \n\
    cd /app\n\
    \n\
    # Set environment variables for Flask\n\
    export FLASK_APP=run.py\n\
    export FLASK_ENV=production\n\
    \n\
    # Check current state first\n\
    check_migration_state\n\
    \n\
    # Run migrations with better error handling\n\
    MIGRATION_OUTPUT=$(flask db upgrade 2>&1)\n\
    MIGRATION_EXIT_CODE=$?\n\
    \n\
    if [ $MIGRATION_EXIT_CODE -eq 0 ]; then\n\
        log "Database migrations completed successfully"\n\
        return 0\n\
    else\n\
        log "ERROR: Database migrations failed with exit code $MIGRATION_EXIT_CODE"\n\
        echo "$MIGRATION_OUTPUT" | grep -A5 -B5 "ERROR\\|CRITICAL\\|Traceback"\n\
        \n\
        # Check for specific errors\n\
        if echo "$MIGRATION_OUTPUT" | grep -q "DuplicateColumn"; then\n\
            log "NOTICE: Duplicate column error detected - this is expected if the database already has the columns"\n\
            log "The migration has been updated to handle this gracefully"\n\
            log "Attempting to mark migration as completed..."\n\
            \n\
            # Check which column is causing the issue\n\
            if echo "$MIGRATION_OUTPUT" | grep -q "ai_enhanced_title"; then\n\
                log "ai_enhanced_title column already exists, stamping migration 5fb5cc7eff5b"\n\
                flask db stamp 5fb5cc7eff5b 2>/dev/null || true\n\
            elif echo "$MIGRATION_OUTPUT" | grep -q "estimated_value_text"; then\n\
                log "estimated_value_text column already exists, stamping migration fbc0e1fbf50d"\n\
                flask db stamp fbc0e1fbf50d 2>/dev/null || true\n\
            fi\n\
            \n\
            # Try to continue with remaining migrations\n\
            if flask db upgrade; then\n\
                log "Successfully continued with remaining migrations"\n\
                return 0\n\
            fi\n\
        fi\n\
        \n\
        log "Checking final migration status..."\n\
        flask db current || true\n\
        log "Checking migration heads..."\n\
        flask db heads || true\n\
        \n\
        # Try to create the alembic_version table if it doesnt exist\n\
        log "Attempting to create alembic_version table..."\n\
        python -c "\n\
import os\n\
os.environ['"'"'FLASK_APP'"'"'] = '"'"'run.py'"'"'\n\
from app import create_app, db\n\
from sqlalchemy import text\n\
app = create_app()\n\
with app.app_context():\n\
    try:\n\
        db.engine.execute(text('"'"'CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))'"'"'))\n\
        print('"'"'alembic_version table created or already exists'"'"')\n\
    except Exception as e:\n\
        print(f'"'"'Error creating alembic_version table: {e}'"'"')\n\
" 2>/dev/null || true\n\
        \n\
        # For now, continue running the app even if migrations fail\n\
        # This allows the app to start with existing database schema\n\
        log "WARNING: Continuing despite migration errors - will try to run app anyway"\n\
        return 0\n\
    fi\n\
}\n\
\n\
# Main execution\n\
log "Environment: ${FLASK_ENV:-production}"\n\
log "Database URL configured: $(echo $DATABASE_URL | cut -d@ -f2 || echo not set)"\n\
\n\
wait_for_db\n\
run_migrations\n\
\n\
log "Starting application with command: $@"\n\
exec "$@"' > /entrypoint.sh && chmod +x /entrypoint.sh

# Install Playwright browsers
RUN playwright install chromium

# Create directories for logs and data
RUN mkdir -p logs logs/error_screenshots logs/error_html data

# Expose port 5001 (standardized)
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Use entrypoint script for database migrations
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "run.py"]