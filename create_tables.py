from src.database.models import Base
from src.database.db_session_manager import engine

def create_all_tables():
    print("Creating all database tables...")
    Base.metadata.create_all(engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    create_all_tables() 