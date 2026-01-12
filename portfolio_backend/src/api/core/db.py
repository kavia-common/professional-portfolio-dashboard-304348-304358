from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.api.core.config import settings


def _create_engine():
    # Use psycopg2-binary driver implicitly via SQLAlchemy URL scheme.
    db_url = settings.resolve_database_url()
    return create_engine(db_url, pool_pre_ping=True)


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# PUBLIC_INTERFACE
def get_db() -> Session:
    """FastAPI dependency that yields a SQLAlchemy Session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
