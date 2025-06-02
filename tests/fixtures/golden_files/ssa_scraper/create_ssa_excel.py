import pandas as pd
import os

# Define paths
csv_file_path = 'tests/fixtures/golden_files/ssa_scraper/ssa_sample_data.csv'
excel_file_path = 'tests/fixtures/golden_files/ssa_scraper/ssa_sample.xlsx'
sheet_name = 'Sheet1' # As expected by SSAConfig's read_options

# Read the CSV, assuming the first 4 rows are blank as per the example structure,
# and row 5 is the header. So, header is at index 4 when reading.
# The CSV was created with blank lines, so pandas read_csv should handle them as empty.
# We need to ensure no header is inferred from first few rows of CSV and then write to excel
# such that the actual headers are on the 5th row (index 4 for header param in read_excel).

# Read the CSV data, effectively skipping the initial blank rows by how we'll write it.
# The header argument in read_csv refers to which row in the CSV contains the headers.
# Our CSV has headers on the 5th line (index 4).
df = pd.read_csv(csv_file_path, header=4, keep_default_na=True)

# Create an ExcelWriter object
# Ensure the target directory exists
os.makedirs(os.path.dirname(excel_file_path), exist_ok=True)

with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
    # Write the DataFrame to Excel, starting from row 5 (1-indexed in Excel, so startrow=4 for 0-indexed pandas)
    # This means there will be 4 blank rows above the header row in the Excel sheet.
    # The header itself will be written by pandas.
    df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=4)

print(f"Excel file '{excel_file_path}' created successfully with data starting at row 6 (header on row 5).")

# Verify by reading back (optional, for debugging the script itself)
# check_df = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=4) # header=4 means 5th row
# print("Verification read:")
# print(check_df.head())
# print(f"Columns: {check_df.columns.tolist()}")
