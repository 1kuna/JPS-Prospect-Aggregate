import pandas as pd
import hashlib
import os
import sys
from pathlib import Path

# Add project root to sys.path to allow absolute imports
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

import logging
import re
from datetime import datetime
from app.utils.parsing import parse_value_range, split_place
from app.database.crud import bulk_upsert_prospects # Import the upsert function

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the base data directory
try:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
except NameError:
    BASE_DIR = Path('.').resolve()

# Specific data directory for SSA
DATA_DIR = BASE_DIR / "data" / "raw" / "ssa_forecast"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# Hardcoded canonical columns
CANONICAL_COLUMNS = [
    'source', 'native_id', 'requirement_title', 'requirement_description',
    'naics', 'estimated_value', 'est_value_unit', 'solicitation_date',
    'award_date', 'office', 'place_city', 'place_state', 'place_country',
    'contract_type', 'set_aside', 'loaded_at', 'extra', 'id'
]

# --- Helper Functions (Potentially reusable) ---

def find_latest_raw_file(data_dir: Path) -> Path | None:
    """Finds the most recently modified file (Excel or CSV) in the directory."""
    try:
        # Include .xlsm for SSA
        excel_files = list(data_dir.glob('*.xlsx')) + list(data_dir.glob('*.xlsm'))
        csv_files = list(data_dir.glob('*.csv'))
        files = excel_files + csv_files
        if not files:
            logging.warning(f"No Excel or CSV files found in {data_dir}")
            return None
        latest_file = max(files, key=os.path.getmtime)
        logging.info(f"Found latest file: {latest_file}")
        return latest_file
    except FileNotFoundError:
        logging.error(f"Data directory not found: {data_dir}")
        return None
    except Exception as e:
        logging.error(f"Error finding latest file in {data_dir}: {e}")
        return None

def generate_id(row: pd.Series) -> str:
    """Generates an MD5 hash for the row based on key fields."""
    naics = str(row.get('naics', ''))
    title = str(row.get('requirement_title', ''))
    desc = str(row.get('requirement_description', ''))
    unique_string = f"{naics}-{title}-{desc}"
    return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

# --- Normalization Function (SSA specific) ---

def normalize_columns_ssa(df: pd.DataFrame, canonical_cols: list[str]) -> pd.DataFrame:
    """Renames SSA columns, normalizes, handles extras."""
    # Define the explicit mapping for SSA from Excel header
    rename_map = {
        'APP #': 'native_id',
        'SITE Type': 'office',
        'REQUIREMENT TYPE': 'requirement_type',
        'DESCRIPTION': 'requirement_title',
        'EST COST PER FY': 'estimated_value_raw', # Rename raw
        'PLANNED AWARD DATE': 'award_date',
        'CONTRACT TYPE': 'contract_type',
        'NAICS': 'naics',
        'TYPE OF COMPETITION': 'set_aside',
        'PLACE OF PERFORMANCE': 'place_raw' # Rename raw
    }
    logging.info(f"Applying SSA specific column mapping: {rename_map}")
    # Filter DataFrame to only columns that exist before renaming 
    existing_raw_cols = [col for col in rename_map.keys() if col in df.columns]
    df = df[existing_raw_cols]
    df = df.rename(columns=rename_map)

    # --- Parsing Logic --- 
    if 'place_raw' in df.columns:
        logging.info("Splitting 'place_raw'.")
        split_places = df['place_raw'].apply(split_place)
        df['place_city'] = split_places.apply(lambda x: x[0])
        df['place_state'] = split_places.apply(lambda x: x[1])
        df['place_country'] = 'USA' # Assume USA
    else:
        df['place_city'], df['place_state'], df['place_country'] = pd.NA, pd.NA, 'USA'

    if 'estimated_value_raw' in df.columns:
        logging.info("Parsing 'estimated_value_raw'.")
        # Cost seems per FY, might need adjustments later if total value is needed
        parsed_values = df['estimated_value_raw'].apply(parse_value_range)
        df['estimated_value'] = parsed_values.apply(lambda x: x[0])
        df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
        if df['est_value_unit'].isnull().all(): # If all units are None after parse
            df['est_value_unit'] = df['est_value_unit'].fillna('Per FY') # Indicate original context
        elif df['est_value_unit'].notnull().any():
             df['est_value_unit'] = df['est_value_unit'].astype(str) + ' (Per FY)' # Append context
        else:
             df['est_value_unit'] = 'Per FY'
    else:
        df['estimated_value'], df['est_value_unit'] = pd.NA, pd.NA

    if 'award_date' in df.columns:
        logging.info("Parsing 'award_date'.")
        df['award_date'] = pd.to_datetime(df['award_date'], errors='coerce')
    else:
        df['award_date'] = pd.NaT

    # Initialize missing columns that weren't directly mapped
    # requirement_description is no longer directly mapped, will be handled below
    df['solicitation_date'] = pd.NaT
    
    # Drop raw columns
    cols_to_drop = ['place_raw', 'estimated_value_raw']
    df = df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore')

    # --- General normalization (lowercase, snake_case) ---
    df.columns = df.columns.str.strip().str.lower().str.replace(r'\s+\(.*?\)', '', regex=True).str.replace(r'\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)

    # --- Handle Extra/Canonical Columns ---
    current_cols = df.columns.tolist()
    normalized_canonical = [c.strip().lower().replace(' ', '_').replace(r'[^a-z0-9_]', '') for c in canonical_cols]
    # Note: SSA starts by selecting specific columns, so unmapped should be minimal
    unmapped_cols = [col for col in current_cols if col not in normalized_canonical and col not in ['source', 'id']]
    if unmapped_cols:
        logging.warning(f"Unexpected unmapped columns found for SSA: {unmapped_cols}") # Should ideally not happen
        df['extra'] = df[unmapped_cols].astype(str).to_dict(orient='records')
        df = df.drop(columns=unmapped_cols)
    else:
        df['extra'] = None
    for col in normalized_canonical:
        if col not in df.columns:
           df[col] = pd.NA

    final_cols_order = [col for col in normalized_canonical if col in df.columns]
    return df[final_cols_order]

# --- Main Transformation Function ---

def transform_ssa() -> pd.DataFrame | None:
    """Transforms the latest SSA forecast raw data."""
    canonical_cols = CANONICAL_COLUMNS
    latest_file = find_latest_raw_file(DATA_DIR)
    if not latest_file:
        logging.error(f"No raw data file found for SSA in {DATA_DIR}")
        return None

    try:
        if latest_file.suffix in ['.xlsx', '.xlsm']:
            # Read from 'Sheet1', header is on row 5 (index 4)
            # Specify engine='openpyxl' if default has issues with .xlsm
            df = pd.read_excel(latest_file, sheet_name='Sheet1', header=4, engine='openpyxl')
            logging.info(f"Loaded {len(df)} rows from Excel file {latest_file}, sheet 'Sheet1'")
        elif latest_file.suffix == '.csv':
            # TODO: Determine correct header row and if on_bad_lines is needed for SSA CSV
            df = pd.read_csv(latest_file, header=0, on_bad_lines='skip')
            logging.info(f"Loaded {len(df)} rows from CSV file {latest_file}")
        else:
            logging.error(f"Unsupported file type: {latest_file.suffix}")
            return None

        if df.empty:
            logging.warning(f"Loaded DataFrame is empty from {latest_file}")
            return df

        # --- Pre-processing --- 
        df.dropna(how='all', inplace=True)

        # Normalize columns
        df_normalized = normalize_columns_ssa(df.copy(), canonical_cols)

        # Add source column
        df_normalized['source'] = 'SSA'

        # Add id column
        df_normalized['id'] = df_normalized.apply(generate_id, axis=1)

        # Reorder columns
        final_ordered_cols = []
        if 'source' in df_normalized.columns: final_ordered_cols.append('source')
        if 'native_id' in df_normalized.columns: final_ordered_cols.append('native_id')
        final_ordered_cols.append('id')
        final_ordered_cols.extend([col for col in df_normalized.columns if col not in ['source', 'native_id', 'id']])
        if 'extra' in final_ordered_cols:
             final_ordered_cols.remove('extra')
             final_ordered_cols.append('extra')
        
        df_final = df_normalized[[col for col in final_ordered_cols if col in df_normalized.columns]]

        logging.info(f"SSA Transformation complete. Processed {len(df_final)} rows.")

        # TEMPORARY EXPORT CODE - COMMENTED OUT
        # export_path = os.path.join('data', 'processed', 'ssa.csv')
        # os.makedirs(os.path.dirname(export_path), exist_ok=True)
        # df_final.to_csv(export_path, index=False)
        # logging.info(f"Temporarily exported data to {export_path}")
        # END TEMPORARY EXPORT CODE

        # Upsert data to database
        try:
            logging.info(f"Attempting to upsert {len(df_final)} records for SSA.")
            bulk_upsert_prospects(df_final)
            logging.info(f"Successfully upserted SSA data.")
        except Exception as db_error:
            logging.error(f"Database upsert failed for SSA: {db_error}", exc_info=True)
            # Optionally return None or re-raise

        return df_final

    except pd.errors.EmptyDataError:
        logging.error(f"Raw data file is empty: {latest_file}")
        return None
    except FileNotFoundError:
         logging.error(f"File not found during processing: {latest_file}")
         return None
    except Exception as e:
        logging.error(f"Error during transformation of {latest_file}: {e}", exc_info=True)
        return None

# Example usage
if __name__ == "__main__":
    transformed_data = transform_ssa()
    if transformed_data is not None:
        print(transformed_data.head())
        print(f"\nTransformed DataFrame shape: {transformed_data.shape}")
        print(f"\nColumns: {transformed_data.columns.tolist()}") 