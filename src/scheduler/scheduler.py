import os
import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from src
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.scrapers.acquisition_gateway import run_scraper as run_acquisition_gateway_scraper
from src.scrapers.ssa_contract_forecast import run_scraper as run_ssa_contract_forecast_scraper
from src.scrapers.health_check import check_all_scrapers

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get scrape interval from environment or use default (24 hours)
SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", 24))
# Health check interval set to 10 minutes
HEALTH_CHECK_INTERVAL_MINUTES = 10

def start_scheduler():
    """Start the background scheduler for running scrapers"""
    logger.info("Starting scheduler")
    
    # Create scheduler
    scheduler = BackgroundScheduler()
    
    # Add jobs
    scheduler.add_job(
        run_acquisition_gateway_scraper,
        trigger=IntervalTrigger(hours=SCRAPE_INTERVAL_HOURS),
        id='acquisition_gateway_scraper',
        name='Acquisition Gateway Scraper',
        replace_existing=True
    )
    
    # Add the new SSA Contract Forecast scraper job
    scheduler.add_job(
        run_ssa_contract_forecast_scraper,
        trigger=IntervalTrigger(hours=SCRAPE_INTERVAL_HOURS),
        id='ssa_contract_forecast_scraper',
        name='SSA Contract Forecast Scraper',
        replace_existing=True
    )
    
    # Add health check job
    scheduler.add_job(
        check_all_scrapers,
        trigger=IntervalTrigger(minutes=HEALTH_CHECK_INTERVAL_MINUTES),
        id='health_check',
        name='Scraper Health Check',
        replace_existing=True
    )
    
    # Start the scheduler in a separate thread
    scheduler.start()
    logger.info(f"Scheduler started with scrape interval of {SCRAPE_INTERVAL_HOURS} hours and health check interval of {HEALTH_CHECK_INTERVAL_MINUTES} minutes")
    
    # Run scrapers immediately on startup
    run_initial_scrape()

def run_initial_scrape():
    """Run initial scrape on startup"""
    logger.info("Running initial scrape")
    
    # Run in separate threads to not block the main thread
    thread1 = threading.Thread(target=run_acquisition_gateway_scraper)
    thread1.daemon = True
    thread1.start()
    
    # Add the new SSA Contract Forecast scraper
    thread2 = threading.Thread(target=run_ssa_contract_forecast_scraper)
    thread2.daemon = True
    thread2.start()
    
    # Run initial health check
    thread3 = threading.Thread(target=check_all_scrapers)
    thread3.daemon = True
    thread3.start()

if __name__ == "__main__":
    start_scheduler() 