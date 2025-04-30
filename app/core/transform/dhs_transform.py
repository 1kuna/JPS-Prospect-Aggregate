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
from app.utils.parsing import parse_value_range, fiscal_quarter_to_date

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the base data directory
try:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
except NameError:
    BASE_DIR = Path('.').resolve()

# Specific data directory for DHS
DATA_DIR = BASE_DIR / "data" / "raw" / "dhs_forecast"

# Hardcoded canonical columns (assuming same as ACQG for now)
CANONICAL_COLUMNS = [
    'source', 'native_id', 'requirement_title', 'requirement_description',
    'naics', 'estimated_value', 'est_value_unit', 'solicitation_date',
    'award_date', 'office', 'place_city', 'place_state', 'place_country',
    'contract_type', 'set_aside', 'loaded_at', 'extra', 'id'
]

# --- Helper Functions (Copied from acqg_transform.py, potentially reusable) ---

def find_latest_raw_file(data_dir: Path) -> Path | None:
    """Finds the most recently modified file in the specified directory."""
    try:
        # Look for Excel files first, then CSV
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

# --- Normalization Function (May need customization per source) ---

def normalize_columns_dhs(df: pd.DataFrame, canonical_cols: list[str]) -> pd.DataFrame:
    """Renames DHS columns, normalizes, handles extras."""
    # Define the explicit mapping for DHS
    rename_map = {
        # Raw DHS Name: Canonical Name
        'APFS Number': 'native_id',
        'NAICS': 'naics',
        'Component': 'office',
        'Title': 'requirement_title',
        'Contract Type': 'contract_type',
        'Dollar Range': 'estimated_value_raw', # Rename raw value first
        'Small Business Set-Aside': 'set_aside',
        'Place of Performance City': 'place_city',
        'Place of Performance State': 'place_state',
        'Description': 'requirement_description',
        'Estimated Solicitation Release': 'solicitation_date',
        'Award Quarter': 'award_date_raw' # Rename raw value first
    }
    logging.info(f"Applying DHS specific column mapping: {rename_map}")
    df = df.rename(columns=rename_map)

    # --- Add Parsing Logic --- 
    # Parse dates
    if 'solicitation_date' in df.columns:
        df['solicitation_date'] = pd.to_datetime(df['solicitation_date'], errors='coerce')
    if 'award_date_raw' in df.columns:
        df['award_date'] = df['award_date_raw'].apply(fiscal_quarter_to_date)
    else: 
        df['award_date'] = pd.NaT

    # Parse estimated value range
    if 'estimated_value_raw' in df.columns:
        parsed_values = df['estimated_value_raw'].apply(parse_value_range)
        df['estimated_value'] = parsed_values.apply(lambda x: x[0])
        df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
    else:
        df['estimated_value'] = pd.NA 
        df['est_value_unit'] = pd.NA

    # Initialize Place Country if missing
    if 'place_country' not in df.columns:
         df['place_country'] = 'USA' # Assume USA if not specified
         
    # Drop raw columns after parsing
    df = df.drop(columns=['estimated_value_raw', 'award_date_raw'], errors='ignore')
    # --- End Parsing Logic ---

    # General normalization (lowercase, snake_case)
    # Remove content in parentheses (e.g., from place names)
    df.columns = df.columns.str.strip().str.lower().str.replace(r'\s+\(.*?\)', '', regex=True).str.replace(r'\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)

    # Identify unmapped columns AFTER normalization and parsing
    current_cols = df.columns.tolist()
    # Ensure canonical columns used for comparison are also normalized
    normalized_canonical = [c.strip().lower().replace(' ', '_').replace(r'[^a-z0-9_]', '') for c in canonical_cols]
    unmapped_cols = [col for col in current_cols if col not in normalized_canonical and col not in ['source', 'id']]

    # Handle 'extra' column
    if unmapped_cols:
        logging.info(f"Found unmapped columns for 'extra': {unmapped_cols}")
        # Convert potential non-string types in unmapped columns before to_dict
        for col in unmapped_cols:
             if df[col].dtype == 'datetime64[ns]' or df[col].dtype.name == 'datetime64[ns, UTC]':
                 df[col] = df[col].dt.isoformat()
             # Add other type conversions if necessary (e.g., numeric to str)
        df['extra'] = df[unmapped_cols].astype(str).to_dict(orient='records') # Ensure all extra data is string
        df = df.drop(columns=unmapped_cols)
    else:
        df['extra'] = None

    # Ensure all canonical columns exist
    for col in normalized_canonical:
        if col not in df.columns:
           df[col] = pd.NA # Use pd.NA for consistency

    # Return dataframe with only canonical columns in the correct order
    # Use the normalized_canonical list for final selection and ordering
    final_cols_order = [col for col in normalized_canonical if col in df.columns]
    return df[final_cols_order]

# --- Main Transformation Function ---

def transform_dhs() -> pd.DataFrame | None:
    """Transforms the latest DHS forecast raw data."""
    canonical_cols = CANONICAL_COLUMNS
    latest_file = find_latest_raw_file(DATA_DIR)
    if not latest_file:
        logging.error(f"No raw data file found for DHS in {DATA_DIR}")
        return None

    try:
        # Determine file type and read accordingly
        if latest_file.suffix == '.xlsx':
            # TODO: Determine correct sheet_name and header row for DHS Excel
            df = pd.read_excel(latest_file, sheet_name=0, header=0)
            logging.info(f"Loaded {len(df)} rows from Excel file {latest_file}")
        elif latest_file.suffix == '.csv':
            # Assume header=0 and skip bad lines for CSV
            df = pd.read_csv(latest_file, header=0, on_bad_lines='skip')
            logging.info(f"Loaded {len(df)} rows from CSV file {latest_file}")
        else:
            logging.error(f"Unsupported file type: {latest_file.suffix}")
            return None

        if df.empty:
            logging.warning(f"Loaded DataFrame is empty from {latest_file}")
            return df

        # --- Pre-processing (if needed, e.g., drop junk rows before normalization) ---
        # Example: df = df.dropna(how='all') # Drop rows where all cells are NaN
        # Example: df = df[df['column_name'].notna()] # Drop rows based on a specific column

        # Normalize columns using the DHS specific function
        df_normalized = normalize_columns_dhs(df.copy(), canonical_cols)

        # Add source column
        df_normalized['source'] = 'DHS'

        # Add id column
        df_normalized['id'] = df_normalized.apply(generate_id, axis=1)

        # Reorder columns: source, native_id, id, rest..., extra
        final_ordered_cols = []
        if 'source' in df_normalized.columns: final_ordered_cols.append('source')
        if 'native_id' in df_normalized.columns: final_ordered_cols.append('native_id')
        final_ordered_cols.append('id')
        final_ordered_cols.extend([col for col in df_normalized.columns if col not in ['source', 'native_id', 'id']])
        # Ensure 'extra' is last if it exists
        if 'extra' in final_ordered_cols:
             final_ordered_cols.remove('extra')
             final_ordered_cols.append('extra')

        df_final = df_normalized[final_ordered_cols]

        logging.info(f"Transformation complete. Processed {len(df_final)} rows.")
        
        # TEMPORARY EXPORT CODE
        export_path = os.path.join('data', 'processed', 'dhs.csv')
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        df_final.to_csv(export_path, index=False)
        logging.info(f"Temporarily exported data to {export_path}")
        # END TEMPORARY EXPORT CODE

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
    transformed_data = transform_dhs()
    if transformed_data is not None:
        print(transformed_data.head())
        print(f"\nTransformed DataFrame shape: {transformed_data.shape}")
        print(f"\nColumns: {transformed_data.columns.tolist()}") 