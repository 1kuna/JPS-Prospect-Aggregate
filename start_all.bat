@echo off
setlocal enabledelayedexpansion

:: Get the project root directory
set PROJECT_ROOT=%~dp0
set PROJECT_ROOT=%PROJECT_ROOT:~0,-1%

:: Create logs directory if it doesn't exist
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"

:: Set up log file with timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set mytime=%%a%%b)
set LOG_FILE=%PROJECT_ROOT%\logs\jps_startup_%mydate%_%mytime%.log

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

:: Configuration options
set "HIDE_WINDOWS=false"  :: Set to "true" to completely hide process windows, "false" to show minimized windows

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

:: Check if Node.js and npm are installed
call :print_status "Checking for Node.js and npm installation..."
where node >nul 2>&1
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    call :print_warning "Node.js or npm is not installed. Vue.js frontend will not be available."
    echo You can download Node.js from: https://nodejs.org/
    set VUE_AVAILABLE=false
) else (
    for /f "tokens=*" %%a in ('node --version') do set NODE_VERSION=%%a
    for /f "tokens=*" %%a in ('npm --version') do set NPM_VERSION=%%a
    call :print_success "Node.js version %NODE_VERSION% and npm version %NPM_VERSION% are installed"
    set VUE_AVAILABLE=true
)

:: Get the environment variable for Vue dev mode
if "%VUE_DEV_MODE%"=="" (
    set VUE_DEV_MODE=true
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

:: Check for Memurai (Redis for Windows)
call :print_status "Checking Memurai installation..."
set "REDIS_INSTALLED=false"
set "REDIS_RUNNING=false"

:: Check if Memurai is installed by looking for the service
sc query Memurai >nul 2>&1
if %ERRORLEVEL% equ 0 (
    call :print_success "Memurai is installed as a Windows service"
    set "REDIS_INSTALLED=true"
    
    :: Check if Memurai service is running
    call :print_status "Checking if Memurai service is running..."
    sc query Memurai | findstr "RUNNING" >nul
    if %ERRORLEVEL% equ 0 (
        call :print_success "Memurai service is running"
        set "REDIS_RUNNING=true"
    ) else (
        call :print_warning "Memurai service is installed but not running"
        call :print_status "Attempting to start Memurai service..."
        net start Memurai
        if %ERRORLEVEL% neq 0 (
            call :print_error "Failed to start Memurai service."
            call :print_error "You may need to run this script as Administrator."
            call :print_error "Please start Memurai manually with: net start Memurai"
            call :print_error "Then run this script again."
            exit /b 1
        ) else (
            call :print_success "Memurai service started successfully"
            set "REDIS_RUNNING=true"
        )
    )
) else (
    :: Check if Memurai is installed in Program Files
    if exist "C:\Program Files\Memurai\*.*" (
        call :print_warning "Memurai is installed but not as a Windows service"
        
        :: Try to find the Memurai executable
        if exist "C:\Program Files\Memurai\memurai.exe" (
            call :print_status "Attempting to start Memurai manually..."
            start "" "C:\Program Files\Memurai\memurai.exe"
            timeout /t 5 /nobreak > nul
            call :print_success "Memurai started manually. Note: This will not persist after reboot."
            set "REDIS_INSTALLED=true"
            set "REDIS_RUNNING=true"
        ) else (
            call :print_error "Could not find Memurai executable."
            call :print_error "Please start Memurai manually and run this script again."
            exit /b 1
        )
    ) else (
        call :print_error "Memurai (Redis for Windows) is not installed."
        call :print_error "Celery requires Redis to function properly on Windows."
        call :print_error "Please download and install Memurai from: https://www.memurai.com/get-memurai"
        call :print_error "After installation, please run this script again."
        exit /b 1
    )
)

:: Check if Redis is accessible by trying to ping it
if "%REDIS_RUNNING%"=="true" (
    call :print_status "Testing connection to Memurai (Redis)..."
    python -c "import redis; r = redis.Redis(host='localhost', port=6379); print(r.ping())" >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        call :print_error "Failed to connect to Memurai (Redis) server."
        call :print_error "Please check that Memurai is running and accessible on port 6379."
        call :print_error "Then run this script again."
        exit /b 1
    ) else (
        call :print_success "Successfully connected to Memurai (Redis) server"
    )
)

:: Update .env file with Redis configuration if needed
call :print_status "Checking .env file for Redis configuration..."
if exist .env (
    type .env | findstr "REDIS_URL" >nul
    if %ERRORLEVEL% neq 0 (
        call :print_status "Adding Redis configuration to .env file..."
        echo. >> .env
        echo # Celery settings (using Memurai as Redis-compatible server on Windows) >> .env
        echo REDIS_URL=redis://localhost:6379/0 >> .env
        echo CELERY_BROKER_URL=redis://localhost:6379/0 >> .env
        echo CELERY_RESULT_BACKEND=redis://localhost:6379/0 >> .env
        call :print_success "Redis configuration added to .env file"
    ) else (
        call :print_success "Redis configuration already exists in .env file"
    )
) else (
    call :print_warning ".env file not found. Attempting to create it..."
    if exist .env.example (
        copy .env.example .env
        call :print_success "Created .env file from .env.example"
        
        :: Check if Redis configuration exists in the new .env file
        type .env | findstr "REDIS_URL" >nul
        if %ERRORLEVEL% neq 0 (
            call :print_status "Adding Redis configuration to .env file..."
            echo. >> .env
            echo # Celery settings (using Memurai as Redis-compatible server on Windows) >> .env
            echo REDIS_URL=redis://localhost:6379/0 >> .env
            echo CELERY_BROKER_URL=redis://localhost:6379/0 >> .env
            echo CELERY_RESULT_BACKEND=redis://localhost:6379/0 >> .env
            call :print_success "Redis configuration added to .env file"
        )
    ) else (
        call :print_warning ".env.example file not found. Creating a basic .env file..."
        (
            echo # Application settings
            echo HOST=0.0.0.0
            echo PORT=5001
            echo DEBUG=False
            echo.
            echo # Database settings
            echo DATABASE_URL=sqlite:///data/proposals.db
            echo SQL_ECHO=False
            echo.
            echo # Scheduler settings
            echo SCRAPE_INTERVAL_HOURS=24
            echo HEALTH_CHECK_INTERVAL_MINUTES=10
            echo.
            echo # Celery settings (using Memurai as Redis-compatible server on Windows)
            echo REDIS_URL=redis://localhost:6379/0
            echo CELERY_BROKER_URL=redis://localhost:6379/0
            echo CELERY_RESULT_BACKEND=redis://localhost:6379/0
            echo.
            echo # Vue.js settings
            echo VUE_DEV_MODE=True
        ) > .env
        call :print_success "Created a basic .env file with default settings"
    )
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

:: Initialize Vue.js availability flag
set "VUE_AVAILABLE=false"

:: Check if Vue.js dev mode is enabled in .env
type .env | findstr "VUE_DEV_MODE=True" >nul
if %ERRORLEVEL% equ 0 (
    set "VUE_DEV_MODE=true"
) else (
    set "VUE_DEV_MODE=false"
)

:: Build Vue.js frontend if not in dev mode
if "%VUE_DEV_MODE%"=="false" (
    call :build_vue_frontend
) else (
    :: Check if Vue.js frontend exists
    if exist src\dashboard\frontend\package.json (
        set "VUE_AVAILABLE=true"
    )
)

:: Start the application components
call :print_status "Starting application components..."

:: Start Flask app
echo.
echo Starting Flask app...
:: Use window visibility based on configuration
if "%HIDE_WINDOWS%"=="true" (
    start /b "" cmd /c "python app.py > "%PROJECT_ROOT%\logs\flask.log" 2>&1"
    for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /fo list ^| findstr "PID:"') do (
        set FLASK_PID=%%a
        echo Flask app started with PID: !FLASK_PID!
    )
) else (
    start /min "Flask App" cmd /c "python app.py > "%PROJECT_ROOT%\logs\flask.log" 2>&1"
    echo Flask app started
)

:: Give Flask app time to start
timeout /t 2 /nobreak > nul

:: Start Celery worker if Memurai is available
if "%REDIS_RUNNING%"=="true" (
    echo.
    echo Starting Celery worker...
    :: Use window visibility based on configuration
    if "%HIDE_WINDOWS%"=="true" (
        start /b "" cmd /c "celery -A src.celery_app worker --loglevel=info > "%PROJECT_ROOT%\logs\celery_worker.log" 2>&1"
        for /f "tokens=2" %%a in ('tasklist /fi "imagename eq celery.exe" /fo list ^| findstr "PID:"') do (
            set WORKER_PID=%%a
            echo Celery worker started with PID: !WORKER_PID!
        )
    ) else (
        start /min "Celery Worker" cmd /c "celery -A src.celery_app worker --loglevel=info > "%PROJECT_ROOT%\logs\celery_worker.log" 2>&1"
        echo Celery worker started
    )
    
    echo.
    echo Starting Celery beat...
    if "%HIDE_WINDOWS%"=="true" (
        start /b "" cmd /c "celery -A src.celery_app beat --loglevel=info > "%PROJECT_ROOT%\logs\celery_beat.log" 2>&1"
        for /f "tokens=2" %%a in ('tasklist /fi "imagename eq celery.exe" /fo list ^| findstr "PID:" ^| findstr /v "!WORKER_PID!"') do (
            set BEAT_PID=%%a
            echo Celery beat started with PID: !BEAT_PID!
        )
    ) else (
        start /min "Celery Beat" cmd /c "celery -A src.celery_app beat --loglevel=info > "%PROJECT_ROOT%\logs\celery_beat.log" 2>&1"
        echo Celery beat started
    )
    
    echo.
    echo Starting Flower monitoring...
    if "%HIDE_WINDOWS%"=="true" (
        start /b "" cmd /c "celery -A src.celery_app flower --port=5555 > "%PROJECT_ROOT%\logs\flower.log" 2>&1"
        for /f "tokens=2" %%a in ('tasklist /fi "imagename eq celery.exe" /fo list ^| findstr "PID:" ^| findstr /v "!WORKER_PID!" ^| findstr /v "!BEAT_PID!"') do (
            set FLOWER_PID=%%a
            echo Flower started with PID: !FLOWER_PID!
        )
    ) else (
        start /min "Flower" cmd /c "celery -A src.celery_app flower --port=5555 > "%PROJECT_ROOT%\logs\flower.log" 2>&1"
        echo Flower started
    )
)

:: Start Vue.js development server if in dev mode
if "%VUE_DEV_MODE%"=="true" if "%VUE_AVAILABLE%"=="true" (
    echo.
    echo Starting Vue.js development server...
    cd src\dashboard\frontend
    if "%HIDE_WINDOWS%"=="true" (
        start /b "" cmd /c "npm run serve > "%PROJECT_ROOT%\logs\vue.log" 2>&1"
        :: Wait a moment for the process to start
        timeout /t 2 /nobreak > nul
        for /f "tokens=2" %%a in ('tasklist /fi "imagename eq node.exe" /fo list ^| findstr "PID:"') do (
            set VUE_PID=%%a
            echo Vue.js development server started with PID: !VUE_PID!
        )
    ) else (
        start /min "Vue.js Dev Server" cmd /c "npm run serve > "%PROJECT_ROOT%\logs\vue.log" 2>&1"
        echo Vue.js development server started
    )
    cd ..\..\..
) else if "%VUE_DEV_MODE%"=="false" if "%VUE_AVAILABLE%"=="true" (
    :: Build Vue.js frontend for production
    call :build_vue_frontend
)

:: Print success message
call :print_status "All services started!"
echo - Flask app running at http://localhost:5001
if "%REDIS_RUNNING%"=="true" (
    echo - Celery worker processing tasks
    echo - Celery beat scheduling tasks
    echo - Flower monitoring available at http://localhost:5555
)
if "%VUE_DEV_MODE%"=="true" if "%VUE_AVAILABLE%"=="true" (
    echo - Vue.js development server running at http://localhost:8080
)

echo.
echo Press any key to stop all services and exit...
echo.

:: Keep the script running until interrupted
pause

:: When the user presses a key, clean up and exit
call :print_status "Stopping all services..."

:: Different cleanup based on window visibility
if "%HIDE_WINDOWS%"=="true" (
    :: For hidden windows, we can use the saved PIDs if available
    echo Stopping Flask app...
    if defined FLASK_PID (
        taskkill /PID !FLASK_PID! /F > nul 2>&1
    ) else (
        taskkill /FI "IMAGENAME eq python.exe" /F > nul 2>&1
    )
    
    if "%REDIS_RUNNING%"=="true" (
        echo Stopping Celery worker...
        if defined WORKER_PID (
            taskkill /PID !WORKER_PID! /F > nul 2>&1
        )
        
        echo Stopping Celery beat...
        if defined BEAT_PID (
            taskkill /PID !BEAT_PID! /F > nul 2>&1
        )
        
        echo Stopping Flower...
        if defined FLOWER_PID (
            taskkill /PID !FLOWER_PID! /F > nul 2>&1
        )
        
        :: Fallback in case PIDs weren't captured correctly
        taskkill /FI "IMAGENAME eq celery.exe" /F > nul 2>&1
    )
    
    if "%VUE_DEV_MODE%"=="true" if "%VUE_AVAILABLE%"=="true" (
        echo Stopping Vue.js development server...
        if defined VUE_PID (
            taskkill /PID !VUE_PID! /F > nul 2>&1
        ) else (
            :: This might kill other node processes too, so be careful
            taskkill /FI "IMAGENAME eq node.exe" /F > nul 2>&1
        )
    )
) else (
    :: For visible windows, we can kill by window title
    echo Stopping Flask app...
    taskkill /FI "WINDOWTITLE eq Flask App" /F > nul 2>&1
    
    if "%REDIS_RUNNING%"=="true" (
        echo Stopping Celery worker...
        taskkill /FI "WINDOWTITLE eq Celery Worker" /F > nul 2>&1
        
        echo Stopping Celery beat...
        taskkill /FI "WINDOWTITLE eq Celery Beat" /F > nul 2>&1
        
        echo Stopping Flower...
        taskkill /FI "WINDOWTITLE eq Flower" /F > nul 2>&1
    )
    
    if "%VUE_DEV_MODE%"=="true" if "%VUE_AVAILABLE%"=="true" (
        echo Stopping Vue.js development server...
        taskkill /FI "WINDOWTITLE eq Vue.js Dev Server" /F > nul 2>&1
    )
)

call :print_success "All services stopped"

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

:: Function to build Vue.js frontend for production
:build_vue_frontend
call :print_status "Building Vue.js frontend for production..."

:: Check if frontend directory exists
if not exist src\dashboard\frontend (
    call :print_warning "Vue.js frontend directory not found at src\dashboard\frontend"
    call :print_warning "Continuing without Vue.js frontend..."
    set "VUE_AVAILABLE=false"
    exit /b 1
)

:: Navigate to the frontend directory
cd src\dashboard\frontend

:: Check if package.json exists
if not exist package.json (
    call :print_warning "package.json not found in frontend directory"
    cd ..\..\..
    call :print_warning "Continuing without Vue.js frontend..."
    set "VUE_AVAILABLE=false"
    exit /b 1
)

:: Check if node_modules exists, if not run npm install
if not exist node_modules (
    call :print_status "Installing Vue.js dependencies..."
    call npm install
    if %ERRORLEVEL% neq 0 (
        call :print_error "Failed to install Vue.js dependencies"
        cd ..\..\..
        call :print_warning "Continuing without Vue.js frontend..."
        set "VUE_AVAILABLE=false"
        exit /b 1
    )
)

:: Check if @vue/cli-service is installed
call npm list @vue/cli-service >nul 2>&1
if %ERRORLEVEL% neq 0 (
    call :print_status "Installing @vue/cli-service..."
    call npm install @vue/cli-service --save-dev
    if %ERRORLEVEL% neq 0 (
        call :print_error "Failed to install @vue/cli-service"
        cd ..\..\..
        call :print_warning "Continuing without Vue.js frontend..."
        set "VUE_AVAILABLE=false"
        exit /b 1
    )
)

:: Build the Vue.js app
call npm run build
if %ERRORLEVEL% neq 0 (
    call :print_error "Failed to build Vue.js frontend"
    cd ..\..\..
    call :print_warning "Continuing without Vue.js frontend..."
    set "VUE_AVAILABLE=false"
    exit /b 1
)

:: Ensure the static/vue directory exists
if not exist ..\static\vue mkdir ..\static\vue

:: Return to the original directory
cd ..\..\..

call :print_success "Vue.js frontend built successfully!"
set "VUE_AVAILABLE=true"
exit /b 0 