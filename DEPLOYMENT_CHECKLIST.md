# Production Deployment Checklist

## ✅ Completed Tasks

### Security Configuration
- [x] Generated secure 64-character SECRET_KEY
- [x] Created `.env.production` with production settings
- [x] Updated `app/config.py` to enforce SECRET_KEY in production
- [x] Enabled HTTPS security settings (SESSION_COOKIE_SECURE, etc.)

### CORS & API Configuration
- [x] Made CORS origins configurable via `ALLOWED_ORIGINS` environment variable
- [x] Updated `app/__init__.py` to read CORS from environment
- [x] Frontend uses relative `/api/` paths (no hardcoded URLs)
- [x] Updated `vite.config.ts` to only use proxy in development

### External Services
- [x] Configured Ollama with fallback behavior (won't crash if unavailable)
- [x] Added graceful error handling for LLM service failures

### Docker & Deployment
- [x] Created `.env.production` with all necessary configurations
- [x] Playwright browsers installed in Docker image
- [x] Created `setup-production.sh` helper script
- [x] Created `deploy-production.sh` deployment script
- [x] Tested frontend production build successfully

## 📋 Ready for Deployment - Next Steps

### 1. Configure Your Domain
Edit `.env.production` and set your domain in ONE place:
```bash
PRODUCTION_DOMAIN=your-actual-domain.com
```
That's it! CORS and API URLs are automatically configured from this single setting.

### 2. Set Up Cloudflare Tunnel (if using)
1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Create a new tunnel
3. Get the tunnel token
4. Add it to `.env.production`: `CLOUDFLARE_TUNNEL_TOKEN=your-token-here`

### 3. Deploy the Application
```bash
# Option 1: Use the setup helper (if starting fresh)
./setup-production.sh

# Option 2: Deploy with existing config
./deploy-production.sh
```

### 4. Verify Deployment
- Check health endpoint: `curl http://localhost:5001/health`
- View logs: `docker-compose logs -f web`
- Access via browser at your configured domain

## 🔧 Quick Commands

### Start/Stop
```bash
# Start
docker-compose --env-file .env.production up -d

# Stop
docker-compose down

# Restart
docker-compose restart
```

### Monitoring
```bash
# View logs
docker-compose logs -f web

# Check status
docker-compose ps

# Database backup
docker exec jps-web sqlite3 /app/data/jps_aggregate.db '.backup /app/backups/backup.db'
```

### Troubleshooting
```bash
# If port 5001 is in use
lsof -i :5001 && kill -9 <PID>

# If Ollama isn't working
docker-compose logs ollama

# Rebuild after changes
docker-compose --env-file .env.production build --no-cache
```

## ⚠️ Important Notes

1. **SECRET_KEY**: Never commit `.env.production` to version control
2. **Domain**: Just set `PRODUCTION_DOMAIN` once - everything else is automatic!
3. **HTTPS**: The application expects HTTPS in production (SESSION_COOKIE_SECURE=True)
4. **Cloudflare**: Optional but recommended for easy HTTPS and tunneling
5. **Ollama**: LLM enhancement will gracefully degrade if Ollama is unavailable

## 🚀 You're Ready to Deploy!

All critical production configurations have been completed. The application is:
- Secure (proper SECRET_KEY, HTTPS cookies, CORS configured)
- Flexible (configurable via environment variables)
- Robust (graceful fallbacks for external services)
- Production-ready (Docker containerized, health checks, logging)

Just update your domain in `.env.production` and run `./deploy-production.sh`!