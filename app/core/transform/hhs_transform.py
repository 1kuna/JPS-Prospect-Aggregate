import os
import sys
from pathlib import Path

# Add project root to sys.path to allow absolute imports
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

import pandas as pd
import hashlib
import logging
import re
from datetime import datetime
from app.utils.parsing import parse_value_range
from app.database.crud import bulk_upsert_prospects

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the base data directory
try:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
except NameError:
    BASE_DIR = Path('.').resolve()

# Specific data directory for HHS
DATA_DIR = BASE_DIR / "data" / "raw" / "hhs_forecast"

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
        excel_files = list(data_dir.glob('*.xlsx'))
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

# --- Normalization Function (HHS specific) ---

def normalize_columns_hhs(df: pd.DataFrame, canonical_cols: list[str]) -> pd.DataFrame:
    """Renames HHS columns, normalizes, handles extras."""
    # Define the explicit mapping for HHS from CSV header
    rename_map = {
        'Existing Contract number (if applicable)': 'native_id',
        'Title': 'requirement_title',
        'Description': 'requirement_description',
        'Primary NAICS': 'naics',
        'Total Contract Range': 'estimated_value_raw', # Rename raw
        'Target Solicitation Month/Year': 'solicitation_date_raw', # Rename raw
        'Target Award Month/Year (Award by)': 'award_date_raw', # Rename raw
        'Operating Division': 'office',
        'Anticipated Acquisition Strategy': 'set_aside'
    }
    logging.info(f"Applying HHS specific column mapping: {rename_map}")
    rename_map_existing = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=rename_map_existing)

    # --- Parsing Logic --- 
    if 'estimated_value_raw' in df.columns:
        logging.info("Parsing 'estimated_value_raw'.")
        parsed_values = df['estimated_value_raw'].apply(parse_value_range)
        df['estimated_value'] = parsed_values.apply(lambda x: x[0])
        df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
    else:
        df['estimated_value'], df['est_value_unit'] = pd.NA, pd.NA

    # Parse dates (attempt multiple formats like MM/YYYY, Mon YYYY, Month YYYY)
    date_formats = ["%m/%Y", "%b %Y", "%B %Y", "%m/%d/%Y"] # Add more formats if needed
    if 'solicitation_date_raw' in df.columns:
        logging.info("Parsing 'solicitation_date_raw'.")
        df['solicitation_date'] = pd.to_datetime(df['solicitation_date_raw'], errors='coerce')
        # Fallback for specific formats if infer fails broadly
        # for fmt in date_formats:
        #     df['solicitation_date'] = df['solicitation_date'].fillna(pd.to_datetime(df['solicitation_date_raw'], format=fmt, errors='coerce'))
    else:
        df['solicitation_date'] = pd.NaT

    if 'award_date_raw' in df.columns:
        logging.info("Parsing 'award_date_raw'.")
        df['award_date'] = pd.to_datetime(df['award_date_raw'], errors='coerce')
        # Fallback for specific formats if infer fails broadly
        # for fmt in date_formats:
        #     df['award_date'] = df['award_date'].fillna(pd.to_datetime(df['award_date_raw'], format=fmt, errors='coerce'))
    else:
        df['award_date'] = pd.NaT

    # Initialize missing place columns
    df['place_city'] = pd.NA
    df['place_state'] = pd.NA
    df['place_country'] = 'USA' # Default assumption for HHS
    
    # Drop raw columns
    cols_to_drop = ['estimated_value_raw', 'solicitation_date_raw', 'award_date_raw']
    df = df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore')

    # --- General normalization (lowercase, snake_case) ---
    df.columns = df.columns.str.replace(r'\(if applicable\)', '', regex=True).str.strip()
    df.columns = df.columns.str.lower().str.replace(r'\s+\(.*?\)', '', regex=True).str.replace(r'\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)

    # --- Handle Extra/Canonical Columns ---
    current_cols = df.columns.tolist()
    normalized_canonical = [c.strip().lower().replace(' ', '_').replace(r'[^a-z0-9_]', '') for c in canonical_cols]
    unmapped_cols = [col for col in current_cols if col not in normalized_canonical and col not in ['source', 'id']]
    if unmapped_cols:
        logging.info(f"Found unmapped columns for 'extra': {unmapped_cols}")
        for col in unmapped_cols:
             if df[col].dtype == 'datetime64[ns]' or df[col].dtype.name == 'datetime64[ns, UTC]':
                 df[col] = df[col].dt.isoformat()
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

def transform_hhs() -> pd.DataFrame | None:
    """Transforms the latest HHS forecast raw data."""
    canonical_cols = CANONICAL_COLUMNS
    latest_file = find_latest_raw_file(DATA_DIR)
    if not latest_file:
        logging.error(f"No raw data file found for HHS in {DATA_DIR}")
        return None

    try:
        if latest_file.suffix == '.xlsx':
            # TODO: Update if HHS uses Excel - sheet_name, header
            df = pd.read_excel(latest_file, sheet_name=0, header=0)
            logging.info(f"Loaded {len(df)} rows from Excel file {latest_file}")
        elif latest_file.suffix == '.csv':
            # Assume header=0 for HHS CSV, skip bad lines
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
        df_normalized = normalize_columns_hhs(df.copy(), canonical_cols)

        # Add source column
        df_normalized['source'] = 'HHS'

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
        
        df_final = df_normalized[final_ordered_cols]

        logging.info(f"Transformation complete. Processed {len(df_final)} rows.")

        # TEMPORARY EXPORT CODE - COMMENTED OUT
        # export_path = os.path.join('data', 'processed', 'hhs.csv')
        # os.makedirs(os.path.dirname(export_path), exist_ok=True)
        # df_final.to_csv(export_path, index=False)
        # logging.info(f"Temporarily exported data to {export_path}")
        # END TEMPORARY EXPORT CODE

        # Upsert data to database
        try:
            logging.info(f"Attempting to upsert {len(df_final)} records for HHS.")
            bulk_upsert_prospects(df_final)
            logging.info(f"Successfully upserted HHS data.")
        except Exception as db_error:
            logging.error(f"Database upsert failed for HHS: {db_error}", exc_info=True)
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
    transformed_data = transform_hhs()
    if transformed_data is not None:
        print(transformed_data.head())
        print(f"\nTransformed DataFrame shape: {transformed_data.shape}")
        print(f"\nColumns: {transformed_data.columns.tolist()}") 