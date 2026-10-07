from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import get_settings
from pathlib import Path

settings = get_settings()
is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine_options = {"connect_args": connect_args, "pool_pre_ping": not is_sqlite}
# An in-memory SQLite database needs one shared connection so API/test sessions
# see the same schema. File SQLite and PostgreSQL use their normal pools.
if settings.database_url in {"sqlite://", "sqlite:///:memory:"}:
    engine_options["poolclass"] = StaticPool
engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass


def upgrade_database() -> None:
    """Apply the idempotent Alembic migrations before serving requests.

    ``create_all`` creates missing tables but never adds columns to an existing
    table. Production began with the earlier trusted-contacts table, so relying
    on it alone left that table incompatible with the current ORM. Running the
    migrations here keeps a serverless deployment from starting against a stale
    schema. All revisions are written to be safe for fresh, current databases.
    """
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
