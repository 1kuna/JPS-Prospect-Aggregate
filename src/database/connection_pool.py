"""
Database connection pool implementation with improved error handling and monitoring.

This module provides a robust connection pool for database operations with features like:
- Connection health checks
- Automatic reconnection
- Connection statistics tracking
- Configurable pool size and timeout
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
import os
from dotenv import load_dotenv
from src.exceptions import DatabaseError

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Connection pool configuration
DEFAULT_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DEFAULT_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DEFAULT_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DEFAULT_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour

class ConnectionStats:
    """Track statistics about database connections."""
    
    def __init__(self):
        self.total_connections_created = 0
        self.total_connections_closed = 0
        self.total_checkouts = 0
        self.total_checkins = 0
        self.checkout_times: List[float] = []
        self.current_connections = 0
        self.max_concurrent_connections = 0
        self.connection_errors = 0
        self.last_error: Optional[str] = None
        self.last_error_time: Optional[float] = None
        self._lock = threading.RLock()
    
    def connection_created(self):
        """Track a new connection being created."""
        with self._lock:
            self.total_connections_created += 1
            self.current_connections += 1
            if self.current_connections > self.max_concurrent_connections:
                self.max_concurrent_connections = self.current_connections
    
    def connection_closed(self):
        """Track a connection being closed."""
        with self._lock:
            self.total_connections_closed += 1
            self.current_connections -= 1
    
    def connection_checkout(self):
        """Track a connection being checked out from the pool."""
        with self._lock:
            self.total_checkouts += 1
    
    def connection_checkin(self, checkout_time: float):
        """Track a connection being checked back into the pool."""
        with self._lock:
            self.total_checkins += 1
            self.checkout_times.append(checkout_time)
            # Keep only the last 100 checkout times
            if len(self.checkout_times) > 100:
                self.checkout_times.pop(0)
    
    def connection_error(self, error: str):
        """Track a connection error."""
        with self._lock:
            self.connection_errors += 1
            self.last_error = error
            self.last_error_time = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current connection statistics."""
        with self._lock:
            avg_checkout_time = sum(self.checkout_times) / len(self.checkout_times) if self.checkout_times else 0
            return {
                "total_connections_created": self.total_connections_created,
                "total_connections_closed": self.total_connections_closed,
                "current_connections": self.current_connections,
                "max_concurrent_connections": self.max_concurrent_connections,
                "total_checkouts": self.total_checkouts,
                "total_checkins": self.total_checkins,
                "avg_checkout_time": avg_checkout_time,
                "connection_errors": self.connection_errors,
                "last_error": self.last_error,
                "last_error_time": self.last_error_time
            }

class DatabaseConnectionPool:
    """Manages a pool of database connections with improved error handling and monitoring."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'DatabaseConnectionPool':
        """Get the singleton instance of the connection pool."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize the database connection pool."""
        if DatabaseConnectionPool._instance is not None:
            raise RuntimeError("Use get_instance() to get the singleton instance")
        
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///data/proposals.db")
        self.stats = ConnectionStats()
        self.engine = self._create_engine()
        self._setup_event_listeners()
    
    def _create_engine(self) -> Engine:
        """Create the SQLAlchemy engine with connection pooling."""
        connect_args = {}
        if self.database_url.startswith('sqlite'):
            connect_args["check_same_thread"] = False
        
        engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=DEFAULT_POOL_SIZE,
            max_overflow=DEFAULT_MAX_OVERFLOW,
            pool_timeout=DEFAULT_POOL_TIMEOUT,
            pool_recycle=DEFAULT_POOL_RECYCLE,
            pool_pre_ping=True,  # Check connection validity before using
            connect_args=connect_args,
            echo=os.getenv("SQL_ECHO", "False").lower() == "true"
        )
        
        return engine
    
    def _setup_event_listeners(self):
        """Set up event listeners for connection pool events."""
        
        @event.listens_for(self.engine, "connect")
        def connect(dbapi_connection, connection_record):
            """Log when a connection is created."""
            logger.debug("Database connection established")
            self.stats.connection_created()
            
            # For SQLite connections, enable foreign keys
            if self.database_url.startswith('sqlite'):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        
        @event.listens_for(self.engine, "checkout")
        def checkout(dbapi_connection, connection_record, connection_proxy):
            """Verify that the connection is still valid when it's checked out from the pool."""
            logger.debug("Database connection checked out from pool")
            self.stats.connection_checkout()
            connection_record.info.setdefault('checkout_time', time.time())
            
            # Verify the connection is still valid
            if self.database_url.startswith('sqlite'):
                try:
                    cursor = dbapi_connection.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                except Exception as e:
                    self.stats.connection_error(str(e))
                    logger.warning(f"Connection invalid: {e}")
                    connection_proxy._pool.dispose()
                    raise DisconnectionError("Connection invalid")
        
        @event.listens_for(self.engine, "checkin")
        def checkin(dbapi_connection, connection_record):
            """Log when a connection is returned to the pool."""
            logger.debug("Database connection returned to pool")
            checkout_time = connection_record.info.get('checkout_time')
            if checkout_time is not None:
                connection_time = time.time() - checkout_time
                connection_record.info.pop('checkout_time', None)
                self.stats.connection_checkin(connection_time)
                logger.debug(f"Connection was checked out for {connection_time:.2f} seconds")
                if connection_time > 300:  # 5 minutes
                    logger.warning(f"Connection was checked out for a long time: {connection_time:.2f} seconds")
        
        @event.listens_for(self.engine, "close")
        def close(dbapi_connection, connection_record):
            """Log when a connection is closed."""
            logger.debug("Database connection closed")
            self.stats.connection_closed()
    
    def get_engine(self) -> Engine:
        """Get the SQLAlchemy engine."""
        return self.engine
    
    def check_connection(self) -> bool:
        """Check if the database connection is valid."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as e:
            self.stats.connection_error(str(e))
            logger.error(f"Database connection check failed: {e}")
            return False
    
    def dispose(self):
        """Dispose of all connections in the pool."""
        try:
            self.engine.dispose()
            logger.info("Database connection pool disposed")
        except Exception as e:
            self.stats.connection_error(str(e))
            logger.error(f"Error disposing database connection pool: {e}")
            raise DatabaseError(f"Failed to dispose database connection pool: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current connection pool statistics."""
        engine_stats = {
            "pool_size": self.engine.pool.size(),
            "checkedin": self.engine.pool.checkedin(),
            "checkedout": self.engine.pool.checkedout(),
            "overflow": self.engine.pool.overflow(),
        }
        return {**self.stats.get_stats(), **engine_stats}

# Singleton instance getter
def get_connection_pool() -> DatabaseConnectionPool:
    """Get the singleton instance of the database connection pool."""
    return DatabaseConnectionPool.get_instance()

# Convenience function to get the engine
def get_engine() -> Engine:
    """Get the SQLAlchemy engine from the connection pool."""
    return get_connection_pool().get_engine() 