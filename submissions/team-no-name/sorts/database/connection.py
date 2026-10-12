from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from contextlib import contextmanager
from sorts.config import settings

# Declare the declarative base for models
Base = declarative_base()

# Configure engine. For SQLite, check_same_thread=False allows multi-threaded Discord bot tasks to reuse connection safely.
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

# Session local factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Scoped session helper
db_session = scoped_session(SessionLocal)

@contextmanager
def get_db():
    """Context manager for transaction management and session cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_db():
    """Creates all database tables defined by models and performs lightweight schema migrations."""
    Base.metadata.create_all(bind=engine)

    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "clubs" in inspector.get_table_names():
        existing_cols = {col["name"] for col in inspector.get_columns("clubs")}
        new_cols = {
            "category": "VARCHAR(100)",
            "official": "BOOLEAN DEFAULT 1",
            "linkedin": "VARCHAR(255)",
            "github": "VARCHAR(255)",
            "youtube": "VARCHAR(255)",
            "linktree": "VARCHAR(255)",
            "beacons": "VARCHAR(255)",
            "aliases_json": "TEXT DEFAULT '[]'",
            "verification_json": "TEXT DEFAULT '{}'",
            "socials_json": "TEXT DEFAULT '{}'",
            "club_metadata_json": "TEXT DEFAULT '{}'"
        }
        with engine.connect() as conn:
            for col_name, col_type in new_cols.items():
                if col_name not in existing_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE clubs ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass
