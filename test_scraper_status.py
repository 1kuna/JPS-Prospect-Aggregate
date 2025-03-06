from src.database.db import get_session, close_session, session_scope
from src.database.models import ScraperStatus, DataSource
from datetime import datetime
import traceback
import time
from sqlalchemy import text

def test_insert_scraper_status():
    print("Starting test...")
    
    # First, check if there are any data sources
    with session_scope() as session:
        data_sources = session.query(DataSource).all()
        print(f"Found {len(data_sources)} data sources:")
        for source in data_sources:
            print(f"ID: {source.id}, Name: {source.name}")
    
    # Check if there are any existing ScraperStatus records
    with session_scope() as session:
        existing_statuses = session.query(ScraperStatus).all()
        print(f"Found {len(existing_statuses)} existing ScraperStatus records")
    
    # Try to insert a new ScraperStatus record for source 1
    print("Trying to insert ScraperStatus for source 1...")
    try:
        with session_scope() as session:
            # Delete any existing status records for this source
            session.query(ScraperStatus).filter(ScraperStatus.source_id == 1).delete()
            
            # Create a new status record
            new_status = ScraperStatus(
                source_id=1,
                status="working",
                last_checked=datetime.utcnow(),
                error_message=None,
                response_time=0.5
            )
            session.add(new_status)
            # Commit happens automatically when the session_scope context manager exits
        print("Successfully added ScraperStatus record for source 1")
    except Exception as e:
        print(f"Error adding ScraperStatus for source 1: {e}")
        print(f"Traceback: {traceback.format_exc()}")
    
    # Wait a moment to ensure the transaction completes
    time.sleep(1)
    
    # Check if the record was inserted
    with session_scope() as session:
        final_statuses = session.query(ScraperStatus).all()
        print(f"Found {len(final_statuses)} ScraperStatus records after insertion:")
        for status in final_statuses:
            print(f"ID: {status.id}, Source ID: {status.source_id}, Status: {status.status}")
    
    # Try direct SQL insertion as a last resort
    print("\nTrying direct SQL insertion...")
    try:
        with session_scope() as session:
            # Use raw SQL to insert a record with text() function
            session.execute(
                text("INSERT INTO scraper_status (source_id, status, last_checked, response_time) VALUES (2, 'working', CURRENT_TIMESTAMP, 0.5)")
            )
            # Commit happens automatically when the session_scope context manager exits
        print("Successfully added ScraperStatus record for source 2 using direct SQL")
    except Exception as e:
        print(f"Error adding ScraperStatus using direct SQL: {e}")
        print(f"Traceback: {traceback.format_exc()}")
    
    # Wait a moment to ensure the transaction completes
    time.sleep(1)
    
    # Final check
    with session_scope() as session:
        final_statuses = session.query(ScraperStatus).all()
        print(f"Found {len(final_statuses)} ScraperStatus records after direct SQL insertion:")
        for status in final_statuses:
            print(f"ID: {status.id}, Source ID: {status.source_id}, Status: {status.status}")

if __name__ == "__main__":
    test_insert_scraper_status() 