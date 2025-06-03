import pandas as pd
import os

# Define paths
csv_file_path = 'tests/fixtures/golden_files/doc_scraper/doc_sample_data.csv'
excel_file_path = 'tests/fixtures/golden_files/doc_scraper/doc_sample.xlsx'
# Sheet name from DOCConfig: "Sheet1"
# Header from DOCConfig: 2 (row 3 in Excel)
sheet_name = 'Sheet1' 

# Read the CSV data.
# The CSV has headers on the 3rd line (index 2).
# The first 2 lines are blank in the CSV to simulate the structure.
df = pd.read_csv(csv_file_path, header=2, keep_default_na=True)

# Create an ExcelWriter object
os.makedirs(os.path.dirname(excel_file_path), exist_ok=True)

with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
    # Write the DataFrame to Excel.
    # The header will be on row 3 (0-indexed startrow=2 for pandas).
    df.to_excel(writer, sheet_name=sheet_name, index=False, header=True, startrow=2)

print(f"Excel file '{excel_file_path}' created successfully with sheet '{sheet_name}' and data starting at row 4 (header on row 3).")

# Verify by reading back (optional)
# check_df = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=2)
# print("Verification read:")
# print(check_df.head())
# print(f"Columns: {check_df.columns.tolist()}")
