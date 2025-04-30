import pandas as pd
import hashlib
import os
from pathlib import Path
import logging

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
        # Raw HHS Name: Canonical Name
        'Existing Contract number (if applicable)': 'native_id',
        'Title': 'requirement_title',
        'Description': 'requirement_description',
        'Primary NAICS': 'naics',
        'Total Contract Range': 'estimated_value', # Needs parsing
        'Target Solicitation Month/Year': 'solicitation_date', # Needs date parsing
        'Target Award Month/Year (Award by)': 'award_date', # Needs date parsing
        'Operating Division': 'office',
        'Anticipated Acquisition Strategy': 'contract_type' # Mapping assumption
        # Place of Performance (City, State, Country) not available
    }
    logging.info(f"Applying HHS specific column mapping: {rename_map}")
    df = df.rename(columns=rename_map)

    # --- Parsing Logic --- 
    # TODO: Implement parsing for 'estimated_value' from range string.
    if 'estimated_value' in df.columns:
        logging.info("'estimated_value' requires parsing.")
        df['estimated_value'] = pd.to_numeric(df['estimated_value'], errors='coerce') # Basic coerce

    # TODO: Implement robust date parsing for 'solicitation_date' (Month/Year format).
    if 'solicitation_date' in df.columns:
        logging.info("'solicitation_date' requires parsing.")
        # Example: Convert 'MM/YYYY' or 'Month YYYY' to datetime
        df['solicitation_date'] = pd.to_datetime(df['solicitation_date'], errors='coerce') 

    # TODO: Implement robust date parsing for 'award_date' (Month/Year format).
    if 'award_date' in df.columns:
        logging.info("'award_date' requires parsing.")
        df['award_date'] = pd.to_datetime(df['award_date'], errors='coerce')

    # Initialize missing place columns
    df['place_city'] = pd.NA
    df['place_state'] = pd.NA
    df['place_country'] = pd.NA

    # --- General normalization (lowercase, snake_case) ---
    # Added cleaning for '(if applicable)' common in HHS headers
    df.columns = df.columns.str.replace(r'\(if applicable\)', '', regex=True).str.strip()
    df.columns = df.columns.str.lower().str.replace(r'\s+\(.*?\)', '', regex=True).str.replace(r'\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)

    # Identify unmapped columns AFTER normalization and derivation
    current_cols = df.columns.tolist()
    unmapped_cols = [col for col in current_cols if col not in canonical_cols and col not in ['source', 'id']]

    # Handle 'extra' column
    if unmapped_cols:
        logging.info(f"Found unmapped columns for 'extra': {unmapped_cols}")
        df['extra'] = df[unmapped_cols].astype(str).to_dict(orient='records')
        df = df.drop(columns=unmapped_cols)
    else:
        df['extra'] = None

    # Ensure all canonical columns exist (excluding 'id')
    for col in canonical_cols:
        if col not in df.columns and col != 'id':
           df[col] = pd.NA

    # Return dataframe with only existing canonical columns (order adjusted later)
    final_cols = [col for col in canonical_cols if col in df.columns and col != 'id']
    return df[final_cols]

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
        
        df_final = df_normalized[[col for col in final_ordered_cols if col in df_normalized.columns]]

        logging.info(f"HHS Transformation complete. Processed {len(df_final)} rows.")
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