# Production Deployment Plan for JPS Prospect Aggregate

## Current State Analysis

### Issues Preventing Immediate Production Deployment

#### Critical Issues
1. **Hardcoded localhost references**
   - Frontend has hardcoded API proxies pointing to `localhost:5001` in `vite.config.ts`
   - CORS configuration only allows localhost origins in `app/__init__.py`
   - Ollama service expects `localhost:11434` connection

2. **Security concerns**
   - Using a default/development `SECRET_KEY` in config
   - `SESSION_COOKIE_SECURE` is False by default - needs HTTPS in production
   - Debug mode enabled by default
   - SQLite databases stored locally without access control

3. **Frontend API calls**
   - React app makes relative `/api` calls which work in dev but need configuration for production
   - No environment-based API URL configuration

4. **Browser automation dependencies**
   - Playwright requires browser binaries installed on host
   - Scrapers download files to local filesystem
   - May not work properly in containerized/tunnel environment

5. **File storage**
   - Local file system dependencies for data storage
   - Logs, screenshots, and downloaded files stored locally
   - No cloud storage integration

### Existing Positives
- Docker setup already includes Cloudflare tunnel support
- Uses Waitress WSGI server (production-ready)
- Environment variable configuration mostly in place
- Frontend build process configured

## Deployment Plan

### Phase 1: Security & Configuration (Priority 1 - CRITICAL)

#### 1.1 Update SECRET_KEY Handling
- [x] Generate strong production SECRET_KEY using: `python -c "import secrets; print(secrets.token_hex(32))"`
- [x] Store in `.env.production` file
- [x] Update `app/config.py` to require SECRET_KEY from environment in production mode
- [x] Never commit production SECRET_KEY to repository

#### 1.2 Fix CORS Configuration
- [x] Add `ALLOWED_ORIGINS` environment variable
- [x] Update `app/__init__.py` to read allowed origins from environment
- [x] Include your production domain (e.g., `https://your-domain.com`) in CORS whitelist
- [x] Keep localhost origins for development only

#### 1.3 Enable HTTPS Security
- [x] Set `SESSION_COOKIE_SECURE=True` for production in `.env.production`
- [x] Set `SESSION_COOKIE_HTTPONLY=True`
- [x] Set `SESSION_COOKIE_SAMESITE=Lax` or `Strict`
- [x] Configure `PERMANENT_SESSION_LIFETIME` appropriately

### Phase 2: Frontend API Configuration (Priority 2 - IMPORTANT)

#### 2.1 Create Dynamic API Configuration
- [x] Add `VITE_API_URL` environment variable for frontend builds
- [x] Update `frontend-react/src/utils/apiUtils.ts` to use environment variable (already uses relative paths)
- [x] Create production build configuration
- [x] Remove hardcoded localhost references

#### 2.2 Update Proxy Settings
- [x] Remove hardcoded proxy from `vite.config.ts` for production builds
- [x] Configure nginx or similar for reverse proxy in production (Flask serves frontend)
- [x] Ensure API calls work through Cloudflare tunnel

### Phase 3: External Services (Priority 3 - MODERATE)

#### 3.1 Configure Ollama Endpoint
- [x] Make `OLLAMA_BASE_URL` fully configurable via environment
- [x] Add fallback behavior when Ollama is unavailable
- [ ] Consider using cloud LLM service (OpenAI, Anthropic) as alternative
- [x] Add error handling for LLM service failures

#### 3.2 Handle Browser Automation
- [x] Ensure Playwright browsers are installed in Docker image
- [x] Add comprehensive error handling for scraper failures
- [ ] Consider running scrapers on schedule rather than on-demand
- [ ] Add option to disable scrapers via environment variable

### Phase 4: Docker & Deployment (Priority 4 - DEPLOYMENT)

#### 4.1 Update Docker Configuration
- [ ] Set up Cloudflare tunnel in Zero Trust dashboard
- [ ] Get tunnel token and add to `.env.production` as `CLOUDFLARE_TUNNEL_TOKEN`
- [ ] Test docker-compose with cloudflare profile: `docker-compose --profile cloudflare up`
- [ ] Verify health checks work through tunnel

#### 4.2 Environment Variables Setup
Create `.env.production` with:
```bash
# Core Settings
ENVIRONMENT=production
SECRET_KEY=<generated-secret-key>
DEBUG=False
FLASK_ENV=production
LOG_LEVEL=INFO

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# CORS
ALLOWED_ORIGINS=https://your-domain.com

# Database
DATABASE_URL=sqlite:///data/jps_aggregate.db
USER_DATABASE_URL=sqlite:///data/jps_users.db

# External Services
OLLAMA_BASE_URL=http://ollama:11434  # Or cloud LLM endpoint

# Cloudflare
CLOUDFLARE_TUNNEL_TOKEN=<your-tunnel-token>

# Frontend (for build time)
VITE_API_URL=https://your-domain.com
```

### Phase 5: Testing & Validation

#### 5.1 Test Production Build Locally
```bash
# Build and run with production settings
docker-compose --env-file .env.production build
docker-compose --env-file .env.production up

# Test endpoints
curl http://localhost:5001/health
curl http://localhost:5001/api/prospects
```

#### 5.2 Validation Checklist
- [ ] Frontend loads and displays properly
- [ ] Authentication flow works
- [ ] API calls succeed through proxy
- [ ] Database persistence works
- [ ] File uploads/downloads work
- [ ] Scrapers run (if enabled)
- [ ] LLM enhancement works (if configured)

## Quick Start Commands

### For Immediate Deployment (Minimum Viable)
```bash
# 1. Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# 2. Create minimal .env.production
cat > .env.production << EOF
ENVIRONMENT=production
SECRET_KEY=<your-generated-key>
DEBUG=False
SESSION_COOKIE_SECURE=True
ALLOWED_ORIGINS=https://your-domain.com
CLOUDFLARE_TUNNEL_TOKEN=<your-tunnel-token>
EOF

# 3. Build and deploy
docker-compose --env-file .env.production build
docker-compose --env-file .env.production --profile cloudflare up -d
```

### Monitoring & Maintenance
```bash
# View logs
docker-compose logs -f web

# Check health
curl https://your-domain.com/health

# Database backup
docker exec jps-web sqlite3 /app/data/jps_aggregate.db ".backup /app/backups/backup.db"
```

## Recommended Immediate Actions

1. **First Priority**: Generate and set a strong SECRET_KEY
2. **Second Priority**: Update CORS to include your production domain
3. **Third Priority**: Set up Cloudflare tunnel and get token
4. **Fourth Priority**: Deploy with Docker using production settings
5. **Fifth Priority**: Test thoroughly before giving access to employees

## Notes for Ongoing Development

- Keep development and production configurations separate
- Use environment variables for all deployment-specific settings
- Consider implementing proper logging and monitoring
- Plan for database backups and data persistence
- Document any custom deployment steps for your team

## Support Resources

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Flask Production Deployment](https://flask.palletsprojects.com/en/latest/deploying/)
- [Docker Compose Best Practices](https://docs.docker.com/compose/production/)