import pandas as pd
import os

# Define paths
csv_file_path = 'tests/fixtures/golden_files/doj_scraper/doj_sample_data.csv'
excel_file_path = 'tests/fixtures/golden_files/doj_scraper/doj_sample.xlsx'
# Sheet name from DOJConfig: "Contracting Opportunities Data"
# Header from DOJConfig: 12 (row 13 in Excel)
sheet_name = 'Contracting Opportunities Data' 

# Read the CSV data.
# The CSV has headers on the 13th line (index 12).
# The first 12 lines are blank in the CSV to simulate the structure.
df = pd.read_csv(csv_file_path, header=12, keep_default_na=True)

# Create an ExcelWriter object
os.makedirs(os.path.dirname(excel_file_path), exist_ok=True)

with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
    # Write the DataFrame to Excel.
    # The header will be on row 13 (0-indexed startrow=12 for pandas).
    df.to_excel(writer, sheet_name=sheet_name, index=False, header=True, startrow=12)

print(f"Excel file '{excel_file_path}' created successfully with sheet '{sheet_name}' and data starting at row 14 (header on row 13).")

# Verify by reading back (optional)
# check_df = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=12)
# print("Verification read:")
# print(check_df.head())
# print(f"Columns: {check_df.columns.tolist()}")
