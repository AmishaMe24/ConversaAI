import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.dialects.postgresql import insert
from sentence_transformers import SentenceTransformer

from database import ensure_providers_schema
from database.client import get_engine
from database.models import providers_table

logger = logging.getLogger("agent")


def _default_data_path() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    return str(repo_root / "data" / "providerlist.json")


def _normalize_list(values: Optional[List[Any]]) -> List[str]:
    if not values:
        return []
    out: List[str] = []
    for v in values:
        if v is None:
            continue
        out.append(str(v))
    return out


def upsert_providers(engine, providers: List[Dict[str, Any]], batch_size: int = 500) -> int:
    rows: List[Dict[str, Any]] = []
    texts: List[str] = []
    for p in providers:
        addr = p.get("address", {}) or {}
        languages = _normalize_list(p.get("languages"))
        insurance = _normalize_list(p.get("insurance_accepted"))
        desc = " ".join(
            [
                str(p.get("full_name") or ""),
                str(p.get("specialty") or ""),
                str(addr.get("city") or ""),
                str(addr.get("state") or ""),
                ",".join(languages),
                ",".join(insurance),
            ]
        ).strip()
        texts.append(desc)
        rows.append(
            {
                "id": p.get("id"),
                "full_name": p.get("full_name"),
                "specialty": p.get("specialty"),
                "phone": p.get("phone"),
                "email": p.get("email"),
                "address_street": addr.get("street"),
                "address_city": addr.get("city"),
                "address_state": addr.get("state"),
                "address_postal_code": addr.get("postal_code"),
                "years_experience": p.get("years_experience"),
                "accepting_new_patients": p.get("accepting_new_patients"),
                "insurance_accepted": insurance,
                "rating": p.get("rating"),
                "license_number": p.get("license_number"),
                "board_certified": p.get("board_certified"),
                "languages": languages,
            }
        )

    model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name)
    vecs = model.encode(texts, batch_size=512, convert_to_numpy=True, normalize_embeddings=True)
    for i, vec in enumerate(vecs):
        rows[i]["embedding"] = vec.tolist()

    total = 0
    excluded = None
    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        stmt = insert(providers_table).values(chunk)
        update_dict = {c.name: stmt.excluded[c.name] for c in providers_table.c if c.name != "id"}
        stmt = stmt.on_conflict_do_update(index_elements=[providers_table.c.id], set_=update_dict)
        with engine.begin() as conn:
            conn.execute(stmt)
        total += len(chunk)
    return total


def load_providers_to_postgres(data_path: Optional[str] = None) -> int:
    path = data_path or _default_data_path()
    logger.info("Loading providers from JSON", extra={"path": path})

    with open(path, "r", encoding="utf-8") as f:
        providers = json.load(f)

    ensure_providers_schema()
    engine = get_engine()
    n = upsert_providers(engine, providers)
    logger.info("Providers upserted to local Postgres", extra={"count": n})
    return n


if __name__ == "__main__":
    import sys
    try:
        from dotenv import load_dotenv
        load_dotenv(".env.local")
    except Exception:
        pass

    data_path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        count = load_providers_to_postgres(data_path)
        print(f"Upserted {count} providers to Postgres")
    except Exception as e:
        print(f"Error loading providers to Postgres: {e}", file=sys.stderr)
        sys.exit(1)