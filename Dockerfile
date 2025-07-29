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
    # Run migrations with better error handling\n\
    if flask db upgrade; then\n\
        log "Database migrations completed successfully"\n\
    else\n\
        log "ERROR: Database migrations failed"\n\
        log "Checking migration status..."\n\
        flask db current || true\n\
        log "Checking migration heads..."\n\
        flask db heads || true\n\
        exit 1\n\
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