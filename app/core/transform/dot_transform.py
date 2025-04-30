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

# Specific data directory for DOT
DATA_DIR = BASE_DIR / "data" / "raw" / "dot_forecast"

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

# --- Normalization Function (DOT specific) ---

def normalize_columns_dot(df: pd.DataFrame, canonical_cols: list[str]) -> pd.DataFrame:
    """Renames DOT columns, normalizes, handles extras."""
    # Define the explicit mapping for DOT from CSV header
    rename_map = {
        # Raw DOT Name: Canonical Name
        'Sequence Number': 'native_id', # Assuming this is unique
        'Procurement Office': 'office',
        'Project Title': 'requirement_title',
        'Description': 'requirement_description',
        'Estimated Value': 'estimated_value', # Requires parsing (e.g., '>$250K')
        'NAICS': 'naics',
        'Competition Type': 'set_aside', # Mapping assumption
        'RFP Quarter': 'solicitation_date', # Requires FY + Quarter parsing
        'Anticipated Award Date': 'award_date', # Requires date parsing
        'Place of Performance': 'place_raw', # Needs splitting
        'Action/Award Type': 'contract_type'
    }
    logging.info(f"Applying DOT specific column mapping: {rename_map}")
    df = df.rename(columns=rename_map)

    # --- Handle combined/derived/parsed fields --- 
    
    # Split 'Place of Performance' 
    # TODO: Implement splitting logic for 'place_raw'. Verify format (City, State? Just State? Country?).
    # Assign results to place_city, place_state, place_country.
    if 'place_raw' in df.columns:
        logging.info("'place_raw' column found, requires splitting.")
        df = df.drop(columns=['place_raw']) # Drop the raw column
    df['place_city'] = pd.NA 
    df['place_state'] = pd.NA
    df['place_country'] = pd.NA # Assign default (e.g., 'USA') or leave NA if needed
    

    # Parse estimated value
    # TODO: Implement robust parsing for 'estimated_value'. Handle ranges, K/M/B suffixes, symbols like '>', '$'.
    if 'estimated_value' in df.columns:
        logging.info("'estimated_value' column found, requires parsing.")
        # Example: df['estimated_value'] = parse_value_string(df['estimated_value'])
        df['estimated_value'] = pd.to_numeric(df['estimated_value'], errors='coerce') # Basic coerce after rename

    # Parse solicitation date (from RFP Quarter like 'Q1')
    # TODO: Implement parsing for 'solicitation_date'. Combine with FY column and convert quarter to date.
    if 'solicitation_date' in df.columns:
        # Example: df['solicitation_date'] = parse_fy_quarter(df, fy_col='fy', quarter_col='solicitation_date')
        logging.warning("'solicitation_date' requires parsing implementation.")
        df['solicitation_date'] = pd.NA # Set to NA until implemented

    # Parse award date
    # TODO: Implement robust date parsing for 'award_date'.
    if 'award_date' in df.columns:
        # Example: df['award_date'] = parse_flexible_date(df['award_date'])
        logging.info("'award_date' column found, requires parsing.")
        df['award_date'] = pd.to_datetime(df['award_date'], errors='coerce') # Basic coerce after rename

    # --- General normalization (lowercase, snake_case) ---
    df.columns = df.columns.str.strip().str.lower().str.replace(r'\s+\(.*?\)', '', regex=True).str.replace(r'\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)

    # Identify unmapped columns
    current_cols = df.columns.tolist()
    unmapped_cols = [col for col in current_cols if col not in canonical_cols and col not in ['source', 'id']]

    # Handle 'extra' column
    if unmapped_cols:
        logging.info(f"Found unmapped columns for 'extra': {unmapped_cols}")
        df['extra'] = df[unmapped_cols].astype(str).to_dict(orient='records')
        df = df.drop(columns=unmapped_cols)
    else:
        df['extra'] = None

    # Ensure all canonical columns exist
    for col in canonical_cols:
        if col not in df.columns and col != 'id':
           df[col] = pd.NA

    # Return dataframe with only existing canonical columns (order adjusted later)
    final_cols = [col for col in canonical_cols if col in df.columns and col != 'id']
    return df[final_cols]

# --- Main Transformation Function ---

def transform_dot() -> pd.DataFrame | None:
    """Transforms the latest DOT forecast raw data."""
    canonical_cols = CANONICAL_COLUMNS
    latest_file = find_latest_raw_file(DATA_DIR)
    if not latest_file:
        logging.error(f"No raw data file found for DOT in {DATA_DIR}")
        return None

    try:
        if latest_file.suffix == '.xlsx':
            # TODO: Update if DOT uses Excel - sheet_name, header
            df = pd.read_excel(latest_file, sheet_name=0, header=0)
            logging.info(f"Loaded {len(df)} rows from Excel file {latest_file}")
        elif latest_file.suffix == '.csv':
            # Assume header=0 for DOT CSV, skip bad lines
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
        df_normalized = normalize_columns_dot(df.copy(), canonical_cols)

        # Add source column
        df_normalized['source'] = 'DOT'

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

        logging.info(f"DOT Transformation complete. Processed {len(df_final)} rows.")
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
    transformed_data = transform_dot()
    if transformed_data is not None:
        print(transformed_data.head())
        print(f"\nTransformed DataFrame shape: {transformed_data.shape}")
        print(f"\nColumns: {transformed_data.columns.tolist()}") 