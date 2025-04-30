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

# Specific data directory for TREASURY
DATA_DIR = BASE_DIR / "data" / "raw" / "treasury_forecast"

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

# --- Normalization Function (TREASURY specific) ---

def normalize_columns_treasury(df: pd.DataFrame, canonical_cols: list[str]) -> pd.DataFrame:
    """Renames TREASURY columns, normalizes, handles extras."""
    # Define the explicit mapping for TREASURY from HTML table header
    rename_map = {
        # Raw TREASURY Name: Canonical Name
        'Specific Id': 'native_id', # Primary choice for ID
        'Bureau': 'office',
        'Type of Requirement': 'requirement_title',
        # Description appears missing
        'Place of Performance': 'place_raw', # Needs splitting
        'Contract Type': 'contract_type',
        'NAICS': 'naics',
        'Estimated Total Contract Value': 'estimated_value', # Needs parsing
        'Type of Small Business Set-aside': 'set_aside',
        'Projected Award FY_Qtr': 'award_date', # Needs FY+Quarter parsing
        'Projected Period of Performance Start': 'solicitation_date' # Assumption, needs date parsing
    }
    logging.info(f"Applying TREASURY specific column mapping: {rename_map}")
    
    # Handle alternative native_id if 'Specific Id' is missing
    if 'Specific Id' not in df.columns and 'ShopCart/req' in df.columns:
        rename_map['ShopCart/req'] = 'native_id'
        logging.info("Using 'ShopCart/req' as native_id fallback.")
    elif 'Specific Id' not in df.columns and 'Contract Number' in df.columns:
         rename_map['Contract Number'] = 'native_id'
         logging.info("Using 'Contract Number' as native_id fallback.")
         
    # Apply renaming
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

    # TODO: Implement parsing for 'award_date' from FY_Qtr.
    if 'award_date' in df.columns:
        logging.info("'award_date' requires FY+Quarter parsing.")
        df['award_date'] = pd.NA # Set to NA until implemented

    # TODO: Implement parsing for 'solicitation_date'.
    if 'solicitation_date' in df.columns:
        logging.info("'solicitation_date' requires parsing.")
        df['solicitation_date'] = pd.to_datetime(df['solicitation_date'], errors='coerce')

    # Initialize missing columns
    df['requirement_description'] = pd.NA

    # --- General normalization (lowercase, snake_case) ---
    df.columns = df.columns.str.strip().str.lower().str.replace(r'\s+\(.*?\)', '', regex=True).str.replace(r'\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)

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
        
        df_final = df_normalized[[col for col in final_ordered_cols if col in df_normalized.columns]]

        logging.info(f"TREASURY Transformation complete. Processed {len(df_final)} rows.")
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