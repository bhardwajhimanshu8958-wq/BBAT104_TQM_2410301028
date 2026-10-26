import os
import threading
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import Engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "parking_management.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine with thread-safety settings and WAL-mode support
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
)

# Re-entrant lock to ensure race condition safety during atomic reservation operations
db_write_lock = threading.RLock()

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Enables SQLite Write-Ahead Logging (WAL) mode and configures busy timeouts
    for high-concurrency read/write transactions.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    FastAPI dependency that yields an independent database session per request
    and guarantees safe cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
