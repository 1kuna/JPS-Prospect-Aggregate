#!/bin/bash
set -e

# JPS Prospect Aggregate - Docker Build Script
# This script builds and deploys the complete application stack

echo "🚀 JPS Prospect Aggregate Docker Build & Deploy"
echo "=============================================="

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "   Please copy .env.example to .env and configure:"
    echo "   cp .env.example .env"
    echo "   Then edit .env with your settings (set ENVIRONMENT=production, DB_PASSWORD, SECRET_KEY)."
    exit 1
fi

# Verify required environment variables are set
echo "📋 Checking configuration..."
if ! grep -q "^DB_PASSWORD=" .env || grep -q "CHANGE_THIS_STRONG_PASSWORD" .env; then
    echo "❌ Error: DB_PASSWORD not configured in .env"
    exit 1
fi

if ! grep -q "^SECRET_KEY=" .env || grep -q "CHANGE_THIS_TO_A_RANDOM_STRING" .env; then
    echo "❌ Error: SECRET_KEY not configured in .env"
    exit 1
fi

# Check if ENVIRONMENT is set to production
if ! grep -q "^ENVIRONMENT=production" .env; then
    echo "❌ Error: ENVIRONMENT must be set to 'production' in .env for Docker deployment"
    exit 1
fi

echo "✅ Configuration looks good!"

# Create required directories
echo "📁 Creating required directories..."
mkdir -p data logs backups

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down || true

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Service Status:"
docker-compose ps

# Check if web service is healthy
if docker-compose ps | grep -q "jps-web.*Up"; then
    echo "✅ Web service is running!"
    echo "🌐 Application available at: http://localhost:5001"
else
    echo "❌ Web service failed to start. Checking logs..."
    docker-compose logs web
    exit 1
fi

# Check database
if docker-compose ps | grep -q "jps-db.*Up"; then
    echo "✅ Database service is running!"
else
    echo "❌ Database service failed to start. Checking logs..."
    docker-compose logs db
    exit 1
fi

# Check Ollama (may still be downloading model)
if docker-compose ps | grep -q "jps-ollama.*Up"; then
    echo "✅ Ollama service is running!"
    echo "🤖 LLM API available at: http://localhost:11434"
    echo "   (Note: qwen3 model may still be downloading in background)"
else
    echo "⚠️  Ollama service status unknown. Check with: docker-compose logs ollama"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📝 Quick commands:"
echo "   View logs:           docker-compose logs -f web"
echo "   Stop services:       docker-compose down"
echo "   Restart web:         docker-compose restart web"
echo "   Access database:     docker exec -it jps-db psql -U jps_user -d jps_prospects"
echo ""
echo "🌐 Access your application at: http://localhost:5001"