# Docker Deployment Documentation

This directory contains all the scripts and documentation needed to deploy the JPS Prospect Aggregate application using Docker.

## Quick Start Guides

1. **[setup-production.md](setup-production.md)** - Complete Windows setup guide
2. **[cloudflare-tunnel-setup.md](cloudflare-tunnel-setup.md)** - Connect your Squarespace domain
3. **[manual-deploy-guide.md](manual-deploy-guide.md)** - How to deploy updates

## Key Scripts

### For Initial Setup
- **`quick-start-windows.ps1`** - One-click initial setup on Windows
- **`init-db.sh`** - Database initialization (runs automatically)

### For Deployment
- **`deploy.ps1`** - Main deployment script with safety features
- **`update-site.ps1`** - Simple double-click updater
- **`deploy.sh`** - Linux/Mac deployment script (if needed)

### For Maintenance
- **`backup.sh`** - Automated backup script (runs daily)
- **`maintenance.html`** - Shown to users during updates

## Deployment Workflow

```
[Your Laptop] → Push to GitHub → Manual trigger → [GitHub Actions] → [Windows PC]
```

1. Make changes on your development machine
2. Push to GitHub (just for backup/sync)
3. When ready, trigger deployment manually
4. Site updates with zero data loss

## Architecture

```
Internet Users
    ↓
Cloudflare (SSL, DDoS protection)
    ↓
Cloudflare Tunnel
    ↓
Your Windows PC
    ↓
Docker Containers:
- Flask App (port 5001)
- SQLite Database (file-based)
- Ollama LLM
- Automated Backups
```

## Common Tasks

### Deploy Updates
```powershell
# Option 1: From GitHub Actions (recommended)
# Go to GitHub → Actions → Run workflow

# Option 2: From Windows PC
.\update-site.ps1
```

### Check Status
```powershell
docker-compose ps
docker logs jps-web --tail 50
```

### Manual Backup
```powershell
docker exec jps-backup /backup.sh
```

### Access Database
```powershell
docker exec -it jps-db psql -U jps_user -d jps_prospects
```

## Troubleshooting

See [setup-production.md](setup-production.md#troubleshooting) for detailed troubleshooting steps.

## Support Files

- **`.env`** - Template for environment variables
- **`Dockerfile`** - Container definition for the Flask app
- **`docker-compose.yml`** - Orchestrates all services
- **`.dockerignore`** - Excludes unnecessary files from builds

## Safety Features

1. **Automatic backups** before every deployment
2. **Maintenance mode** during updates
3. **Health checks** before going live
4. **Easy rollback** to previous versions
5. **No data loss** guarantee

For questions or issues, check the documentation files or create an issue on GitHub.