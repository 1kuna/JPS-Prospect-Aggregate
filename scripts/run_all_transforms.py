import os
import sys
import logging
import time
from pathlib import Path

# --- Path Setup ---
# Add the project root directory to the Python path
# Assumes the script is in the 'scripts' directory, adjust if needed
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# --- End Path Setup ---

# --- Import Database Components ---
# Import necessary components after ORM consolidation
from app import create_app # To create an app context
from app.models import db    # The Flask-SQLAlchemy instance
# try: # Old imports removed
#     from app.database.session import engine # Get the configured engine
#     from app.database.models import Base    # Get the base class for models
# except ImportError as e:
#     logging.basicConfig() # Ensure logging is configured even if imports fail early
#     logging.error(f"Failed to import database components (engine, Base): {e}", exc_info=True)
#     logging.error("Ensure database session and models are correctly defined.")
#     sys.exit(1)
# --- End DB Imports ---

# --- Logging Setup ---
# Use a basic configuration for this script
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.propagate = False # Prevent double logging if root logger is also configured

# --- Silence SQLAlchemy INFO logs which can be verbose ---
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
# --- End Logging Setup ---

# --- Import Transformation Functions ---
# Import functions dynamically or explicitly. Explicit is clearer.
try:
    from app.core.transform.acqg_transform import transform_acquisition_gateway
    from app.core.transform.doc_transform import transform_doc
    from app.core.transform.doj_transform import transform_doj
    from app.core.transform.dos_transform import transform_dos
    from app.core.transform.dot_transform import transform_dot
    from app.core.transform.dhs_transform import transform_dhs
    from app.core.transform.hhs_transform import transform_hhs
    from app.core.transform.ssa_transform import transform_ssa
    from app.core.transform.treasury_transform import transform_treasury
except ImportError as e:
    logger.error(f"Failed to import transformation functions: {e}", exc_info=True)
    logger.error("Ensure the script is run from the project root or the Python path is correctly set.")
    sys.exit(1)
# --- End Imports ---


def run_single_transform(transform_func):
    """Runs a single transformation function and logs the outcome."""
    start_time = time.time()
    func_name = transform_func.__name__
    source_name = func_name.replace('transform_', '').upper() # Derive source name
    logger.info(f"--- Running Transformation: {source_name} ---")
    
    try:
        result_df = transform_func()
        duration = time.time() - start_time
        if result_df is not None:
            logger.info(f"--- Completed {source_name} in {duration:.2f}s. Processed {len(result_df)} rows. ---")
            return True, len(result_df)
        else:
            # Function completed but returned None (e.g., no file found, empty file)
            logger.warning(f"--- {source_name} transform completed but returned None (check logs for details). Duration: {duration:.2f}s ---")
            return True, 0 # Indicate completion, 0 rows processed
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"--- !!! FAILED {source_name} transform after {duration:.2f}s: {e} !!! ---", exc_info=True)
        return False, 0 # Indicate failure


def main():
    """Main function to run all transformations sequentially."""
    
    app = create_app() # Create a Flask app instance
    with app.app_context(): # Push an application context
        # --- Ensure Database Tables Exist ---
        logger.info("Checking and creating database tables if necessary...")
        try:
            # engine is now db.engine, and Base.metadata is db.metadata
            db.create_all() # Creates tables based on models registered with db
            logger.info("Database tables checked/created successfully.")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}", exc_info=True)
            sys.exit(1)
        # --- End Table Creation ---
    
    logger.info(">>> Starting all data transformations <<<")
    overall_start_time = time.time()
    
    transformations = [
        transform_acquisition_gateway,
        transform_doc,
        transform_doj,
        transform_dos,
        transform_dot,
        transform_dhs,
        transform_hhs,
        transform_ssa,
        transform_treasury,
    ]
    
    success_count = 0
    failure_count = 0
    total_rows_processed = 0
    
    for func in transformations:
        success, rows_processed = run_single_transform(func)
        if success:
            success_count += 1
            total_rows_processed += rows_processed
        else:
            failure_count += 1
            
    overall_duration = time.time() - overall_start_time
    logger.info(">>> All transformations finished <<<")
    logger.info(f"Summary: Success={success_count}, Failure={failure_count}, Total Rows Processed={total_rows_processed}")
    logger.info(f"Total execution time: {overall_duration:.2f}s")

if __name__ == "__main__":
    main() 