import os
import pathlib
from typing import List, Dict, Any, Optional

# Base paths
BASE_DIR = pathlib.Path(__file__).parent.parent.absolute()
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
DATA_DIR = os.path.join(BASE_DIR, 'data')
DOWNLOADS_DIR = os.path.join(DATA_DIR, 'downloads')

# Ensure directories exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Application configuration
class Config:
    """Base configuration class with common settings."""
    # Flask settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", os.urandom(24).hex())
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 5001))
    
    # Playwright timeouts (in milliseconds)
    PAGE_NAVIGATION_TIMEOUT: int = int(os.getenv("PAGE_NAVIGATION_TIMEOUT", 60000))  # 60 seconds
    PAGE_ELEMENT_TIMEOUT: int = int(os.getenv("PAGE_ELEMENT_TIMEOUT", 30000))     # 30 seconds
    TABLE_LOAD_TIMEOUT: int = int(os.getenv("TABLE_LOAD_TIMEOUT", 60000))       # 60 seconds
    DOWNLOAD_TIMEOUT: int = int(os.getenv("DOWNLOAD_TIMEOUT", 60000))         # 60 seconds

    # File processing
    CSV_ENCODINGS: List[str] = ['utf-8', 'latin-1', 'cp1252']
    FILE_FRESHNESS_SECONDS: int = int(os.getenv("FILE_FRESHNESS_SECONDS", 86400))   # 24 hours

    # Scraper URLs
    ACQUISITION_GATEWAY_URL: str = os.getenv("ACQUISITION_GATEWAY_URL", "https://acquisitiongateway.gov/forecast")
    SSA_CONTRACT_FORECAST_URL: str = os.getenv("SSA_CONTRACT_FORECAST_URL", "https://www.ssa.gov/oag/business/forecast.html")

    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE_MAX_BYTES: int = int(os.getenv("LOG_FILE_MAX_BYTES", 5 * 1024 * 1024))  # 5MB
    LOG_FILE_BACKUP_COUNT: int = int(os.getenv("LOG_FILE_BACKUP_COUNT", 3))  # Keep only 3 log files

    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(DATA_DIR, 'proposals.db')}")

    # Scheduler configuration
    SCRAPE_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_INTERVAL_HOURS", 24))
    HEALTH_CHECK_INTERVAL_MINUTES: int = int(os.getenv("HEALTH_CHECK_INTERVAL_MINUTES", 10))
    
    # Redis configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    # In production, you might want to use a more robust database
    # DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")


class TestingConfig(Config):
    """Testing configuration."""
    TESTING: bool = True
    DEBUG: bool = True
    # Use in-memory SQLite for testing
    DATABASE_URL: str = "sqlite:///:memory:"


# Configuration dictionary
config_by_name: Dict[str, Any] = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Get current configuration based on environment
active_config = config_by_name[os.getenv('FLASK_ENV', 'default')]

# For backward compatibility with existing code
PAGE_NAVIGATION_TIMEOUT = active_config.PAGE_NAVIGATION_TIMEOUT
PAGE_ELEMENT_TIMEOUT = active_config.PAGE_ELEMENT_TIMEOUT
TABLE_LOAD_TIMEOUT = active_config.TABLE_LOAD_TIMEOUT
DOWNLOAD_TIMEOUT = active_config.DOWNLOAD_TIMEOUT
CSV_ENCODINGS = active_config.CSV_ENCODINGS
FILE_FRESHNESS_SECONDS = active_config.FILE_FRESHNESS_SECONDS
ACQUISITION_GATEWAY_URL = active_config.ACQUISITION_GATEWAY_URL
SSA_CONTRACT_FORECAST_URL = active_config.SSA_CONTRACT_FORECAST_URL
LOG_LEVEL = active_config.LOG_LEVEL
LOG_FORMAT = active_config.LOG_FORMAT
LOG_FILE_MAX_BYTES = active_config.LOG_FILE_MAX_BYTES
LOG_FILE_BACKUP_COUNT = active_config.LOG_FILE_BACKUP_COUNT
DATABASE_URL = active_config.DATABASE_URL
SCRAPE_INTERVAL_HOURS = active_config.SCRAPE_INTERVAL_HOURS
HEALTH_CHECK_INTERVAL_MINUTES = active_config.HEALTH_CHECK_INTERVAL_MINUTES
REDIS_URL = active_config.REDIS_URL 