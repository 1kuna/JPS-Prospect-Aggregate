from contextlib import contextmanager
from functools import wraps
from typing import Generator, TypeVar, Callable, Any

from sqlalchemy.orm import Session
from src.database.session import SessionLocal

T = TypeVar('T')

@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Automatically handles session creation, commit/rollback, and cleanup.
    
    Usage:
        with db_session() as session:
            result = session.query(Model).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def with_db_session(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that provides a database session to the decorated function.
    The session is automatically managed and cleaned up.
    
    Usage:
        @with_db_session
        def get_user(session: Session, user_id: int):
            return session.query(User).filter(User.id == user_id).first()
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        with db_session() as session:
            return func(session, *args, **kwargs)
    return wrapper 