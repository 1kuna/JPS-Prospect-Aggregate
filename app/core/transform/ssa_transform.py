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

# Specific data directory for SSA
DATA_DIR = BASE_DIR / "data" / "raw" / "ssa_forecast"

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
    # Uses the first set of headers found
    rename_map = {
        # Raw SSA Name: Canonical Name
        'APP #': 'native_id',
        'SITE Type': 'office', # Assumption
        'REQUIREMENT TYPE': 'requirement_title', # Assumption
        'DESCRIPTION': 'requirement_description',
        'EST COST PER FY': 'estimated_value', # Needs parsing
        'PLANNED AWARD DATE': 'award_date', # Needs parsing
        'CONTRACT TYPE': 'contract_type',
        'NAICS': 'naics',
        'TYPE OF COMPETITION': 'set_aside', # Assumption
        'PLACE OF PERFORMANCE': 'place_raw' # Needs splitting
        # 'solicitation_date' appears missing
    }
    logging.info(f"Applying SSA specific column mapping: {rename_map}")
    # Filter DataFrame to only columns that exist before renaming to avoid errors with repeated headers
    df = df[list(rename_map.keys())] 
    df = df.rename(columns=rename_map)

    # --- Parsing Logic --- 
    # TODO: Implement splitting logic for 'place_raw'. Verify format.
    if 'place_raw' in df.columns:
        logging.info("'place_raw' requires splitting.")
        df = df.drop(columns=['place_raw'])
    df['place_city'] = pd.NA
    df['place_state'] = pd.NA
    df['place_country'] = pd.NA # Default?

    # TODO: Implement parsing for 'estimated_value'.
    if 'estimated_value' in df.columns:
        logging.info("'estimated_value' requires parsing.")
        df['estimated_value'] = pd.to_numeric(df['estimated_value'], errors='coerce') # Basic coerce

    # TODO: Implement parsing for 'award_date'.
    if 'award_date' in df.columns:
        logging.info("'award_date' requires parsing.")
        df['award_date'] = pd.to_datetime(df['award_date'], errors='coerce')

    # Initialize missing columns
    df['solicitation_date'] = pd.NA

    # --- General normalization (lowercase, snake_case) ---
    df.columns = df.columns.str.strip().str.lower().str.replace(r'\s+\(.*?\)', '', regex=True).str.replace(r'\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)

    # Identify unmapped columns AFTER normalization and derivation
    # Note: We explicitly selected columns earlier, so this should ideally be empty unless 
    # canonical_cols contains items not in the initial rename_map
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