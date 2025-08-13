#!/bin/bash

# JPS Prospect Aggregate - Production Setup Helper
# This script helps set up the production environment

set -e  # Exit on error

echo "================================================"
echo "JPS Prospect Aggregate - Production Setup"
echo "================================================"
echo ""

# Check if .env.production already exists
if [ -f .env.production ]; then
    echo "⚠️  .env.production already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Generate SECRET_KEY
echo "Generating secure SECRET_KEY..."
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
echo "✅ SECRET_KEY generated"

# Get production domain
echo ""
read -p "Enter your production domain (e.g., app.example.com): " DOMAIN
if [ -z "$DOMAIN" ]; then
    echo "❌ Domain is required!"
    exit 1
fi

# Get Cloudflare tunnel token (optional)
echo ""
echo "Cloudflare tunnel setup (optional - press Enter to skip)"
echo "Get your token from: Cloudflare Dashboard → Zero Trust → Tunnels"
read -p "Enter Cloudflare tunnel token: " CLOUDFLARE_TOKEN

# Create .env.production
echo ""
echo "Creating .env.production file..."
cat > .env.production << EOF
# JPS Prospect Aggregate - Production Environment Configuration
# Generated on $(date)

# ==============================
# DOMAIN CONFIGURATION - CHANGE THIS ONLY!
# ==============================
# Set your production domain here (without https://)
# This will be used to automatically configure CORS and API URLs
PRODUCTION_DOMAIN=${DOMAIN}

# ==============================
# Core Settings
# ==============================
ENVIRONMENT=production
SECRET_KEY=${SECRET_KEY}
DEBUG=False
FLASK_ENV=production
LOG_LEVEL=INFO

# ==============================
# Security Settings
# ==============================
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=3600

# ==============================
# CORS Configuration
# ==============================
# ALLOWED_ORIGINS is automatically constructed from PRODUCTION_DOMAIN
# It will include: https://\${PRODUCTION_DOMAIN} plus localhost origins for development

# ==============================
# Database Configuration
# ==============================
DATABASE_URL=sqlite:///data/jps_aggregate.db
USER_DATABASE_URL=sqlite:///data/jps_users.db

# SQLite optimization for production
SQLITE_JOURNAL_MODE=WAL
SQLITE_SYNCHRONOUS=NORMAL
SQLITE_CACHE_SIZE=-64000

# ==============================
# External Services
# ==============================
# Ollama configuration (Docker internal network)
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen3:latest

# ==============================
# Cloudflare Tunnel
# ==============================
CLOUDFLARE_TUNNEL_TOKEN=${CLOUDFLARE_TOKEN}

# ==============================
# Application Settings
# ==============================
HOST=0.0.0.0
PORT=5001
FLASK_APP=run.py

# File processing
FILE_FRESHNESS_SECONDS=86400

# Feature flags
ENABLE_LLM_ENHANCEMENT=True
ENABLE_DUPLICATE_DETECTION=True
ENABLE_AUTO_ARCHIVAL=True

# ==============================
# Scraper Configuration
# ==============================
# Playwright timeouts (milliseconds)
PAGE_NAVIGATION_TIMEOUT=60000
PAGE_ELEMENT_TIMEOUT=30000
TABLE_LOAD_TIMEOUT=60000
DOWNLOAD_TIMEOUT=60000
PLAYWRIGHT_TIMEOUT=60000

# Scraper behavior
SCRAPER_TIMEOUT=120
SCRAPER_RETRY_ATTEMPTS=3
SCRAPE_INTERVAL_HOURS=24
HEALTH_CHECK_INTERVAL_MINUTES=10
SCRAPER_TIMEOUT_HOURS=2
SCRAPER_CLEANUP_ENABLED=true

# ==============================
# Performance Settings
# ==============================
SQLALCHEMY_POOL_SIZE=10
SQLALCHEMY_POOL_RECYCLE=3600
SQLALCHEMY_MAX_OVERFLOW=20

# Production server settings
WORKERS=12
TIMEOUT=120

# ==============================
# File Upload Settings
# ==============================
MAX_CONTENT_LENGTH=104857600
UPLOAD_FOLDER=/app/uploads

# ==============================
# Logging Configuration
# ==============================
LOG_FILE_MAX_BYTES=5242880
LOG_FILE_BACKUP_COUNT=3
LOG_FILE=/app/logs/app.log

# ==============================
# Backup Settings
# ==============================
BACKUP_RETENTION_DAYS=7
BACKUP_DIRECTORY=/app/backups

# ==============================
# AI Data Preservation
# ==============================
PRESERVE_AI_DATA_ON_REFRESH=true
ENABLE_SMART_DUPLICATE_MATCHING=true

# Duplicate matching thresholds
DUPLICATE_MIN_CONFIDENCE=0.80
DUPLICATE_NATIVE_ID_MIN_CONTENT_SIM=0.30
DUPLICATE_TITLE_SIMILARITY_THRESHOLD=0.70
DUPLICATE_FUZZY_CONTENT_THRESHOLD=0.90

# ==============================
# Frontend Settings
# ==============================
# VITE_API_URL is automatically constructed from PRODUCTION_DOMAIN
REACT_DEV_MODE=False
REACT_FORCE_REBUILD=False
EOF

echo "✅ .env.production created successfully!"

# Create necessary directories
echo ""
echo "Creating required directories..."
mkdir -p data logs backups
echo "✅ Directories created"

# Show summary
echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Configuration Summary:"
echo "  Domain: https://${DOMAIN}"
echo "  SECRET_KEY: [Generated - 64 characters]"
if [ ! -z "$CLOUDFLARE_TOKEN" ]; then
    echo "  Cloudflare: Configured"
else
    echo "  Cloudflare: Not configured (can add later)"
fi
echo ""
echo "Next steps:"
echo "  1. Review .env.production and adjust any settings if needed"
echo "  2. Run ./deploy-production.sh to deploy the application"
echo ""
echo "================================================"