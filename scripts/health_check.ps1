# Quick Health Check Script for JPS Docker Deployment

Write-Host "=== JPS Docker Health Check ===" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "[OK] Docker is running" -ForegroundColor Green
}
catch {
    Write-Host "[FAIL] Docker is not running or not installed" -ForegroundColor Red
    exit 1
}

# Check container status
Write-Host ""
Write-Host "Container Status:" -ForegroundColor Yellow

# Get container status safely
try {
    $containerOutput = docker-compose ps 2>&1
    if ($containerOutput -match "error" -or $containerOutput -match "ERROR") {
        Write-Host "[FAIL] Unable to get container status" -ForegroundColor Red
    }
    else {
        $services = @("web", "db", "ollama")
        foreach ($service in $services) {
            if ($containerOutput -match "$service.*Up") {
                Write-Host "[OK] $service : running" -ForegroundColor Green
            }
            elseif ($containerOutput -match "$service") {
                Write-Host "[FAIL] $service : not running" -ForegroundColor Red
            }
            else {
                Write-Host "[FAIL] $service : not found" -ForegroundColor Red
            }
        }
    }
}
catch {
    Write-Host "[FAIL] Error checking container status" -ForegroundColor Red
}

# Check web application
Write-Host ""
Write-Host "Web Application:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5001/health" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] Web app responding on http://localhost:5001" -ForegroundColor Green
    }
    else {
        Write-Host "[WARN] Web app responding with HTTP $($response.StatusCode)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "[FAIL] Web app not responding on http://localhost:5001" -ForegroundColor Red
}

# Check database connection
Write-Host ""
Write-Host "Database:" -ForegroundColor Yellow
try {
    $dbTest = docker-compose exec -T db psql -U jps_user -d jps_prospects -c "SELECT 1;" 2>&1
    if ($dbTest -match "1") {
        Write-Host "[OK] Database connection working" -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] Database connection failed" -ForegroundColor Red
    }
}
catch {
    Write-Host "[FAIL] Unable to test database connection" -ForegroundColor Red
}

# Check migration status
Write-Host ""
Write-Host "Migration Status:" -ForegroundColor Yellow
try {
    $migrationStatus = docker-compose exec -T web flask db current 2>&1
    if ($migrationStatus -match "error" -or $migrationStatus -match "ERROR") {
        Write-Host "[FAIL] Migration errors detected" -ForegroundColor Red
        Write-Host "  Run .\scripts\windows_docker_reset.ps1 to fix" -ForegroundColor Gray
    }
    else {
        Write-Host "[OK] Migrations appear to be working" -ForegroundColor Green
        Write-Host "  Current: $migrationStatus" -ForegroundColor Gray
    }
}
catch {
    Write-Host "[FAIL] Unable to check migration status" -ForegroundColor Red
}

# Recent logs
Write-Host ""
Write-Host "Recent Web Container Logs:" -ForegroundColor Yellow
try {
    docker-compose logs --tail=5 web
}
catch {
    Write-Host "[FAIL] Unable to get container logs" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Health Check Complete ===" -ForegroundColor Cyan