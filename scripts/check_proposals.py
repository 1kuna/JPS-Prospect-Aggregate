from src.database.db_session_manager import session_scope
from src.database.models import Proposal

def main():
    with session_scope() as session:
        total_count = session.query(Proposal).count()
        print(f"Total proposals in database: {total_count}")

if __name__ == "__main__":
    main() 