import os
import pathlib
from typing import List, Dict, Type # Changed Any to Type
from dotenv import load_dotenv

# Environment variables loading
load_dotenv()

# Base paths
BASE_DIR = pathlib.Path(__file__).parent.parent.absolute()
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

# Ensure directories exist (directly, without using file_utils to avoid circular imports)
for directory in [LOGS_DIR, DATA_DIR, RAW_DATA_DIR, TEMP_DIR]:
    os.makedirs(directory, exist_ok=True)

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
    
    # Logging configuration
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE_MAX_BYTES: int = int(os.getenv("LOG_FILE_MAX_BYTES", 5 * 1024 * 1024))
    LOG_FILE_BACKUP_COUNT: int = int(os.getenv("LOG_FILE_BACKUP_COUNT", 3))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Scraper URLs
    ACQUISITION_GATEWAY_URL: str = os.getenv("ACQUISITION_GATEWAY_URL", "https://acquisitiongateway.gov/forecast")
    SSA_CONTRACT_FORECAST_URL: str = os.getenv("SSA_CONTRACT_FORECAST_URL", "https://www.ssa.gov/osdbu/contract-forecast-intro.html")
    COMMERCE_FORECAST_URL: str = os.getenv("COMMERCE_FORECAST_URL", "https://www.commerce.gov/oam/industry/procurement-forecasts")
    HHS_FORECAST_URL: str = os.getenv("HHS_FORECAST_URL", "https://osdbu.hhs.gov/industry/opportunity-forecast")
    DHS_FORECAST_URL: str = os.getenv("DHS_FORECAST_URL", "https://apfs-cloud.dhs.gov/forecast/")
    DOJ_FORECAST_URL: str = os.getenv("DOJ_FORECAST_URL", "https://www.justice.gov/jmd/doj-forecast-contracting-opportunities")
    DOS_FORECAST_URL: str = os.getenv("DOS_FORECAST_URL", "https://www.state.gov/procurement-forecast")
    TREASURY_FORECAST_URL: str = os.getenv("TREASURY_FORECAST_URL", "https://osdbu.forecast.treasury.gov/")
    DOT_FORECAST_URL: str = os.getenv("DOT_FORECAST_URL", "https://www.transportation.gov/osdbu/procurement-assistance/summary-forecast")

    # Database configuration
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'jps.db')}")

    # Redis configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Scheduler configuration
    SCRAPE_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_INTERVAL_HOURS", 24))
    HEALTH_CHECK_INTERVAL_MINUTES: int = int(os.getenv("HEALTH_CHECK_INTERVAL_MINUTES", 10))

    # File processing
    CSV_ENCODINGS: List[str] = ['utf-8', 'latin-1', 'cp1252']
    FILE_FRESHNESS_SECONDS: int = int(os.getenv("FILE_FRESHNESS_SECONDS", 86400))

    # Playwright timeouts (in milliseconds)
    PAGE_NAVIGATION_TIMEOUT: int = int(os.getenv("PAGE_NAVIGATION_TIMEOUT", 60000))
    PAGE_ELEMENT_TIMEOUT: int = int(os.getenv("PAGE_ELEMENT_TIMEOUT", 30000))
    TABLE_LOAD_TIMEOUT: int = int(os.getenv("TABLE_LOAD_TIMEOUT", 60000))
    DOWNLOAD_TIMEOUT: int = int(os.getenv("DOWNLOAD_TIMEOUT", 60000))


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG: bool = False
    # LOG_LEVEL: str = "INFO" # Inherits from Config, which defaults to "INFO"
    # In production, you might want to use a more robust database


class TestingConfig(Config):
    """Testing configuration."""
    TESTING: bool = True
    DEBUG: bool = True
    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"


def get_config() -> Config:
    """
    Factory function to get the appropriate configuration instance 
    based on the FLASK_ENV environment variable.
    """
    env = os.getenv('FLASK_ENV', 'development')
    # Using Type for class references, Dict[str, Type[Config]]
    config_classes: Dict[str, Type[Config]] = { 
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
        'default': DevelopmentConfig  # Fallback to development
    }
    config_class = config_classes.get(env, DevelopmentConfig) # .get for safety
    return config_class()


# Instantiate the current configuration
current_config = get_config()


# Export selected configuration variables
__all__ = [
    'current_config', 
    'get_config', 
    'Config', 
    'DevelopmentConfig', 
    'ProductionConfig', 
    'TestingConfig'
] 