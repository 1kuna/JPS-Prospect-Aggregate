import os
import pathlib
from typing import List, Dict, Any
from dotenv import load_dotenv

# Environment variables loading
load_dotenv()

# Base paths
BASE_DIR = pathlib.Path(__file__).parent.parent.absolute()
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')
ERROR_SCREENSHOTS_DIR = os.path.join(LOGS_DIR, 'error_screenshots')
ERROR_HTML_DIR = os.path.join(LOGS_DIR, 'error_html')

# Ensure directories exist (directly, without using file_utils to avoid circular imports)
for directory in [LOGS_DIR, DATA_DIR, RAW_DATA_DIR, TEMP_DIR, ERROR_SCREENSHOTS_DIR, ERROR_HTML_DIR]:
    os.makedirs(directory, exist_ok=True)

# Define all configuration variables at the module level
# Logging configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE_MAX_BYTES = int(os.getenv("LOG_FILE_MAX_BYTES", 5 * 1024 * 1024))  # 5MB
LOG_FILE_BACKUP_COUNT = int(os.getenv("LOG_FILE_BACKUP_COUNT", 3))  # Keep only 3 log files
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Scraper URLs
ACQUISITION_GATEWAY_URL = "https://acquisitiongateway.gov/forecast"
SSA_CONTRACT_FORECAST_URL = "https://www.ssa.gov/osdbu/contract-forecast-intro.html"
COMMERCE_FORECAST_URL = "https://www.commerce.gov/oam/industry/procurement-forecasts"
HHS_FORECAST_URL = "https://osdbu.hhs.gov/industry/opportunity-forecast"
DHS_FORECAST_URL = "https://apfs-cloud.dhs.gov/forecast/"
DOJ_FORECAST_URL = "https://www.justice.gov/jmd/doj-forecast-contracting-opportunities"
DOS_FORECAST_URL = "https://www.state.gov/procurement-forecast"
TREASURY_FORECAST_URL = "https://osdbu.forecast.treasury.gov/"
DOT_FORECAST_URL = "https://www.transportation.gov/osdbu/procurement-assistance/summary-forecast"

# Database configuration
# Use an absolute path for the SQLite database
DEFAULT_DB_PATH = os.path.join(BASE_DIR, 'jps.db')
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Scheduler configuration
SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", 24))
HEALTH_CHECK_INTERVAL_MINUTES = int(os.getenv("HEALTH_CHECK_INTERVAL_MINUTES", 10))

# AI data preservation configuration
PRESERVE_AI_DATA_ON_REFRESH = os.getenv("PRESERVE_AI_DATA_ON_REFRESH", "true").lower() == "true"

# File processing
CSV_ENCODINGS = ['utf-8', 'latin-1', 'cp1252']
FILE_FRESHNESS_SECONDS = int(os.getenv("FILE_FRESHNESS_SECONDS", 86400))   # 24 hours

# Playwright timeouts (in milliseconds)
PAGE_NAVIGATION_TIMEOUT = int(os.getenv("PAGE_NAVIGATION_TIMEOUT", 60000))  # 60 seconds
PAGE_ELEMENT_TIMEOUT = int(os.getenv("PAGE_ELEMENT_TIMEOUT", 30000))     # 30 seconds
TABLE_LOAD_TIMEOUT = int(os.getenv("TABLE_LOAD_TIMEOUT", 60000))       # 60 seconds
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", 60000))         # 60 seconds

# Application configuration
class Config:
    """Base configuration class with common settings."""
    # Flask settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", os.urandom(24).hex())
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 5001))
    
    # Directory paths
    BASE_DIR: str = BASE_DIR
    LOGS_DIR: str = LOGS_DIR
    DATA_DIR: str = DATA_DIR
    RAW_DATA_DIR: str = RAW_DATA_DIR
    TEMP_DIR: str = TEMP_DIR
    ERROR_SCREENSHOTS_DIR: str = ERROR_SCREENSHOTS_DIR
    ERROR_HTML_DIR: str = ERROR_HTML_DIR
    
    # Playwright timeouts (in milliseconds)
    PAGE_NAVIGATION_TIMEOUT: int = PAGE_NAVIGATION_TIMEOUT
    PAGE_ELEMENT_TIMEOUT: int = PAGE_ELEMENT_TIMEOUT
    TABLE_LOAD_TIMEOUT: int = TABLE_LOAD_TIMEOUT
    DOWNLOAD_TIMEOUT: int = DOWNLOAD_TIMEOUT

    # File processing
    CSV_ENCODINGS: List[str] = CSV_ENCODINGS
    FILE_FRESHNESS_SECONDS: int = FILE_FRESHNESS_SECONDS

    # Scraper URLs
    ACQUISITION_GATEWAY_URL: str = ACQUISITION_GATEWAY_URL
    SSA_CONTRACT_FORECAST_URL: str = SSA_CONTRACT_FORECAST_URL
    COMMERCE_FORECAST_URL: str = COMMERCE_FORECAST_URL
    HHS_FORECAST_URL: str = HHS_FORECAST_URL
    DHS_FORECAST_URL: str = DHS_FORECAST_URL
    DOJ_FORECAST_URL: str = DOJ_FORECAST_URL
    DOS_FORECAST_URL: str = DOS_FORECAST_URL
    TREASURY_FORECAST_URL: str = TREASURY_FORECAST_URL
    DOT_FORECAST_URL: str = DOT_FORECAST_URL

    # Logging configuration
    LOG_LEVEL: str = LOG_LEVEL
    LOG_FORMAT: str = LOG_FORMAT
    LOG_FILE_MAX_BYTES: int = LOG_FILE_MAX_BYTES
    LOG_FILE_BACKUP_COUNT: int = LOG_FILE_BACKUP_COUNT

    # Database configuration
    SQLALCHEMY_DATABASE_URI: str = DATABASE_URL

    # Scheduler configuration
    SCRAPE_INTERVAL_HOURS: int = SCRAPE_INTERVAL_HOURS
    HEALTH_CHECK_INTERVAL_MINUTES: int = HEALTH_CHECK_INTERVAL_MINUTES
    
    # AI data preservation configuration
    PRESERVE_AI_DATA_ON_REFRESH: bool = PRESERVE_AI_DATA_ON_REFRESH
    
    # Redis configuration
    REDIS_URL: str = REDIS_URL


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    # In production, you might want to use a more robust database


class TestingConfig(Config):
    """Testing configuration."""
    TESTING: bool = True
    DEBUG: bool = True
    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"


# Configuration dictionary
config_by_name: Dict[str, Any] = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Get current configuration based on environment
active_config = config_by_name[os.getenv('FLASK_ENV', 'default')]

# Export selected configuration variables
__all__ = [
    'active_config', 'BASE_DIR', 'LOGS_DIR', 'DATA_DIR', 'RAW_DATA_DIR'
] 