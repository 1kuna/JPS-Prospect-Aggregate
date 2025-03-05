@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo JPS Prospect Aggregate Auto-Setup ^& Launch
echo ==========================================

:: Set colors for Windows console
set "GREEN=[92m"
set "RED=[91m"
set "BLUE=[94m"
set "RESET=[0m"

:: Function to print status messages
call :print_status "Starting setup process..."

:: Check if conda is installed
call :print_status "Checking for Conda installation..."
where conda >nul 2>&1
if %ERRORLEVEL% neq 0 (
    call :print_error "Conda is not installed. Please install Miniconda or Anaconda first."
    echo You can download it from: https://docs.conda.io/en/latest/miniconda.html
    exit /b 1
) else (
    call :print_success "Conda is installed"
)

:: Get conda base directory
for /f "tokens=*" %%a in ('conda info --base') do set "CONDA_BASE=%%a"

:: Activate conda environment
call :print_status "Setting up Conda environment..."
call "%CONDA_BASE%\Scripts\activate.bat"

:: Check if the conda environment exists
conda env list | findstr /C:"jps_env" >nul
if %ERRORLEVEL% neq 0 (
    echo Conda environment 'jps_env' not found. Creating...
    conda create -n jps_env python=3.12 -y
    if %ERRORLEVEL% neq 0 (
        call :print_error "Failed to create conda environment"
        exit /b 1
    )
    call :print_success "Created conda environment 'jps_env'"
) else (
    call :print_success "Found existing conda environment 'jps_env'"
)

:: Activate the environment
call :print_status "Activating conda environment..."
call conda activate jps_env
if %ERRORLEVEL% neq 0 (
    call :print_error "Failed to activate conda environment"
    exit /b 1
)
call :print_success "Activated conda environment 'jps_env'"

:: Check Python version
call :print_status "Checking Python version..."
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%a"
for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
    set "PYTHON_MAJOR=%%a"
    set "PYTHON_MINOR=%%b"
)

if !PYTHON_MAJOR! neq 3 (
    call :print_error "Python version !PYTHON_VERSION! is not compatible. Updating to Python 3.12..."
    conda install -y python=3.12
    if %ERRORLEVEL% neq 0 (
        call :print_error "Failed to update Python version"
        exit /b 1
    )
) else (
    if !PYTHON_MINOR! lss 10 (
        call :print_error "Python version !PYTHON_VERSION! is not compatible. Updating to Python 3.12..."
        conda install -y python=3.12
        if %ERRORLEVEL% neq 0 (
            call :print_error "Failed to update Python version"
            exit /b 1
        )
    ) else (
        call :print_success "Python version !PYTHON_VERSION! is compatible"
    )
)

:: Check if requirements.txt exists
call :print_status "Checking for requirements.txt..."
if not exist requirements.txt (
    call :print_error "requirements.txt not found. Cannot install dependencies."
    exit /b 1
) else (
    call :print_success "Found requirements.txt"
)

:: Install dependencies
call :print_status "Installing/updating dependencies..."
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    call :print_error "Failed to install dependencies"
    exit /b 1
)
call :print_success "Dependencies installed/updated"

:: Install Celery dependencies
call :print_status "Installing Celery dependencies..."
pip install redis celery flower
if %ERRORLEVEL% neq 0 (
    call :print_error "Failed to install Celery dependencies"
    exit /b 1
)
call :print_success "Celery dependencies installed"

:: Check for Redis (Windows)
call :print_status "Checking Redis installation..."

:: Check if Redis is installed by looking for redis-server.exe
where redis-server >nul 2>&1
if %ERRORLEVEL% neq 0 (
    call :print_error "Redis is not installed on Windows."
    echo Please download and install Redis for Windows from: https://github.com/microsoftarchive/redis/releases
    echo After installation, please restart this script.
    exit /b 1
) else (
    call :print_success "Redis is installed"
)

:: Check if Redis service is running
call :print_status "Checking if Redis is running..."
sc query redis >nul 2>&1
if %ERRORLEVEL% neq 0 (
    call :print_error "Redis service not found. Please install Redis as a Windows service."
    exit /b 1
)

sc query redis | findstr "RUNNING" >nul
if %ERRORLEVEL% neq 0 (
    echo Redis service is not running. Starting Redis...
    net start redis
    if %ERRORLEVEL% neq 0 (
        call :print_error "Failed to start Redis service. Please start it manually."
        exit /b 1
    )
    call :print_success "Redis service started"
) else (
    call :print_success "Redis service is running"
)

:: Check if start_all.py exists
call :print_status "Checking for start_all.py..."
if not exist start_all.py (
    call :print_error "start_all.py not found. Cannot start application."
    exit /b 1
)
call :print_success "Found start_all.py"

:: Add the project root to PYTHONPATH
set "PYTHONPATH=%PYTHONPATH%;%CD%"
call :print_success "PYTHONPATH updated"

:: Initialize database
call :print_status "Initializing database..."
if exist src\database\init_db.py (
    python src\database\init_db.py
    if %ERRORLEVEL% neq 0 (
        call :print_error "Failed to initialize database"
        exit /b 1
    )
    call :print_success "Database initialized"
) else (
    call :print_error "Database initialization script not found at src\database\init_db.py"
    call :print_status "Continuing without database initialization..."
)

:: All checks passed, start the application
call :print_status "All checks passed! Starting JPS Prospect Aggregate..."
echo ==========================================
python start_all.py

:: If the script exits, deactivate the conda environment
call conda deactivate
exit /b 0

:: ==========================================
:: Function Definitions
:: ==========================================

:print_status
echo.
echo %BLUE%📋 %~1%RESET%
exit /b 0

:print_success
echo %GREEN%✅ %~1%RESET%
exit /b 0

:print_error
echo %RED%❌ %~1%RESET%
exit /b 0 