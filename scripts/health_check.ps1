# Quick Health Check Script for JPS Docker Deployment

Write-Host "=== JPS Docker Health Check ===" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running or not installed" -ForegroundColor Red
    exit 1
}

# Check container status
Write-Host ""
Write-Host "Container Status:" -ForegroundColor Yellow
$containers = docker-compose ps --format json | ConvertFrom-Json

$services = @("web", "db", "ollama")
foreach ($service in $services) {
    $container = $containers | Where-Object { $_.Service -eq $service }
    if ($container) {
        $status = $container.State
        if ($status -eq "running") {
            Write-Host "✓ $service : $status" -ForegroundColor Green
        } else {
            Write-Host "✗ $service : $status" -ForegroundColor Red
        }
    } else {
        Write-Host "✗ $service : not found" -ForegroundColor Red
    }
}

# Check web application
Write-Host ""
Write-Host "Web Application:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5001/health" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Web app responding on http://localhost:5001" -ForegroundColor Green
    } else {
        Write-Host "⚠ Web app responding with HTTP $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Web app not responding on http://localhost:5001" -ForegroundColor Red
}

# Check database connection
Write-Host ""
Write-Host "Database:" -ForegroundColor Yellow
try {
    $dbTest = docker-compose exec -T db psql -U jps_user -d jps_prospects -c "SELECT 1;" 2>&1
    if ($dbTest -match "1") {
        Write-Host "✓ Database connection working" -ForegroundColor Green
    } else {
        Write-Host "✗ Database connection failed" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Unable to test database connection" -ForegroundColor Red
}

# Check migration status
Write-Host ""
Write-Host "Migration Status:" -ForegroundColor Yellow
try {
    $migrationStatus = docker-compose exec -T web flask db current 2>&1
    if ($migrationStatus -match "error" -or $migrationStatus -match "ERROR") {
        Write-Host "✗ Migration errors detected" -ForegroundColor Red
        Write-Host "  Run .\scripts\windows_docker_reset.ps1 to fix" -ForegroundColor Gray
    } else {
        Write-Host "✓ Migrations appear to be working" -ForegroundColor Green
        Write-Host "  Current: $migrationStatus" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Unable to check migration status" -ForegroundColor Red
}

# Recent logs
Write-Host ""
Write-Host "Recent Web Container Logs:" -ForegroundColor Yellow
docker-compose logs --tail=5 web

Write-Host ""
Write-Host "=== Health Check Complete ===" -ForegroundColor Cyan