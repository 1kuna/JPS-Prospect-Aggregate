@echo off
echo Starting JPS Prospect Aggregate with Celery...

:: Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found. Creating...
    python -m venv venv
    call venv\Scripts\activate
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

:: Start the application
python start_all.py

:: If the script exits, deactivate the virtual environment
call venv\Scripts\deactivate 