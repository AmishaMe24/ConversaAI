from sqlalchemy import text
from .models import metadata
from .client import get_engine

def ensure_providers_schema() -> None:
    engine = get_engine()
    # Ensure pgvector extension is available
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    # Create tables and indexes
    metadata.create_all(engine)