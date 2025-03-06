import sqlite3
import requests
import time
import datetime
import os
import json
from urllib.parse import urlparse

def check_source_health(url):
    """Check if a data source is healthy by making a request to its URL."""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=10)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            return "working", None, response_time
        else:
            return "not_working", f"HTTP status code: {response.status_code}", response_time
    except requests.exceptions.RequestException as e:
        return "not_working", str(e), 0

def is_valid_url(url):
    """Check if a URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def run_health_checks():
    """Run health checks for all data sources and update their status."""
    print("Starting health checks...")
    
    # Connect to the database
    db_path = os.path.join('data', 'proposals.db')
    print(f"Database path: {db_path}")
    print(f"Database exists: {os.path.exists(db_path)}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all data sources
    cursor.execute("SELECT id, name, url FROM data_sources")
    data_sources = cursor.fetchall()
    print(f"Found {len(data_sources)} data sources")
    
    # Check health for each data source
    for source in data_sources:
        source_id = source['id']
        name = source['name']
        url = source['url']
        
        print(f"\nChecking health for source {source_id}: {name}")
        print(f"URL: {url}")
        
        if not url or not is_valid_url(url):
            status = "unknown"
            error_message = "Invalid or missing URL"
            response_time = 0
            print(f"Status: {status} - {error_message}")
        else:
            status, error_message, response_time = check_source_health(url)
            print(f"Status: {status}")
            if error_message:
                print(f"Error: {error_message}")
            print(f"Response time: {response_time:.2f}s")
        
        # Insert the status into the scraper_status table
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute(
                "INSERT INTO scraper_status (source_id, status, last_checked, error_message, response_time) "
                "VALUES (?, ?, ?, ?, ?)",
                (source_id, status, timestamp, error_message, response_time)
            )
            conn.commit()
            print(f"Status record inserted successfully for source {source_id}")
        except sqlite3.Error as e:
            print(f"Error inserting status record: {e}")
            conn.rollback()
    
    # Verify the inserted records
    cursor.execute("SELECT * FROM scraper_status ORDER BY last_checked DESC LIMIT 20")
    records = cursor.fetchall()
    print("\nLatest 20 records in scraper_status table:")
    for record in records:
        print(f"- Source {record['source_id']}: {record['status']} at {record['last_checked']} (Response time: {record['response_time']:.2f}s)")
        if record['error_message']:
            print(f"  Error: {record['error_message']}")
    
    # Close the database connection
    cursor.close()
    conn.close()
    print("\nHealth checks completed")

if __name__ == "__main__":
    run_health_checks() 