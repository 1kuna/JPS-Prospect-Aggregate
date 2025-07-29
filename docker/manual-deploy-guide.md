# Manual Deployment Guide

This guide explains how to manually deploy updates to your JPS Prospect Aggregate application.

## Quick Start: Deploy from GitHub UI

1. **Navigate to Actions**
   - Go to your GitHub repository
   - Click the "Actions" tab at the top

2. **Run the Deployment**
   - Find "Deploy to Production" in the workflows list
   - Click on it
   - Click the "Run workflow" button on the right
   - Select branch: `main` (or your feature branch)
   - Click the green "Run workflow" button

3. **Monitor Progress**
   - The deployment will start within a few seconds
   - Click on the running workflow to see live logs
   - Total deployment time: ~5-10 minutes

4. **Verify Deployment**
   - Check the green checkmark when complete
   - Visit your site to confirm updates are live

## Alternative Methods

### Deploy from Command Line (GitHub CLI)

```bash
# Install GitHub CLI first: https://cli.github.com/

# Deploy latest main branch
gh workflow run deploy.yml --ref main

# Deploy a specific branch
gh workflow run deploy.yml --ref feature/my-branch

# Check deployment status
gh run list --workflow=deploy.yml --limit 5

# Watch deployment logs
gh run watch
```

### Deploy Directly on Windows PC

```powershell
# Navigate to project directory
cd C:\Docker\JPS-Prospect-Aggregate

# Get latest code
git pull origin main

# Run deployment
.\docker\deploy.ps1

# Skip maintenance mode (risky but faster)
.\docker\deploy.ps1 -SkipMaintenance

# Skip backup (not recommended)
.\docker\deploy.ps1 -SkipBackup
```

## Deployment Process Overview

When you trigger a deployment, here's what happens:

1. **GitHub Actions** (if using GitHub deployment):
   - Builds a new Docker image
   - Runs security scans
   - Pushes to Docker Hub
   - Connects to your Windows PC via SSH

2. **On Your Windows PC**:
   - Shows maintenance page to users
   - Backs up databases
   - Pulls new Docker images
   - Stops old containers
   - Starts new containers
   - Runs database migrations
   - Performs health checks
   - Removes maintenance page

3. **Safety Features**:
   - Automatic database backup before any changes
   - Health checks before going live
   - Easy rollback if something goes wrong

## Troubleshooting

### Deployment Failed?

1. **Check GitHub Actions logs**:
   - Click on the failed workflow run
   - Expand the failed step
   - Look for error messages

2. **Common Issues**:
   - Docker Hub login failed → Check secrets in GitHub settings
   - SSH connection failed → Verify Windows PC is accessible
   - Build failed → Check recent code changes

3. **On Windows PC**:
   ```powershell
   # Check if maintenance mode is stuck
   docker ps | Select-String maintenance
   
   # Remove maintenance page manually
   docker rm -f maintenance-page
   
   # Check application logs
   docker logs jps-web --tail 100
   ```

### Need to Rollback?

```powershell
# On Windows PC - List recent images
docker images | Select-String jps-prospect

# Rollback to previous version
docker-compose down
docker run -d --name jps-web YOUR_USERNAME/jps-prospect-aggregate:[previous-sha]

# Or restore from backup
Get-ChildItem backups\ | Sort-Object LastWriteTime -Descending
# Pick a backup file and restore it
```

## Best Practices

1. **Always deploy during low-traffic times**
2. **Test changes locally first**
3. **Keep an eye on the deployment progress**
4. **Have a rollback plan ready**
5. **Don't skip backups unless absolutely necessary**

## Deployment Schedule

Recommended deployment windows:
- Early morning (before business hours)
- Late evening
- Weekends for major updates

Avoid:
- Middle of the workday
- During known high-usage periods
- Right before leaving for the day

## Getting Help

- Check deployment logs in GitHub Actions
- Review Windows Event Viewer for system issues
- Docker logs: `docker logs [container-name]`
- Contact support with deployment run ID from GitHub Actions