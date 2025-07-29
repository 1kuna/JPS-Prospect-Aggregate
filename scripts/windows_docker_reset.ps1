# Windows PowerShell script to reset Docker deployment
# Run this script when migrations are stuck

Write-Host "=== JPS Docker Reset Script for Windows ===" -ForegroundColor Cyan
Write-Host ""

# Function to run docker-compose commands
function Run-DockerCompose {
    param($command)
    $result = docker-compose $command.Split() 2>&1
    return $result
}

# Check if docker-compose is available
try {
    docker-compose version | Out-Null
} catch {
    Write-Host "ERROR: docker-compose not found. Please ensure Docker Desktop is installed and running." -ForegroundColor Red
    exit 1
}

Write-Host "This script will reset your Docker deployment to fix migration issues." -ForegroundColor Yellow
Write-Host "WARNING: This will stop all containers but preserve your data." -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Continue? (y/N)"

if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Write-Host "Aborted." -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "Step 1: Stopping all containers..." -ForegroundColor Green
docker-compose stop

Write-Host ""
Write-Host "Step 2: Removing web container to force rebuild..." -ForegroundColor Green
docker-compose rm -f web

Write-Host ""
Write-Host "Step 3: Checking database state..." -ForegroundColor Green
$dbRunning = docker-compose ps db | Select-String "Up"
if (-not $dbRunning) {
    Write-Host "Starting database container..." -ForegroundColor Yellow
    docker-compose up -d db
    Start-Sleep -Seconds 10
}

Write-Host ""
Write-Host "Step 4: Cleaning up migration state..." -ForegroundColor Green
# Try to connect to database and clean up
$cleanupCommands = @(
    "DROP TABLE IF EXISTS alembic_version;",
    "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));",
    "INSERT INTO alembic_version (version_num) VALUES ('000_create_base_tables');"
)

foreach ($cmd in $cleanupCommands) {
    Write-Host "Executing: $cmd" -ForegroundColor Gray
    docker-compose exec -T db psql -U jps_user -d jps_prospects -c $cmd 2>&1 | Out-Null
}

Write-Host ""
Write-Host "Step 5: Rebuilding web container with latest fixes..." -ForegroundColor Green
docker-compose build --no-cache web

Write-Host ""
Write-Host "Step 6: Starting services..." -ForegroundColor Green
docker-compose up -d

Write-Host ""
Write-Host "Step 7: Waiting for services to stabilize..." -ForegroundColor Green
Start-Sleep -Seconds 15

Write-Host ""
Write-Host "Step 8: Checking service status..." -ForegroundColor Green
docker-compose ps

Write-Host ""
Write-Host "Step 9: Checking migration status..." -ForegroundColor Green
docker-compose exec web flask db current

Write-Host ""
Write-Host "Step 10: Viewing recent logs..." -ForegroundColor Green
docker-compose logs --tail=20 web

Write-Host ""
Write-Host "=== Reset Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check if the application is running at: http://localhost:5001" -ForegroundColor Yellow
Write-Host ""
Write-Host "If you still see errors, try:" -ForegroundColor Yellow
Write-Host "  1. docker-compose down -v  (WARNING: This deletes all data)" -ForegroundColor Red
Write-Host "  2. docker-compose up --build -d" -ForegroundColor Yellow
Write-Host ""