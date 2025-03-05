@echo off
setlocal enabledelayedexpansion

:: Create logs directory if it doesn't exist
if not exist logs mkdir logs

:: Set up log file with timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set mytime=%%a%%b)
set LOG_FILE=logs\jps_startup_%mydate%_%mytime%.log

:: Start logging - redirect all output to both console and log file
echo ==========================================
echo JPS Prospect Aggregate Auto-Setup ^& Launch
echo ==========================================
echo Logging to: %LOG_FILE%
echo Started at: %date% %time%
echo ==========================================

:: Log all output to file
call :ENABLE_LOGGING

:: Set colors for Windows console
set "GREEN=[92m"
set "RED=[91m"
set "BLUE=[94m"
set "YELLOW=[93m"
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
set "REDIS_INSTALLED=false"
set "REDIS_RUNNING=false"

:: Check if Redis is installed by looking for redis-server.exe
where redis-server >nul 2>&1
if %ERRORLEVEL% equ 0 (
    call :print_success "Redis is installed"
    set "REDIS_INSTALLED=true"
    
    :: Check if Redis service is running
    call :print_status "Checking if Redis service is running..."
    sc query redis >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        sc query redis | findstr "RUNNING" >nul
        if %ERRORLEVEL% equ 0 (
            call :print_success "Redis service is running"
            set "REDIS_RUNNING=true"
        ) else (
            call :print_warning "Redis service is installed but not running"
        )
    ) else (
        call :print_warning "Redis is installed but not configured as a Windows service"
    )
) else (
    call :print_warning "Redis is not installed"
)

:: Try to start Redis if it's installed but not running
if "%REDIS_INSTALLED%"=="true" if "%REDIS_RUNNING%"=="false" (
    call :print_status "Attempting to start Redis service..."
    sc query redis >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        net start redis
        if %ERRORLEVEL% neq 0 (
            call :print_error "Failed to start Redis service."
            call :print_warning "You can try starting Redis manually with: net start redis"
            call :print_warning "Continuing without Redis. Celery tasks will not work properly."
        ) else (
            call :print_success "Redis service started"
            set "REDIS_RUNNING=true"
        )
    ) else (
        call :print_warning "Redis is not configured as a Windows service."
        call :print_warning "Please install Redis as a Windows service or start it manually."
        call :print_warning "Continuing without Redis. Celery tasks will not work properly."
    )
)

:: If Redis is not installed, provide instructions
if "%REDIS_INSTALLED%"=="false" (
    call :print_warning "Redis is not installed on Windows."
    echo Please download and install Redis for Windows from: https://github.com/microsoftarchive/redis/releases
    echo After installation, please configure it as a Windows service.
    call :print_warning "Continuing without Redis. Celery tasks will not work properly."
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
if "%REDIS_RUNNING%"=="false" (
    call :print_warning "Redis is not running. Celery tasks will not work properly."
    call :print_warning "You may see errors related to Celery and Redis when the application starts."
)
echo ==========================================
echo Application starting at: %date% %time%
echo Log file: %LOG_FILE%
echo ==========================================
echo Starting application... >> "%LOG_FILE%"
python start_all.py >> "%LOG_FILE%" 2>&1

:: If the script exits, deactivate the conda environment
echo ==========================================
echo Application exited at: %date% %time%
echo ==========================================
call conda deactivate
exit /b 0

:: ==========================================
:: Function Definitions
:: ==========================================

:ENABLE_LOGGING
:: Save all previous output to log file
(
  echo ==========================================
  echo JPS Prospect Aggregate Auto-Setup ^& Launch
  echo ==========================================
  echo Logging to: %LOG_FILE%
  echo Started at: %date% %time%
  echo ==========================================
) > "%LOG_FILE%"
exit /b 0

:print_status
echo.
echo %BLUE%📋 %~1%RESET%
echo. >> "%LOG_FILE%"
echo 📋 %~1 >> "%LOG_FILE%"
exit /b 0

:print_success
echo %GREEN%✅ %~1%RESET%
echo ✅ %~1 >> "%LOG_FILE%"
exit /b 0

:print_error
echo %RED%❌ %~1%RESET%
echo ❌ %~1 >> "%LOG_FILE%"
exit /b 0

:print_warning
echo %YELLOW%⚠️ %~1%RESET%
echo ⚠️ %~1 >> "%LOG_FILE%"
exit /b 0 