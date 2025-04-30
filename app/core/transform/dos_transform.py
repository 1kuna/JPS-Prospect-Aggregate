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

# Specific data directory for DOS
DATA_DIR = BASE_DIR / "data" / "raw" / "dos_forecast"

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
        # Add other potential extensions if needed (e.g., .xls)
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

# --- Normalization Function (DOS specific) ---

def normalize_columns_dos(df: pd.DataFrame, canonical_cols: list[str]) -> pd.DataFrame:
    """Renames DOS columns, normalizes, handles extras."""
    # Define the explicit mapping for DOS from Excel header
    rename_map = {
        # Raw DOS Name: Canonical Name
        'Contract Number': 'native_id',
        'Office Symbol': 'office',
        'Requirement Title': 'requirement_title',
        'Requirement Description': 'requirement_description',
        'Estimated Value': 'estimated_value', # Requires parsing (range or value?)
        'Place of Performance Country': 'place_country',
        'Place of Performance City': 'place_city',
        'Place of Performance State': 'place_state',
        'Award Type': 'contract_type',
        'Anticipated Award Date': 'award_date', # Requires date parsing
        'Anticipated Set Aside': 'set_aside',
        'Anticipated Solicitation Release Date': 'solicitation_date' # Requires date parsing
        # NAICS code not present in source
    }
    logging.info(f"Applying DOS specific column mapping: {rename_map}")
    df = df.rename(columns=rename_map)

    # --- Handle potential alternative/derived fields ---
    # Award Date Parsing
    # TODO: Implement robust parsing for 'award_date'. Consider both 'Anticipated Award Date' and 'Target Award Quarter'.
    if 'award_date' in df.columns:
        logging.info("'award_date' requires parsing (might be date or quarter).")
        # Basic coerce attempt after rename, likely insufficient for quarters
        df['award_date'] = pd.to_datetime(df['award_date'], errors='coerce')
    elif 'Target Award Quarter' in df.columns:
        logging.info("'Target Award Quarter' found, requires parsing for 'award_date'.")
        df['award_date'] = pd.NA # Initialize award_date if only quarter exists
    else:
        df['award_date'] = pd.NA

    # Estimated Value Parsing
    # TODO: Implement robust parsing for 'estimated_value'. Check both 'Estimated Value' and 'Dollar Value' columns. Handle ranges/values.
    if 'estimated_value' in df.columns:
        logging.info("'estimated_value' requires parsing.")
        df['estimated_value'] = pd.to_numeric(df['estimated_value'], errors='coerce') # Basic coerce
    elif 'Dollar Value' in df.columns:
        logging.info("'Dollar Value' column found, requires parsing for 'estimated_value'.")
        df['estimated_value'] = pd.to_numeric(df['Dollar Value'], errors='coerce') # Rename & basic coerce
        df = df.drop(columns=['Dollar Value']) # Drop original after potential use
    else:
        df['estimated_value'] = pd.NA

    # Solicitation Date Parsing
    # TODO: Implement robust date parsing for 'solicitation_date'.
    if 'solicitation_date' in df.columns:
        logging.info("'solicitation_date' requires parsing.")
        df['solicitation_date'] = pd.to_datetime(df['solicitation_date'], errors='coerce')

    # --- General normalization (lowercase, snake_case) ---
    df.columns = df.columns.str.strip().str.lower().str.replace(r'\s+\(.*?\)', '', regex=True).str.replace(r'\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)

    # Identify unmapped columns AFTER normalization and derivation
    current_cols = df.columns.tolist()
    unmapped_cols = [col for col in current_cols if col not in canonical_cols and col not in ['source', 'id']]

    # Handle 'extra' column
    if unmapped_cols:
        logging.info(f"Found unmapped columns for 'extra': {unmapped_cols}")
        # Ensure data types are suitable for JSON serialization if needed
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

def transform_dos() -> pd.DataFrame | None:
    """Transforms the latest DOS forecast raw data."""
    canonical_cols = CANONICAL_COLUMNS
    latest_file = find_latest_raw_file(DATA_DIR)
    if not latest_file:
        logging.error(f"No raw data file found for DOS in {DATA_DIR}")
        return None

    try:
        if latest_file.suffix == '.xlsx':
            # Read from 'FY25-Procurement-Forecast', header is on row 1 (index 0)
            df = pd.read_excel(latest_file, sheet_name='FY25-Procurement-Forecast', header=0)
            logging.info(f"Loaded {len(df)} rows from Excel file {latest_file}, sheet 'FY25-Procurement-Forecast'")
        elif latest_file.suffix == '.csv':
            # TODO: Determine correct header row and if on_bad_lines is needed for DOS CSV
            df = pd.read_csv(latest_file, header=0, on_bad_lines='skip')
            logging.info(f"Loaded {len(df)} rows from CSV file {latest_file}")
        else:
            logging.error(f"Unsupported file type: {latest_file.suffix}")
            return None

        if df.empty:
            logging.warning(f"Loaded DataFrame is empty from {latest_file}")
            return df

        # --- Pre-processing --- 
        # Add any DOS specific cleaning here if needed (e.g., drop totally empty rows)
        df.dropna(how='all', inplace=True)

        # Normalize columns
        df_normalized = normalize_columns_dos(df.copy(), canonical_cols)

        # Add source column
        df_normalized['source'] = 'DOS'

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
        
        # Ensure final dataframe only contains columns from the final ordered list
        df_final = df_normalized[[col for col in final_ordered_cols if col in df_normalized.columns]]

        logging.info(f"DOS Transformation complete. Processed {len(df_final)} rows.")
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
    transformed_data = transform_dos()
    if transformed_data is not None:
        print(transformed_data.head())
        print(f"\nTransformed DataFrame shape: {transformed_data.shape}")
        print(f"\nColumns: {transformed_data.columns.tolist()}") 