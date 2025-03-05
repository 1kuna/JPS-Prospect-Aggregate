import os
import pathlib

# Base paths
BASE_DIR = pathlib.Path(__file__).parent.parent.absolute()
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
DATA_DIR = os.path.join(BASE_DIR, 'data')
DOWNLOADS_DIR = os.path.join(DATA_DIR, 'downloads')

# Ensure directories exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Playwright timeouts (in milliseconds)
PAGE_NAVIGATION_TIMEOUT = 60000  # 60 seconds
PAGE_ELEMENT_TIMEOUT = 30000     # 30 seconds
TABLE_LOAD_TIMEOUT = 60000       # 60 seconds
DOWNLOAD_TIMEOUT = 60000         # 60 seconds

# File processing
CSV_ENCODINGS = ['utf-8', 'latin-1', 'cp1252']
FILE_FRESHNESS_SECONDS = 86400   # 24 hours

# Scraper URLs
ACQUISITION_GATEWAY_URL = "https://acquisitiongateway.gov/forecast"
SSA_CONTRACT_FORECAST_URL = "https://www.ssa.gov/oag/business/forecast.html"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024  # 5MB
LOG_FILE_BACKUP_COUNT = 3  # Keep only 3 log files (changed from 5)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///" + os.path.join(DATA_DIR, "proposals.db"))

# Scheduler configuration
SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", 24)) 