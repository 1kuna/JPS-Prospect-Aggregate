# Production Setup Guide - Windows

## On Your Windows PC

### 1. Install Docker Desktop

Download and install Docker Desktop for Windows from:
https://www.docker.com/products/docker-desktop/

Requirements:
- Windows 10 64-bit: Pro, Enterprise, or Education (Build 19041 or higher)
- Windows 11 64-bit: Home, Pro, Enterprise, or Education
- Enable WSL 2 feature
- 4GB system RAM minimum

During installation:
- Use WSL 2 instead of Hyper-V (recommended)
- Start Docker Desktop after installation
- Verify Docker is running (whale icon in system tray)

### 2. Clone Repository

Open PowerShell or Windows Terminal as Administrator:

```powershell
# Navigate to where you want to install (e.g., C:\Docker)
cd C:\
mkdir Docker
cd Docker

# Clone the repository
git clone https://github.com/YOUR_USERNAME/JPS-Prospect-Aggregate.git
cd JPS-Prospect-Aggregate
```

### 3. Configure Environment

```powershell
# Copy production environment template
copy .env.production.example .env.production

# Edit with Notepad or your preferred editor
notepad .env.production
# Required changes:
# - Set DB_PASSWORD to a strong password
# - Set SECRET_KEY to a random secret key
# - Verify PORT=5001 (default, don't change unless needed)
# Save and close when done
```

### 4. Initial Setup

```powershell
# Create necessary directories
mkdir data, logs, backups -Force

# Start services (Docker Desktop must be running)
docker-compose up -d

# Wait for services to start (about 30 seconds)
Start-Sleep -Seconds 30

# Initialize Ollama model
docker exec jps-ollama ollama pull qwen3:latest

# Run initial database setup
docker exec jps-web python scripts/setup_databases.py
```

### 5. Test the deployment

```powershell
# Check all services are running
docker-compose ps

# Check application health (PowerShell)
Invoke-WebRequest -Uri http://localhost:5001/health -UseBasicParsing

# Or open in browser
Start-Process "http://localhost:5001"
```

## On Your Development Machine

### 1. Set up GitHub repository

```bash
# If not already done
git remote add origin https://github.com/YOUR_USERNAME/JPS-Prospect-Aggregate.git
git push -u origin main
```

### 2. Configure GitHub Secrets

Go to Settings → Secrets and add:
- `DOCKER_USERNAME`: Your Docker Hub username
- `DOCKER_PASSWORD`: Your Docker Hub password
- `PRODUCTION_HOST`: Your Windows PC's IP or domain
- `PRODUCTION_USER`: Your Windows username
- `PRODUCTION_SSH_KEY`: Private SSH key (see below)
- `SLACK_WEBHOOK`: (Optional) For notifications

### 3. Enable SSH on Windows (for automated deployment)

On your Windows PC:

```powershell
# Install OpenSSH Server (Run as Administrator)
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# Start SSH service
Start-Service sshd

# Set to start automatically
Set-Service -Name sshd -StartupType 'Automatic'

# Check Windows Firewall rule
Get-NetFirewallRule -Name *ssh*

# Generate SSH key on your dev machine and copy to Windows
# On dev machine:
ssh-keygen -t ed25519 -f ~/.ssh/jps-deploy-key

# Copy public key to Windows PC
# Replace USER and WINDOWS_IP
ssh USER@WINDOWS_IP "mkdir -p .ssh"
scp ~/.ssh/jps-deploy-key.pub USER@WINDOWS_IP:.ssh/authorized_keys

# On Windows, fix permissions (PowerShell as Admin):
icacls C:\Users\YOUR_USERNAME\.ssh\authorized_keys /inheritance:r /grant "YOUR_USERNAME:F" /grant "SYSTEM:F"
```

## Deployment Workflow

### Manual Deployment via GitHub Actions (Recommended)

1. Make changes on your laptop
2. Commit and push to main branch (this just syncs code, doesn't deploy)
3. When ready to deploy:
   - Go to your GitHub repository
   - Click the "Actions" tab
   - Select "Deploy to Production" workflow
   - Click "Run workflow" button
   - Select branch (usually main)
   - Click green "Run workflow" button
4. GitHub Actions will:
   - Build Docker image
   - Push to Docker Hub
   - SSH to Windows PC
   - Run deployment with maintenance mode
   - Backup database before changes
   - Run migrations
   - Restore service

### Manual Deployment from Command Line

If you have GitHub CLI installed:
```bash
# Deploy from your laptop
gh workflow run deploy.yml --ref main

# Check deployment status
gh run list --workflow=deploy.yml
```

### Local Manual Deployment on Windows PC

```powershell
# Open PowerShell in project directory
cd C:\Docker\JPS-Prospect-Aggregate

# Pull latest code
git pull origin main

# Run the deployment script
.\docker\deploy.ps1
```

## Domain Access Options

### Option 1: Cloudflare Tunnel (Recommended)

See the complete setup guide: [cloudflare-tunnel-setup.md](cloudflare-tunnel-setup.md)

Quick start:
```powershell
# Install Cloudflare connector
# Get your token from Cloudflare Dashboard → Zero Trust → Tunnels
cloudflared service install YOUR-TUNNEL-TOKEN

# Or run via Docker
docker run -d `
  --name cloudflared `
  --restart unless-stopped `
  cloudflare/cloudflared:latest tunnel `
  --no-autoupdate run `
  --token YOUR_TUNNEL_TOKEN
```

Benefits:
- No port forwarding needed
- Automatic SSL/TLS
- DDoS protection
- Works with Squarespace domains

### Option 2: Traditional Port Forwarding
1. Forward port 80/443 to your spare PC
2. Use Let's Encrypt with nginx-proxy:
```yaml
# Add to docker-compose.yml
nginx-proxy:
  image: nginxproxy/nginx-proxy
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - /var/run/docker.sock:/tmp/docker.sock:ro
    - certs:/etc/nginx/certs
    - vhost:/etc/nginx/vhost.d
    - html:/usr/share/nginx/html

letsencrypt:
  image: nginxproxy/acme-companion
  volumes_from:
    - nginx-proxy
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - acme:/etc/acme.sh
  environment:
    - DEFAULT_EMAIL=your-email@domain.com
```

## Monitoring

### Check logs

```powershell
# Application logs
docker logs jps-web

# Database logs  
docker logs jps-db

# All logs (follow mode)
docker-compose logs -f

# Save logs to file
docker logs jps-web > web-logs.txt 2>&1
```

### Database backups

```powershell
# Manual backup
docker exec jps-backup /backup.sh

# List backups
Get-ChildItem backups\ | Sort-Object LastWriteTime -Descending

# Restore from backup (PowerShell)
Get-Content backups\jps_prospects_20240101_120000.sql | docker exec -i jps-db psql -U jps_user jps_prospects
```

## Troubleshooting

### If deployment fails

1. Check Docker Desktop is running (whale icon in system tray)
2. Check maintenance mode: 
   ```powershell
   docker ps | Select-String maintenance
   ```
3. Check logs: 
   ```powershell
   docker logs jps-web --tail 50
   ```
4. Manually restore: 
   ```powershell
   docker-compose up -d
   ```

### Database issues

```powershell
# Connect to database
docker exec -it jps-db psql -U jps_user -d jps_prospects

# Check migrations
docker exec jps-web alembic current

# If connection fails, restart database
docker-compose restart db
```

### Windows-specific issues

1. **Docker Desktop not starting**: 
   - Enable virtualization in BIOS
   - Ensure WSL 2 is installed: `wsl --install`
   
2. **Port already in use**:
   ```powershell
   # Find what's using port 5001
   netstat -ano | findstr :5001
   # Kill the process using the PID from above
   taskkill /PID <PID> /F
   ```

3. **File permission issues**:
   - Run PowerShell as Administrator
   - Docker Desktop → Settings → Resources → File Sharing → Add project directory

### Rollback procedure

```powershell
# List available images
docker images | Select-String jps-prospect

# Use previous image tag
docker-compose down
docker run -d --name jps-web YOUR_USERNAME/jps-prospect-aggregate:previous-sha
```