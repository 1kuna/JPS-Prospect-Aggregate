import requests
import sys

url = "https://www.state.gov/wp-content/uploads/2025/02/FY25-Procurement-Forecast-2.xlsx"
output_path = "temp/dos_file_head.txt"
headers_output_path = "temp/dos_headers.txt" # To capture headers for sure

print(f"--- Attempting to download from URL: {url} ---")
sys.stdout.flush()

try:
    response = requests.get(url, allow_redirects=True, timeout=30, stream=True)

    print(f"Status Code: {response.status_code}")
    sys.stdout.flush()

    content_type = response.headers.get('Content-Type', 'Not Specified')
    print(f"Content-Type: {content_type}")
    sys.stdout.flush()

    # Save headers to a file for reliable capture
    with open(headers_output_path, "w") as hf:
        hf.write(f"Status Code: {response.status_code}\n")
        hf.write(f"Content-Type: {content_type}\n")
        hf.write("\nAll Headers:\n")
        for k, v in response.headers.items():
            hf.write(f"{k}: {v}\n")
    print(f"--- Headers saved to {headers_output_path} ---")
    sys.stdout.flush()

    # Read and save the first 500 bytes
    first_500_bytes = response.raw.read(500)

    with open(output_path, "wb") as f: # Write in binary mode
        f.write(first_500_bytes)

    print(f"--- First 500 bytes saved to {output_path} ---")
    sys.stdout.flush()

    # Preliminary content check
    if 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type:
        print("Content-Type indicates an Excel file.")
    elif 'text/html' in content_type:
        print("Content-Type indicates HTML.")
        # Try decoding and printing a bit of HTML for confirmation
        try:
            print(f"First 100 bytes as text (if HTML): {first_500_bytes[:100].decode('utf-8', errors='ignore')}")
        except Exception:
            pass # Ignore if decoding fails
    elif first_500_bytes.startswith(b'PK\x03\x04'): # Common start for .xlsx (zip) files
        print("First bytes suggest a ZIP archive (likely Excel .xlsx).")
    elif b'<!DOCTYPE html>' in first_500_bytes.lower() or b'<html' in first_500_bytes.lower():
        print("First bytes suggest HTML content.")
    else:
        print("Content-Type is not definitive Excel, and first bytes do not strongly suggest HTML or ZIP/Excel.")
    sys.stdout.flush()

except requests.exceptions.RequestException as e:
    print(f"Error during request: {e}")
    sys.stdout.flush()
    # Save error to headers file if request failed
    with open(headers_output_path, "w") as hf:
        hf.write(f"Error during request: {e}\n")

print(f"--- Script finished ---")
sys.stdout.flush()
