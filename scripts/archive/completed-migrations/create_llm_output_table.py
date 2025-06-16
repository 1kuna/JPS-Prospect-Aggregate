#!/usr/bin/env python3
"""
Create the LLMOutput table in the database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db
from app.database.models import LLMOutput
from app import create_app

def create_llm_output_table():
    """Create the LLMOutput table"""
    app = create_app()
    
    with app.app_context():
        # Create the table
        db.create_all()
        print("LLMOutput table created successfully!")

if __name__ == "__main__":
    create_llm_output_table()