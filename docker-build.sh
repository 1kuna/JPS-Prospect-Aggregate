#!/bin/bash
set -e

# JPS Prospect Aggregate - Docker Build Script
# This script builds and deploys the complete application stack

echo "🚀 JPS Prospect Aggregate Docker Build & Deploy"
echo "=============================================="

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "❌ Error: .env.production file not found!"
    echo "   Please copy .env.production.example to .env.production and configure:"
    echo "   cp .env.production.example .env.production"
    echo "   Then edit .env.production with your database password and secret key."
    exit 1
fi

# Verify required environment variables are set
echo "📋 Checking configuration..."
if ! grep -q "^DB_PASSWORD=" .env.production || grep -q "CHANGE_THIS_STRONG_PASSWORD" .env.production; then
    echo "❌ Error: DB_PASSWORD not configured in .env.production"
    exit 1
fi

if ! grep -q "^SECRET_KEY=" .env.production || grep -q "CHANGE_THIS_RANDOM_SECRET_KEY" .env.production; then
    echo "❌ Error: SECRET_KEY not configured in .env.production"
    exit 1
fi

echo "✅ Configuration looks good!"

# Create required directories
echo "📁 Creating required directories..."
mkdir -p data logs backups

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose --env-file .env.production down || true

# Build and start services
echo "🔨 Building and starting services..."
docker-compose --env-file .env.production up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Service Status:"
docker-compose --env-file .env.production ps

# Check if web service is healthy
if docker-compose --env-file .env.production ps | grep -q "jps-web.*Up"; then
    echo "✅ Web service is running!"
    echo "🌐 Application available at: http://localhost:5001"
else
    echo "❌ Web service failed to start. Checking logs..."
    docker-compose --env-file .env.production logs web
    exit 1
fi

# Check database
if docker-compose --env-file .env.production ps | grep -q "jps-db.*Up"; then
    echo "✅ Database service is running!"
else
    echo "❌ Database service failed to start. Checking logs..."
    docker-compose --env-file .env.production logs db
    exit 1
fi

# Check Ollama (may still be downloading model)
if docker-compose --env-file .env.production ps | grep -q "jps-ollama.*Up"; then
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
echo "   View logs:           docker-compose --env-file .env.production logs -f web"
echo "   Stop services:       docker-compose --env-file .env.production down"
echo "   Restart web:         docker-compose --env-file .env.production restart web"
echo "   Access database:     docker exec -it jps-db psql -U jps_user -d jps_prospects"
echo ""
echo "🌐 Access your application at: http://localhost:5001"