#!/bin/bash

# JPS Prospect Aggregate - Production Deployment Script
# This script helps deploy the application to production using Docker

set -e  # Exit on error

echo "================================================"
echo "JPS Prospect Aggregate - Production Deployment"
echo "================================================"

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo "❌ ERROR: .env.production file not found!"
    echo ""
    echo "Please create .env.production with the following required settings:"
    echo "  - SECRET_KEY (generate with: python -c \"import secrets; print(secrets.token_hex(32))\")"
    echo "  - ALLOWED_ORIGINS (your production domain)"
    echo "  - CLOUDFLARE_TUNNEL_TOKEN (from Cloudflare Zero Trust dashboard)"
    echo ""
    echo "You can copy from the template:"
    echo "  cp .env.example .env.production"
    echo ""
    exit 1
fi

# Check for required environment variables
source .env.production

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "CHANGE_THIS_TO_A_RANDOM_STRING" ]; then
    echo "❌ ERROR: SECRET_KEY not properly set in .env.production!"
    echo "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    exit 1
fi

# Check for production domain and construct derived variables
if [ -z "$PRODUCTION_DOMAIN" ]; then
    echo "❌ ERROR: PRODUCTION_DOMAIN not set in .env.production!"
    echo "Please set PRODUCTION_DOMAIN to your domain (e.g., example.com)"
    exit 1
fi

# Dynamically construct ALLOWED_ORIGINS and VITE_API_URL from PRODUCTION_DOMAIN
export ALLOWED_ORIGINS="https://${PRODUCTION_DOMAIN},http://localhost:5173,http://localhost:5001"
export VITE_API_URL="https://${PRODUCTION_DOMAIN}"

echo "✅ Using domain: ${PRODUCTION_DOMAIN}"
echo "✅ CORS configured for: ${ALLOWED_ORIGINS}"

# Option to use Cloudflare tunnel
USE_CLOUDFLARE=false
if [ ! -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
    echo ""
    echo "Cloudflare tunnel token detected."
    read -p "Deploy with Cloudflare tunnel? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        USE_CLOUDFLARE=true
    fi
fi

# Build the Docker images
echo ""
echo "Building Docker images..."
docker-compose --env-file .env.production build

# Stop any existing containers
echo ""
echo "Stopping existing containers (if any)..."
docker-compose down

# Start the application
echo ""
if [ "$USE_CLOUDFLARE" = true ]; then
    echo "Starting application with Cloudflare tunnel..."
    docker-compose --env-file .env.production --profile cloudflare up -d
else
    echo "Starting application without Cloudflare tunnel..."
    docker-compose --env-file .env.production up -d
fi

# Wait for services to be ready
echo ""
echo "Waiting for services to start..."
sleep 10

# Check health endpoint
echo ""
echo "Checking application health..."
if curl -f http://localhost:5001/health > /dev/null 2>&1; then
    echo "✅ Application is healthy!"
else
    echo "⚠️  Health check failed. Checking logs..."
    docker-compose logs --tail=50 web
fi

# Display status
echo ""
echo "================================================"
echo "Deployment Status:"
echo "================================================"
docker-compose ps

echo ""
echo "================================================"
echo "Next Steps:"
echo "================================================"
if [ "$USE_CLOUDFLARE" = true ]; then
    echo "1. Your application should be accessible via your Cloudflare tunnel"
    echo "2. Check your domain to verify it's working"
else
    echo "1. Application is running on http://localhost:5001"
    echo "2. Configure your reverse proxy (nginx/Apache) to point to this port"
    echo "3. Set up SSL certificates (Let's Encrypt recommended)"
fi
echo ""
echo "Useful commands:"
echo "  View logs:        docker-compose logs -f web"
echo "  Stop application: docker-compose down"
echo "  Restart:          docker-compose restart"
echo "  Database backup:  docker exec jps-web sqlite3 /app/data/jps_aggregate.db '.backup /app/backups/backup.db'"
echo ""
echo "================================================"