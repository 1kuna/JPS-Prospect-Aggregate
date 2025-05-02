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
# Import parsing functions
from app.utils.parsing import parse_value_range, fiscal_quarter_to_date, split_place
from app.database.crud import bulk_upsert_prospects # Import the upsert function

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the base data directory
try:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
except NameError:
    BASE_DIR = Path('.').resolve()

# Specific data directory for TREASURY
DATA_DIR = BASE_DIR / "data" / "raw" / "treasury_forecast"

# Hardcoded canonical columns
CANONICAL_COLUMNS = [
    'source', 'native_id', 'requirement_title', 'requirement_description',
    'naics', 'estimated_value', 'est_value_unit', 'solicitation_date',
    'award_date', 'award_fiscal_year', 'office', 'place_city', 'place_state', 'place_country',
    'contract_type', 'set_aside', 'loaded_at', 'extra', 'id'
]

# --- Helper Functions (Potentially reusable) ---

def find_latest_raw_file(data_dir: Path) -> Path | None:
    """Finds the most recently modified file (Excel or CSV) in the directory."""
    try:
        # Include .xls for Treasury
        excel_files = list(data_dir.glob('*.xlsx')) + list(data_dir.glob('*.xlsm')) + list(data_dir.glob('*.xls'))
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

# --- Helper functions are imported from app.utils.parsing ---

# --- Normalization Function (TREASURY specific) ---

def normalize_columns_treasury(df: pd.DataFrame, canonical_cols: list[str]) -> pd.DataFrame:
    """Renames TREASURY columns, normalizes, handles extras."""
    # Define the explicit mapping for TREASURY from HTML table header
    rename_map = {
        'Specific Id': 'native_id',
        'Bureau': 'office',
        'PSC': 'requirement_title',
        'Type of Requirement': 'requirement_type',
        'Place of Performance': 'place_raw',
        'Contract Type': 'contract_type',
        'NAICS': 'naics',
        'Estimated Total Contract Value': 'estimated_value_raw',
        'Type of Small Business Set-aside': 'set_aside',
        'Projected Award FY_Qtr': 'award_qtr_raw',
        'Project Period of Performance Start': 'solicitation_date'
    }
    logging.info(f"Applying TREASURY specific column mapping: {rename_map}")
    
    # Handle alternative native_id
    if 'Specific Id' not in df.columns and 'ShopCart/req' in df.columns:
        rename_map['ShopCart/req'] = 'native_id'
        logging.info("Using 'ShopCart/req' as native_id fallback.")
    elif 'Specific Id' not in df.columns and 'Contract Number' in df.columns:
         rename_map['Contract Number'] = 'native_id'
         logging.info("Using 'Contract Number' as native_id fallback.")
         
    rename_map_existing = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=rename_map_existing)

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
        parsed_values = df['estimated_value_raw'].apply(parse_value_range)
        df['estimated_value'] = parsed_values.apply(lambda x: x[0])
        df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
    else:
        df['estimated_value'], df['est_value_unit'] = pd.NA, pd.NA

    if 'award_qtr_raw' in df.columns:
        logging.info("Parsing 'award_qtr_raw'.")
        # Use updated fiscal_quarter_to_date which returns (date, year)
        parsed_award_info = df['award_qtr_raw'].apply(fiscal_quarter_to_date)
        df['award_date'] = parsed_award_info.apply(lambda x: x[0])
        df['award_fiscal_year'] = parsed_award_info.apply(lambda x: x[1])
    else:
        df['award_date'] = pd.NaT
        df['award_fiscal_year'] = pd.NA

    if 'solicitation_date' in df.columns:
        logging.info("Parsing 'solicitation_date'.")
        df['solicitation_date'] = pd.to_datetime(df['solicitation_date'], errors='coerce')
    else:
        df['solicitation_date'] = pd.NaT

    # Initialize missing columns
    if 'requirement_description' not in df.columns:
        df['requirement_description'] = pd.NA
        
    # Drop raw columns
    cols_to_drop = ['place_raw', 'estimated_value_raw', 'award_qtr_raw']
    df = df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore')

    # --- General normalization (lowercase, snake_case) ---
    df.columns = df.columns.str.strip().str.lower().str.replace(r'\s+\(.*?\)', '', regex=True).str.replace(r'\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)

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

    # Convert award_fiscal_year to nullable integer type
    if 'award_fiscal_year' in df.columns:
        df['award_fiscal_year'] = pd.to_numeric(df['award_fiscal_year'], errors='coerce').astype('Int64')

    final_cols_order = [col for col in normalized_canonical if col in df.columns]
    return df[final_cols_order]

# --- Main Transformation Function ---

def transform_treasury() -> pd.DataFrame | None:
    """Transforms the latest TREASURY forecast raw data."""
    canonical_cols = CANONICAL_COLUMNS
    latest_file = find_latest_raw_file(DATA_DIR)
    if not latest_file:
        logging.error(f"No raw data file found for TREASURY in {DATA_DIR}")
        return None

    try:
        # Removed sheet_name and engine as they don't apply to read_html
        header_row = 0 # Row 1 -> index 0

        # Treasury file seems to be HTML saved as .xls
        if latest_file.suffix == '.xls': 
            try:
                # read_html returns a list of DataFrames
                df_list = pd.read_html(latest_file, header=header_row)
                if not df_list:
                    raise ValueError("No tables found in the HTML file.")
                df = df_list[0] # Assume the first table is the correct one
                logging.info(f"Loaded {len(df)} rows from HTML file (saved as .xls): {latest_file}")
            except ValueError as e:
                 # Handle case where file might not be HTML or no tables found
                 logging.error(f"Could not read HTML table from {latest_file}: {e}")
                 return None
        elif latest_file.suffix in ['.xlsx', '.xlsm']:
            # Fallback logic if Treasury uses modern Excel in the future
            sheet_name = 'Sheet1' # Default assumption if not HTML
            engine = 'openpyxl'
            df = pd.read_excel(latest_file, sheet_name=sheet_name, header=header_row, engine=engine)
            logging.info(f"Loaded {len(df)} rows from Excel file {latest_file}, sheet '{sheet_name}'")
        elif latest_file.suffix == '.csv':
            # TODO: Determine correct header row and if on_bad_lines is needed for TREASURY CSV
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
        df_normalized = normalize_columns_treasury(df.copy(), canonical_cols)

        # Add source column
        df_normalized['source'] = 'TREASURY' # Using TREASURY as per initial request

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
        # export_path = os.path.join('data', 'processed', 'treasury.csv')
        # os.makedirs(os.path.dirname(export_path), exist_ok=True)
        # df_final.to_csv(export_path, index=False)
        # logging.info(f"Temporarily exported data to {export_path}")
        # END TEMPORARY EXPORT CODE
        
        # Upsert data to database
        try:
            logging.info(f"Attempting to upsert {len(df_final)} records for TREASURY.")
            bulk_upsert_prospects(df_final)
            logging.info(f"Successfully upserted TREASURY data.")
        except Exception as db_error:
            logging.error(f"Database upsert failed for TREASURY: {db_error}", exc_info=True)
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
    transformed_data = transform_treasury()
    if transformed_data is not None:
        print(transformed_data.head())
        print(f"\nTransformed DataFrame shape: {transformed_data.shape}")
        print(f"\nColumns: {transformed_data.columns.tolist()}") 