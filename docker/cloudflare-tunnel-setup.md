# Cloudflare Tunnel Setup Guide - Squarespace Domain

This guide will help you expose your local Windows PC application to the internet using your Squarespace domain through Cloudflare Tunnel.

## Overview

Cloudflare Tunnel creates a secure connection between your Windows PC and Cloudflare's network without opening any ports on your router. Your Squarespace domain will point to Cloudflare, which tunnels traffic to your PC.

## Prerequisites

- A domain registered with Squarespace
- A Cloudflare account (free tier is fine)
- Your JPS application running on Windows PC

## Step 1: Transfer DNS to Cloudflare

### On Cloudflare:

1. **Create a Cloudflare account** at https://cloudflare.com
2. **Add your site**:
   - Click "Add a Site" 
   - Enter your domain (e.g., `yourdomain.com`)
   - Select the Free plan
3. **Copy the nameservers** Cloudflare provides (they look like):
   - `anna.ns.cloudflare.com`
   - `bob.ns.cloudflare.com`

### On Squarespace:

1. **Login to Squarespace** and go to your domain settings
2. **Navigate to**: Settings → Domains → Your Domain
3. **Click** "Advanced Settings" or "DNS Settings"
4. **Change nameservers**:
   - Look for "Nameservers" or "Use custom nameservers"
   - Replace Squarespace nameservers with Cloudflare's
   - Save changes

**Note**: DNS propagation takes 24-48 hours, but often works within minutes.

## Step 2: Create Cloudflare Tunnel

### On Cloudflare Dashboard:

1. **Go to** Zero Trust → Access → Tunnels
2. **Click** "Create a tunnel"
3. **Name your tunnel**: `jps-prospect-aggregate`
4. **Save tunnel**

### Install and Run Connector on Windows:

1. **Choose Windows** as your environment
2. **Download the installer** or use the command provided
3. **Open PowerShell as Administrator** and run:

```powershell
# Cloudflare will show you a command like this:
# Copy and paste the EXACT command from your Cloudflare dashboard
cloudflared service install <YOUR-TOKEN-HERE>
```

4. **Verify tunnel is running**:
```powershell
# Check service status
Get-Service cloudflared

# View logs
cloudflared tail
```

## Step 3: Configure Tunnel Routes

### In Cloudflare Dashboard:

1. **Go to your tunnel** configuration
2. **Click** "Configure" → "Public Hostname"
3. **Add a public hostname**:
   - **Subdomain**: `app` (or leave blank for root domain)
   - **Domain**: Select your domain
   - **Type**: `HTTP`
   - **URL**: `localhost:5000`

### Advanced Settings (recommended):

- **Enable** "No TLS Verify" (since localhost uses HTTP)
- **HTTP Host Header**: Leave as default
- **Origin Server Name**: Leave empty

## Step 4: Configure Docker for Cloudflare

### Update your docker-compose.yml (optional):

If you want the tunnel to auto-start with your app:

```yaml
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: jps-cloudflared
    restart: unless-stopped
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    networks:
      - jps-network
```

### Add to .env file:

```bash
# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_TOKEN=your-tunnel-token-here
```

## Step 5: DNS Configuration

### In Cloudflare DNS:

1. **Go to** DNS → Records
2. **Ensure you have**:
   - `A` record: `@` → `100.64.0.0` (dummy IP, tunnel will override)
   - `CNAME` record: `app` → `@` (if using subdomain)
   - **Orange cloud** must be ON (proxied)

## Step 6: Test Your Setup

1. **Local test**:
   ```powershell
   # Ensure your app is running
   curl http://localhost:5000/health
   ```

2. **Tunnel test**:
   - Visit `https://yourdomain.com` or `https://app.yourdomain.com`
   - You should see your application!

3. **Check tunnel status**:
   - Cloudflare Dashboard → Zero Trust → Tunnels
   - Your tunnel should show as "Healthy"

## Troubleshooting

### Site not loading?

1. **Check tunnel status**:
   ```powershell
   Get-Service cloudflared
   cloudflared tunnel info
   ```

2. **Check Docker**:
   ```powershell
   docker ps
   docker logs jps-web
   ```

3. **DNS issues**:
   - Use `nslookup yourdomain.com`
   - Should resolve to Cloudflare IPs

### Common Issues:

- **502 Bad Gateway**: App not running or wrong port
- **523 Origin Unreachable**: Tunnel not connected
- **521 Web Server Down**: Docker containers not running

### Cloudflare Tunnel Logs:

```powershell
# View tunnel logs
cloudflared tail

# Test tunnel connection
cloudflared tunnel run --hello-world
```

## Security Benefits

Using Cloudflare Tunnel provides:

1. **No open ports** on your router
2. **DDoS protection** from Cloudflare
3. **SSL/TLS encryption** automatically
4. **Web Application Firewall** (if enabled)
5. **Hide your home IP** address

## Optional: Access Restrictions

### Add authentication (Zero Trust):

1. **Go to** Zero Trust → Access → Applications
2. **Create application** for your tunnel
3. **Add policies**:
   - Email authentication
   - IP restrictions
   - Device requirements

### Example policy:
- **Name**: "JPS Admin Access"
- **Action**: Allow
- **Include**: Emails ending in `@yourdomain.com`

## Maintenance

### Update tunnel:
```powershell
# Windows
cloudflared update

# Or download latest from Cloudflare
```

### View metrics:
- Cloudflare Dashboard → Analytics
- See traffic, threats blocked, bandwidth used

### Restart tunnel:
```powershell
Restart-Service cloudflared
```

## Quick Reference

After setup, your architecture looks like:

```
[Internet Users] → [Cloudflare Network] → [Tunnel] → [Your Windows PC] → [Docker Containers]
```

Domain: `yourdomain.com` → Cloudflare DNS → Tunnel → `localhost:5000`

## Next Steps

1. **Test everything** works as expected
2. **Set up monitoring** (optional)
3. **Configure backups** for your data
4. **Plan deployment** schedule

Remember: Your Windows PC needs to stay on and connected to the internet for the site to be accessible!