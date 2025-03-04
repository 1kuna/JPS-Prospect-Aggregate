@echo off
echo Setting up JPS Proposal Forecast Aggregator...

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo Initializing database...
python init_db.py

echo Setup complete!
echo.
echo To run the application:
echo 1. Activate the virtual environment: venv\Scripts\activate.bat
echo 2. Run the application: python app.py
echo.
pause 