# Nuclear Reset Script for JPS Docker Deployment
# This completely destroys and recreates everything from scratch

Write-Host "=== JPS NUCLEAR RESET SCRIPT ===" -ForegroundColor Red
Write-Host "This script will COMPLETELY DESTROY your Docker deployment and recreate it from scratch." -ForegroundColor Red
Write-Host "ALL DATA WILL BE LOST!" -ForegroundColor Red
Write-Host ""

# Function to run docker-compose commands safely
function Run-DockerCompose {
    param($command)
    try {
        $result = docker-compose $command.Split() 2>&1
        return $result
    } catch {
        Write-Host "Error running docker-compose $command : $_" -ForegroundColor Red
        return $null
    }
}

# Check prerequisites
try {
    docker-compose version | Out-Null
    docker version | Out-Null
} catch {
    Write-Host "ERROR: Docker or docker-compose not found. Please ensure Docker Desktop is running." -ForegroundColor Red
    exit 1
}

Write-Host "This will:" -ForegroundColor Yellow
Write-Host "  1. Stop and remove ALL containers" -ForegroundColor Yellow
Write-Host "  2. Remove ALL volumes (DELETE ALL DATA)" -ForegroundColor Yellow
Write-Host "  3. Remove ALL images for this project" -ForegroundColor Yellow
Write-Host "  4. Rebuild everything from scratch" -ForegroundColor Yellow
Write-Host ""

$confirm1 = Read-Host "Type 'DESTROY' to confirm you want to delete all data"
if ($confirm1 -ne 'DESTROY') {
    Write-Host "Aborted - you must type exactly 'DESTROY' to proceed." -ForegroundColor Green
    exit 0
}

$confirm2 = Read-Host "Are you absolutely sure? Type 'YES' to proceed"
if ($confirm2 -ne 'YES') {
    Write-Host "Aborted." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "=== NUCLEAR RESET STARTING ===" -ForegroundColor Red

Write-Host ""
Write-Host "Step 1: Stopping all containers..." -ForegroundColor Cyan
docker-compose down 2>&1

Write-Host ""
Write-Host "Step 2: Removing all volumes (DELETING ALL DATA)..." -ForegroundColor Cyan
docker-compose down -v 2>&1

Write-Host ""
Write-Host "Step 3: Removing JPS images..." -ForegroundColor Cyan
docker image rm jps-prospect-aggregate:latest 2>&1 | Out-Null
docker image prune -f 2>&1 | Out-Null

Write-Host ""
Write-Host "Step 4: Cleaning up orphaned containers..." -ForegroundColor Cyan
docker container prune -f 2>&1 | Out-Null

Write-Host ""
Write-Host "Step 5: Cleaning up networks..." -ForegroundColor Cyan
docker network prune -f 2>&1 | Out-Null

Write-Host ""
Write-Host "Step 6: Building fresh images..." -ForegroundColor Cyan
docker-compose build --no-cache --parallel

Write-Host ""
Write-Host "Step 7: Starting services..." -ForegroundColor Cyan
docker-compose up -d

Write-Host ""
Write-Host "Step 8: Waiting for services to initialize..." -ForegroundColor Cyan
$timeout = 60
$elapsed = 0
do {
    Start-Sleep -Seconds 5
    $elapsed += 5
    $webStatus = docker-compose ps web | Select-String "Up"
    $dbStatus = docker-compose ps db | Select-String "Up.*healthy"
    
    Write-Host "Waiting... ($elapsed/$timeout seconds)" -ForegroundColor Gray
    
    if ($webStatus -and $dbStatus) {
        Write-Host "Services are running!" -ForegroundColor Green
        break
    }
    
    if ($elapsed -ge $timeout) {
        Write-Host "Timeout waiting for services to start." -ForegroundColor Yellow
        break
    }
} while ($true)

Write-Host ""
Write-Host "Step 9: Checking final status..." -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "Step 10: Testing database connection..." -ForegroundColor Cyan
$dbTest = docker-compose exec -T db psql -U jps_user -d jps_prospects -c "SELECT 1;" 2>&1
if ($dbTest -match "1") {
    Write-Host "Database connection: OK" -ForegroundColor Green
} else {
    Write-Host "Database connection: FAILED" -ForegroundColor Red
    Write-Host $dbTest
}

Write-Host ""
Write-Host "Step 11: Checking migration status..." -ForegroundColor Cyan
$migrationStatus = docker-compose exec -T web flask db current 2>&1
Write-Host "Migration status: $migrationStatus"

Write-Host ""
Write-Host "Step 12: Testing web application..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5001/health" -TimeoutSec 10 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "Web application: OK" -ForegroundColor Green
    } else {
        Write-Host "Web application: HTTP $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Web application: NOT RESPONDING" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose logs web"
}

Write-Host ""
Write-Host "=== NUCLEAR RESET COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "Your application should be available at: http://localhost:5001" -ForegroundColor Yellow
Write-Host ""
Write-Host "If you still have issues:" -ForegroundColor Yellow
Write-Host "  - Check logs: docker-compose logs web" -ForegroundColor Gray
Write-Host "  - Check database: docker-compose logs db" -ForegroundColor Gray
Write-Host "  - Restart services: docker-compose restart" -ForegroundColor Gray
Write-Host ""