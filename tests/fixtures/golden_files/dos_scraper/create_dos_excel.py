import pandas as pd
import os

# Define paths
csv_file_path = 'tests/fixtures/golden_files/dos_scraper/dos_sample_data.csv'
excel_file_path = 'tests/fixtures/golden_files/dos_scraper/dos_sample.xlsx'
# Sheet name from DOSConfig: "FY25-Procurement-Forecast"
# Header from DOSConfig: 0 (row 1 in Excel)
sheet_name = 'FY25-Procurement-Forecast' 

# Read the CSV data. Header is on the first line (index 0)
df = pd.read_csv(csv_file_path, header=0, keep_default_na=True)

# Create an ExcelWriter object
os.makedirs(os.path.dirname(excel_file_path), exist_ok=True)

with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
    # Write the DataFrame to Excel. Header will be on row 1 (index 0).
    df.to_excel(writer, sheet_name=sheet_name, index=False, header=True)

print(f"Excel file '{excel_file_path}' created successfully with sheet '{sheet_name}' and data starting at row 1 (header on row 1).")

# Verify by reading back (optional, for debugging the script itself)
# check_df = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=0)
# print("Verification read:")
# print(check_df.head())
# print(f"Columns: {check_df.columns.tolist()}")
