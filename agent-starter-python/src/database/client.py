import os
from typing import Optional
from urllib.parse import quote

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
_engine: Optional[Engine] = None

def get_db_url() -> str:
    db_url = os.getenv("POSTGRES_URL")
    if db_url:
        return db_url

    # Fallback to components
    user = os.getenv("POSTGRES_USER") or os.getenv("user")
    password = os.getenv("POSTGRES_PASSWORD") or os.getenv("password")
    host = os.getenv("POSTGRES_HOST") or os.getenv("host")
    port = os.getenv("POSTGRES_PORT") or os.getenv("port")
    dbname = os.getenv("POSTGRES_DB") or os.getenv("dbname")
    if not all([user, password, host, port, dbname]):
        raise RuntimeError(
            "Database URL not set. Provide POSTGRES_URL or all of POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB"
        )
    user_enc = quote(user, safe="")
    password_enc = quote(password, safe="")
    return f"postgresql+psycopg://{user_enc}:{password_enc}@{host}:{port}/{dbname}"


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    db_url = get_db_url()
    _engine = create_engine(db_url, pool_pre_ping=True)
    return _engine