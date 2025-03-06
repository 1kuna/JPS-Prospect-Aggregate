import sqlite3
import os

def create_scraper_status_table():
    print("Starting script...")
    
    # Make sure the data directory exists
    os.makedirs('data', exist_ok=True)
    print(f"Data directory exists: {os.path.exists('data')}")
    
    # Connect to the database
    db_path = 'data/proposals.db'
    print(f"Database path: {os.path.abspath(db_path)}")
    print(f"Database exists: {os.path.exists(db_path)}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print("Connected to database")
        
        # Check if the table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scraper_status'")
        if cursor.fetchone():
            print("ScraperStatus table already exists")
        else:
            # Create the scraper_status table
            print("Creating ScraperStatus table...")
            cursor.execute('''
            CREATE TABLE scraper_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'unknown',
                last_checked DATETIME,
                error_message TEXT,
                response_time FLOAT,
                FOREIGN KEY (source_id) REFERENCES data_sources(id)
            )
            ''')
            print("ScraperStatus table created successfully")
        
        # Check all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Tables in database:")
        for table in tables:
            print(f"- {table[0]}")
        
        # Insert test records
        print("\nInserting test records...")
        try:
            # Delete any existing records
            cursor.execute("DELETE FROM scraper_status WHERE source_id IN (1, 2)")
            
            # Insert records for sources 1 and 2
            cursor.execute('''
            INSERT INTO scraper_status (source_id, status, last_checked, error_message, response_time)
            VALUES (1, 'working', CURRENT_TIMESTAMP, NULL, 0.5)
            ''')
            
            cursor.execute('''
            INSERT INTO scraper_status (source_id, status, last_checked, error_message, response_time)
            VALUES (2, 'working', CURRENT_TIMESTAMP, NULL, 0.5)
            ''')
            
            # Commit the changes
            conn.commit()
            print("Test records inserted successfully")
            
            # Verify the records were inserted
            cursor.execute("SELECT * FROM scraper_status")
            records = cursor.fetchall()
            print(f"Found {len(records)} records in scraper_status table:")
            for record in records:
                print(f"- {record}")
        except Exception as e:
            print(f"Error inserting test records: {e}")
        
        # Close the connection
        cursor.close()
        conn.close()
        print("Database connection closed")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_scraper_status_table() 