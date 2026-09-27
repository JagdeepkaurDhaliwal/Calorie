from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# Ensure parent directory exists if using file-based SQLite (e.g. /tmp)
if settings.database_url.startswith("sqlite"):
    try:
        clean_path = settings.database_url.replace("sqlite:////", "/").replace("sqlite:///", "")
        if clean_path and clean_path != ":memory:":
            db_path = Path(clean_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(settings.database_url, connect_args=connect_args)
except Exception:
    # Graceful fallback to memory SQLite if file database cannot be accessed
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_on_connect(dbapi_connection, _connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        except Exception:
            pass


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
