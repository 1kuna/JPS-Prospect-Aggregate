import pandas as pd
import hashlib
import os
from pathlib import Path
import logging
import sys # Add sys import if needed for path adjustments

# --- Start temporary path adjustment ---
# Adjust path if necessary to find app modules
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# --- End temporary path adjustment ---

from app.database.crud import bulk_upsert_prospects # Import the upsert function

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the base data directory
# Assuming the script runs from the project root or similar context
# Adjust BASE_DIR if necessary based on execution context
try:
    # Assumes execution from project root
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
except NameError:
    # Fallback for interactive environments
    BASE_DIR = Path('.').resolve()

DATA_DIR = BASE_DIR / "data" / "raw" / "acquisition_gateway"
DOCS_DIR = BASE_DIR / "docs"

# Hardcoded canonical columns based on docs/canonical_columns.csv
CANONICAL_COLUMNS = [
    'source', 'native_id', 'requirement_title', 'requirement_description',
    'naics', 'estimated_value', 'est_value_unit', 'solicitation_date',
    'award_date', 'office', 'place_city', 'place_state', 'place_country',
    'contract_type', 'set_aside', 'loaded_at', 'extra', 'id'
]

def find_latest_raw_file(data_dir: Path) -> Path | None:
    """Finds the most recently modified file in the specified directory."""
    try:
        files = list(data_dir.glob('*.*')) # Assuming CSV or other flat files
        if not files:
            logging.warning(f"No files found in {data_dir}")
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

def normalize_columns(df: pd.DataFrame, canonical_cols: list[str]) -> pd.DataFrame:
    """Renames columns based on explicit mapping, normalizes others, and handles extras."""
    # Define the explicit mapping from raw column names to canonical names
    rename_map = {
        # Raw Name: Canonical Name
        'Listing ID': 'native_id', # Assuming Listing ID is the preferred native identifier
        'Title': 'requirement_title',
        'Body': 'requirement_description', # Prioritizing Body over Summary
        'NAICS Code': 'naics',
        'Estimated Contract Value': 'estimated_value',
        'Estimated Solicitation Date': 'solicitation_date',
        'Ultimate Completion Date': 'award_date', # Using this for award_date
        'Organization': 'office',
        'Place of Performance City': 'place_city',
        'Place of Performance State': 'place_state',
        'Place of Performance Country': 'place_country',
        'Contract Type': 'contract_type',
        'Set Aside Type': 'set_aside'
        # Add other mappings as needed
    }

    # Apply the explicit renaming
    df = df.rename(columns=rename_map)

    # Handle potential alternative for description if 'Body' wasn't present but 'Summary' is
    if 'requirement_description' not in df.columns and 'Summary' in df.columns:
        df = df.rename(columns={'Summary': 'requirement_description'})

    # --- Add Parsing Logic --- 
    # Parse dates (assuming standard formats, add error handling)
    if 'solicitation_date' in df.columns:
        df['solicitation_date'] = pd.to_datetime(df['solicitation_date'], errors='coerce')
    if 'award_date' in df.columns:
        df['award_date'] = pd.to_datetime(df['award_date'], errors='coerce')

    # Parse estimated value (simple numeric conversion, assumes no units/ranges in source)
    if 'estimated_value' in df.columns:
        df['estimated_value'] = pd.to_numeric(df['estimated_value'], errors='coerce')
        df['est_value_unit'] = None # Explicitly set unit to None if only number exists
    else:
        df['estimated_value'] = pd.NA # Ensure column exists even if not in source
        df['est_value_unit'] = pd.NA

    # --- End Parsing Logic ---

    # Normalize all column names AFTER explicit renaming (lowercase, snake_case)
    df.columns = df.columns.str.strip().str.lower().str.replace(r'\s+\(\w+\)', '', regex=True).str.replace(r'\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)

    # Remove duplicate columns after normalization, keeping the first occurrence
    df = df.loc[:, ~df.columns.duplicated()]

    # Identify unmapped columns AFTER normalization
    # These are columns that were not explicitly mapped and whose normalized name is not in canonical_cols
    current_cols = df.columns.tolist()
    unmapped_cols = [col for col in current_cols if col not in canonical_cols and col not in ['source', 'id']]

    # Add 'extra' column for unmapped fields
    if unmapped_cols:
        # Important: Create the 'extra' column from the original DataFrame *before* dropping columns
        # This requires referencing the original column names (before normalization) if they were complex
        # Simpler approach: Use the *normalized* unmapped column names
        df['extra'] = df[unmapped_cols].to_dict(orient='records')
        # Drop original unmapped columns
        df = df.drop(columns=unmapped_cols)
    else:
        # Ensure 'extra' column exists even if empty, matching canonical list
        df['extra'] = None # Or pd.NA or {} as preferred

    # Ensure all canonical columns exist, adding missing ones as None/NA
    for col in canonical_cols:
        if col not in df.columns:
            df[col] = pd.NA # Add missing canonical columns

    # Return dataframe with only canonical columns in the specified order
    # Filter canonical_cols to only those actually present (should be all now)
    final_cols_order = [col for col in canonical_cols if col in df.columns]

    return df[final_cols_order]


def generate_id(row: pd.Series) -> str:
    """Generates an MD5 hash for the row based on key fields."""
    # Use empty string for missing values to ensure consistent hashing
    naics = str(row.get('naics', ''))
    title = str(row.get('requirement_title', ''))
    desc = str(row.get('requirement_description', ''))
    
    unique_string = f"{naics}-{title}-{desc}"
    return hashlib.md5(unique_string.encode('utf-8')).hexdigest()


def transform_acquisition_gateway() -> pd.DataFrame | None:
    """Transforms the latest Acquisition Gateway raw data."""
    # Use the hardcoded list of canonical columns
    canonical_cols = CANONICAL_COLUMNS
    if not canonical_cols: # Should not happen with hardcoded list, but good practice
        logging.error("Canonical columns list is empty.")
        return None

    latest_file = find_latest_raw_file(DATA_DIR)
    if not latest_file:
        logging.error(f"No raw data file found for Acquisition Gateway in {DATA_DIR}")
        return None

    try:
        # Use header=0 since the first line (index 0) contains the headers
        # Skip rows with too many fields (parsing errors)
        df = pd.read_csv(latest_file, header=0, on_bad_lines='skip')
        logging.info(f"Loaded {len(df)} rows from {latest_file}")

        # Normalize columns using the updated function
        df_normalized = normalize_columns(df.copy(), canonical_cols)

        # Add source column
        df_normalized['source'] = 'ACQG'

        # Add id column (ensure required fields are present *after* normalization)
        # The generate_id function already handles missing keys gracefully
        df_normalized['id'] = df_normalized.apply(generate_id, axis=1)

        # Reorder columns to final desired state: source, native_id, id, rest..., extra
        # Note: normalize_columns already returns columns in canonical order
        # We just need to insert 'id' correctly if not already handled
        final_ordered_cols = df_normalized.columns.tolist()
        if 'id' in final_ordered_cols:
            final_ordered_cols.remove('id')
        
        id_insert_pos = 0
        if 'source' in final_ordered_cols:
            id_insert_pos += 1
        if 'native_id' in final_ordered_cols:
             id_insert_pos += 1
        
        final_ordered_cols.insert(id_insert_pos, 'id')
        
        df_final = df_normalized[final_ordered_cols]

        logging.info(f"Transformation complete. Processed {len(df_final)} rows.")

        # TEMPORARY EXPORT CODE - COMMENTED OUT
        # export_path = os.path.join('data', 'processed', 'acqg.csv')
        # os.makedirs(os.path.dirname(export_path), exist_ok=True)
        # df_final.to_csv(export_path, index=False)
        # logging.info(f"Temporarily exported data to {export_path}")
        # END TEMPORARY EXPORT CODE

        # Upsert data to database
        try:
            logging.info(f"Attempting to upsert {len(df_final)} records for ACQG.")
            bulk_upsert_prospects(df_final)
            logging.info(f"Successfully upserted ACQG data.")
        except Exception as db_error:
            logging.error(f"Database upsert failed for ACQG: {db_error}", exc_info=True)
            # Decide if failure should halt the process or just be logged
            # return None # Optionally return None or re-raise

        return df_final

    except pd.errors.EmptyDataError:
        logging.error(f"Raw data file is empty: {latest_file}")
        return None
    except Exception as e:
        logging.error(f"Error during transformation of {latest_file}: {e}")
        return None

# Example usage (optional, for testing)
if __name__ == "__main__":
    transformed_data = transform_acquisition_gateway()
    if transformed_data is not None:
        print(transformed_data.head())
        print(f"Transformed DataFrame shape: {transformed_data.shape}")
        print(f"Columns: {transformed_data.columns.tolist()}") 