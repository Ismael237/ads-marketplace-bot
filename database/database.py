"""
Database configuration and session management for Bot Marketplace
Simplified: provide minimal engine and session helpers
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
import config
from utils.logger import get_logger

# Initialize logger
logger = get_logger("database")

# Create engine and session factory (simple configuration)
engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    echo=(config.LOG_LEVEL == "DEBUG"),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_database_engine():
    """Return the already configured engine (kept for compatibility)."""
    return engine


def create_session_factory():
    """Return the already configured session factory (kept for compatibility)."""
    return SessionLocal


def init_database():
    """Initialize the database and create all tables"""
    try:
        # Import models to ensure they are registered
        from database.models import Base
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions (no auto-commit)
    Caller is responsible for commit/rollback.
    """
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI or similar frameworks
    Returns a database session
    """
    with get_db_session() as session:
        yield session
# Initialize database objects at import
try:
    init_database()
    logger.info("Database module initialized")
except Exception as e:
    logger.error(f"Database initialization error: {e}")
