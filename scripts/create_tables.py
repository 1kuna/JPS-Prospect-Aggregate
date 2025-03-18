from src.database.models import Base
from src.database.db import engine, init_db

def create_all_tables():
    print("Creating all database tables...")
    init_db()
    print("Tables created successfully!")

if __name__ == "__main__":
    create_all_tables() 