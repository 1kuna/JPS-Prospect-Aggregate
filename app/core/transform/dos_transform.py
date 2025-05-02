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
from app.utils.parsing import parse_value_range, fiscal_quarter_to_date
from app.database.crud import bulk_upsert_prospects

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
    'award_date', 'award_fiscal_year', 'office', 'place_city', 'place_state', 'place_country',
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
    original_cols = df.columns.tolist()
    
    # Define the explicit mapping for DOS from Excel header
    rename_map = {
        # Raw DOS Name: Canonical Name
        'Contract Number': 'native_id',
        'Office Symbol': 'office',
        'Requirement Title': 'requirement_title',
        'Requirement Description': 'requirement_description',
        'Estimated Value': 'estimated_value_raw', # Raw - Primary
        'Dollar Value': 'dollar_value_raw',       # Raw - Secondary
        'Place of Performance Country': 'place_country',
        'Place of Performance City': 'place_city',
        'Place of Performance State': 'place_state',
        'Award Type': 'contract_type',
        'Anticipated Award Date': 'award_date_raw', # Raw - Primary Date
        'Target Award Quarter': 'award_qtr_raw',    # Raw - Secondary Quarter
        'Fiscal Year': 'award_fiscal_year_raw', # Added direct FY mapping
        'Anticipated Set Aside': 'set_aside',
        'Anticipated Solicitation Release Date': 'solicitation_date' 
        # NAICS code not present in source
    }
    logging.info(f"Applying DOS specific column mapping: {rename_map}")
    rename_map_existing = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=rename_map_existing)

    # --- Handle potential alternative/derived fields ---
    # Award Date/Year Parsing (Priority: FY column -> Date col -> Quarter col)
    df['award_date'] = pd.NaT # Initialize columns
    df['award_fiscal_year'] = pd.NA

    # 1. Try parsing direct Fiscal Year column first
    if 'award_fiscal_year_raw' in df.columns:
        df['award_fiscal_year'] = pd.to_numeric(df['award_fiscal_year_raw'], errors='coerce')
        logging.info("Processed 'Fiscal Year' column for award_fiscal_year.")

    # 2. Try parsing Anticipated Award Date (if FY parse failed or didn't exist)
    if 'award_date_raw' in df.columns:
        # Attempt direct parsing of the date
        parsed_date = pd.to_datetime(df['award_date_raw'], errors='coerce')
        # Update award_date where parsing worked
        df['award_date'] = df['award_date'].fillna(parsed_date) 
        
        # Update award_fiscal_year *only if it's still missing* and date parse worked
        needs_fy_from_date_mask = df['award_fiscal_year'].isna() & parsed_date.notna()
        if needs_fy_from_date_mask.any():
            logging.info("Using year from 'Anticipated Award Date' as fallback for award_fiscal_year.")
            df.loc[needs_fy_from_date_mask, 'award_fiscal_year'] = parsed_date[needs_fy_from_date_mask].dt.year

    # 3. Try parsing Target Award Quarter (if both FY and Date parse failed/missing)
    if 'award_qtr_raw' in df.columns:
        # Identify rows where award_date is still NaT (meaning direct date failed or was missing)
        # AND award_fiscal_year is still NA (meaning direct FY failed or was missing)
        needs_qtr_parse_mask = df['award_date'].isna() & df['award_fiscal_year'].isna() & df['award_qtr_raw'].notna()
        if needs_qtr_parse_mask.any():
            logging.info("Using 'Target Award Quarter' as final fallback for award date/year.")
            # Apply fiscal_quarter_to_date only to rows needing it
            parsed_qtr_info = df.loc[needs_qtr_parse_mask, 'award_qtr_raw'].apply(fiscal_quarter_to_date)
            # Update award_date and award_fiscal_year using the tuple returned
            df.loc[needs_qtr_parse_mask, 'award_date'] = parsed_qtr_info.apply(lambda x: x[0])
            df.loc[needs_qtr_parse_mask, 'award_fiscal_year'] = parsed_qtr_info.apply(lambda x: x[1])

    # --- End Award Date/Year Parsing ---

    # Estimated Value Parsing (Prioritize 'estimated_value_raw', then 'dollar_value_raw')
    if 'estimated_value_raw' in df.columns:
        logging.info("Parsing 'estimated_value_raw' as primary value source.")
        parsed_values = df['estimated_value_raw'].apply(parse_value_range)
        df['estimated_value'] = parsed_values.apply(lambda x: x[0])
        df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
    elif 'dollar_value_raw' in df.columns:
        logging.info("Parsing 'dollar_value_raw' as secondary value source.")
        # Assume 'Dollar Value' is just a number if it exists as secondary
        df['estimated_value'] = pd.to_numeric(df['dollar_value_raw'], errors='coerce')
        df['est_value_unit'] = None # No unit context if it's just 'Dollar Value'
    else:
        df['estimated_value'] = pd.NA
        df['est_value_unit'] = pd.NA

    # Solicitation Date Parsing
    if 'solicitation_date' in df.columns:
        logging.info("Parsing 'solicitation_date'.")
        df['solicitation_date'] = pd.to_datetime(df['solicitation_date'], errors='coerce')
    else:
         df['solicitation_date'] = pd.NaT
         
    # Initialize NAICS if missing
    if 'naics' not in df.columns:
        df['naics'] = pd.NA
        
    # Initialize Place columns if missing
    if 'place_city' not in df.columns: df['place_city'] = pd.NA
    if 'place_state' not in df.columns: df['place_state'] = pd.NA
    if 'place_country' not in df.columns: df['place_country'] = 'USA' # Default

    # Drop raw columns used only for parsing
    cols_to_drop = ['estimated_value_raw', 'dollar_value_raw', 'award_date_raw', 'award_qtr_raw', 'award_fiscal_year_raw']
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
             # Check if the column dtype suggests it might be datetime-like
             if pd.api.types.is_datetime64_any_dtype(df[col]):
                 # Convert datetime-like columns to string safely
                 df[col] = df[col].astype(str)
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

        # TEMPORARY EXPORT CODE - COMMENTED OUT
        # export_path = os.path.join('data', 'processed', 'dos.csv')
        # os.makedirs(os.path.dirname(export_path), exist_ok=True)
        # df_final.to_csv(export_path, index=False)
        # logging.info(f"Temporarily exported data to {export_path}")
        # END TEMPORARY EXPORT CODE

        # Upsert data to database
        try:
            logging.info(f"Attempting to upsert {len(df_final)} records for DOS.")
            bulk_upsert_prospects(df_final)
            logging.info(f"Successfully upserted DOS data.")
        except Exception as db_error:
            logging.error(f"Database upsert failed for DOS: {db_error}", exc_info=True)
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
    transformed_data = transform_dos()
    if transformed_data is not None:
        print(transformed_data.head())
        print(f"\nTransformed DataFrame shape: {transformed_data.shape}")
        print(f"\nColumns: {transformed_data.columns.tolist()}") 