# Quick Start Script for Windows
# Run this after cloning the repository and configuring .env

Write-Host "JPS Prospect Aggregate - Quick Start for Windows" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Check if Docker is running
Write-Host "`nChecking Docker Desktop..." -ForegroundColor Yellow
docker version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker Desktop is not running! Please start Docker Desktop first." -ForegroundColor Red
    Write-Host "Download from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}
Write-Host "Docker Desktop is running." -ForegroundColor Green

# Check if .env exists
Write-Host "`nChecking configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host ".env file not found! Creating from template..." -ForegroundColor Yellow
    Copy-Item ".env.production" ".env"
    Write-Host "Please edit .env file with your settings before continuing." -ForegroundColor Red
    notepad .env
    Write-Host "Press any key when you've saved your .env file..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
}
Write-Host "Configuration found." -ForegroundColor Green

# Create necessary directories
Write-Host "`nCreating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path data, logs, backups | Out-Null
Write-Host "Directories created." -ForegroundColor Green

# Start services
Write-Host "`nStarting services..." -ForegroundColor Yellow
docker-compose up -d

# Wait for services
Write-Host "`nWaiting for services to start (30 seconds)..." -ForegroundColor Yellow
$startTime = Get-Date
while ((Get-Date) -lt $startTime.AddSeconds(30)) {
    $elapsed = [math]::Round(((Get-Date) - $startTime).TotalSeconds)
    Write-Progress -Activity "Starting services" -Status "$elapsed seconds elapsed" -PercentComplete (($elapsed / 30) * 100)
    Start-Sleep -Milliseconds 500
}
Write-Progress -Activity "Starting services" -Completed

# Check service status
Write-Host "`nChecking service status..." -ForegroundColor Yellow
docker-compose ps

# Initialize Ollama
Write-Host "`nInitializing Ollama LLM model (this may take a few minutes)..." -ForegroundColor Yellow
docker exec jps-ollama ollama pull qwen3:latest

# Initialize database
Write-Host "`nInitializing database..." -ForegroundColor Yellow
docker exec jps-web python scripts/setup_databases.py

# Health check
Write-Host "`nPerforming health check..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri http://localhost:5000/health -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "Application is healthy!" -ForegroundColor Green
    }
}
catch {
    Write-Host "Health check failed. Check logs with: docker logs jps-web" -ForegroundColor Red
}

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "`nApplication URL: http://localhost:5000" -ForegroundColor Cyan
Write-Host "`nUseful commands:" -ForegroundColor Yellow
Write-Host "  View logs:        docker-compose logs -f" -ForegroundColor White
Write-Host "  Stop services:    docker-compose down" -ForegroundColor White
Write-Host "  Deploy updates:   .\docker\deploy.ps1" -ForegroundColor White
Write-Host "  Manual backup:    docker exec jps-backup /backup.sh" -ForegroundColor White

# Open browser
$openBrowser = Read-Host "`nOpen application in browser? (Y/N)"
if ($openBrowser -eq 'Y' -or $openBrowser -eq 'y') {
    Start-Process "http://localhost:5000"
}