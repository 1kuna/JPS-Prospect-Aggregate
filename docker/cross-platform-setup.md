# Docker Cross-Platform Setup Guide

This guide ensures the JPS Prospect Aggregate Docker setup works seamlessly on both Windows and macOS/Linux systems.

## Prerequisites

### All Platforms
- Docker Desktop installed and running
- Git installed
- Python 3.11+ (for generating SECRET_KEY)
- At least 8GB of available disk space (for Ollama model)

### Windows-Specific
- PowerShell 5.0 or higher
- Enable script execution: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Docker Desktop configured with WSL2 backend (recommended)

### macOS/Linux-Specific
- Docker Compose (usually included with Docker Desktop)
- Bash shell

## Quick Start

### For Windows Users

1. **Clone the repository**
   ```powershell
   git clone <repository-url>
   cd JPS-Prospect-Aggregate
   ```

2. **Run the setup script**
   ```powershell
   .\docker-start.ps1
   ```

### For macOS/Linux Users

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd JPS-Prospect-Aggregate
   ```

2. **Run the setup script**
   ```bash
   ./docker-start.sh
   ```

## Manual Setup (All Platforms)

If you prefer to set up manually or the scripts don't work:

1. **Copy and configure .env file**
   ```bash
   cp .env.example .env
   ```

2. **Edit .env file with your settings:**
   - Set `ENVIRONMENT=production`
   - Set a strong `DB_PASSWORD`
   - Generate and set `SECRET_KEY`:
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
   - Update database URLs to use production settings

3. **Start Docker services**
   ```bash
   docker-compose up -d
   ```

   Or with optional services:
   ```bash
   # With Watchtower (auto-updates)
   docker-compose --profile full up -d
   
   # With Cloudflare tunnel (if configured)
   docker-compose --profile cloudflare up -d
   ```

## Cross-Platform Features

### Line Endings
- `.gitattributes` file ensures consistent line endings
- Shell scripts automatically converted to LF in Docker build
- PowerShell scripts use CRLF for Windows compatibility

### Volume Mounts
- All volume mounts use relative paths (`./data`, `./logs`)
- Works identically on Windows and macOS/Linux
- Docker Desktop handles path translation on Windows

### Shell Scripts
- All shell scripts include cross-platform compatibility fixes
- `dos2unix` installed in containers to handle line endings
- Portable command alternatives used where possible

### Database Connectivity
- Uses `pg_isready` instead of `nc` for database checks
- More reliable across different environments
- Better error handling and logging

## Troubleshooting

### Windows Issues

1. **"Docker daemon is not running"**
   - Start Docker Desktop
   - Ensure WSL2 is properly configured

2. **Permission errors with volumes**
   - Run PowerShell as Administrator
   - Check Docker Desktop file sharing settings

3. **Line ending errors**
   - Git may convert line endings on Windows
   - The Docker build process automatically fixes this
   - If issues persist, run: `git config core.autocrlf false`

### macOS/Linux Issues

1. **"Permission denied" on scripts**
   ```bash
   chmod +x docker-start.sh
   chmod +x docker/*.sh
   ```

2. **Docker socket errors**
   - Ensure Docker Desktop is running
   - Check Docker daemon: `docker info`

### Common Issues (All Platforms)

1. **Port conflicts**
   - Web app uses port 5001
   - Ollama uses port 11434
   - Change in docker-compose.yml if needed

2. **Ollama model download slow**
   - First run downloads 5.2GB model
   - Check progress: `docker-compose logs -f ollama`

3. **Database initialization fails**
   - Check logs: `docker-compose logs db`
   - Ensure DB_PASSWORD is set in .env
   - Try clean restart: `docker-compose down -v && docker-compose up -d`

## Verifying Installation

After setup, verify everything is working:

1. **Check service status**
   ```bash
   docker-compose ps
   ```

2. **Access web interface**
   - http://localhost:5001
   - Should see the JPS Prospect Aggregate interface

3. **Check Ollama**
   ```bash
   curl http://localhost:11434/api/version
   ```

4. **View logs**
   ```bash
   docker-compose logs -f
   ```

## Platform-Specific Notes

### Windows with WSL2
- Better performance than Hyper-V backend
- Seamless Linux container support
- File system performance optimized

### macOS with Apple Silicon
- Docker Desktop runs x86 containers via Rosetta
- Native ARM images used where available
- Performance is generally excellent

### Linux
- Native Docker performance
- No translation layers needed
- Best overall performance

## Optional Services

### Watchtower (Auto-updates)
- Automatically updates containers
- Enable with `--profile full` flag
- Works identically on all platforms

### Cloudflare Tunnel
- Requires CLOUDFLARE_TUNNEL_TOKEN in .env
- Enable with `--profile cloudflare` flag
- Same configuration across platforms

## Best Practices

1. **Always use the provided scripts** for initial setup
2. **Keep .env file secure** and never commit it
3. **Regular backups** are automated via backup service
4. **Monitor logs** during first startup
5. **Use Docker Desktop** for GUI management

## Support

If you encounter platform-specific issues:

1. Check the logs: `docker-compose logs`
2. Verify prerequisites are installed
3. Ensure ports are not in use
4. Try a clean restart: `docker-compose down -v`
5. Report issues with platform details