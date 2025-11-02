import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer
from sqlalchemy import select, and_, bindparam
from pgvector.sqlalchemy import Vector
from database.client import get_engine
from database.models import providers_table


@dataclass
class Provider:
    id: int
    full_name: str
    specialty: str
    phone: str
    email: str
    address: Dict[str, Any]
    years_experience: Optional[int]
    accepting_new_patients: Optional[bool]
    insurance_accepted: List[str]
    rating: Optional[float]
    license_number: Optional[str]
    board_certified: Optional[bool]
    languages: List[str]


_embedding_model: Optional[SentenceTransformer] = None


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model


def _build_query_text(
    *,
    city: Optional[str],
    state: Optional[str],
    specialty: Optional[str],
    name_contains: Optional[str],
    insurance: Optional[str],
    language: Optional[str],
) -> str:
    parts: List[str] = []
    for v in [name_contains, specialty, city, state, insurance, language]:
        v2 = (v or "").strip()
        if v2:
            parts.append(v2)
    return " ".join(parts) or "providers"


def semantic_search_providers(
    *,
    city: Optional[str] = None,
    state: Optional[str] = None,
    specialty: Optional[str] = None,
    name_contains: Optional[str] = None,
    accepting_new_patients: Optional[bool] = None,
    min_rating: Optional[float] = None,
    insurance: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    model = _get_embedding_model()
    query_text = _build_query_text(
        city=city,
        state=state,
        specialty=specialty,
        name_contains=name_contains,
        insurance=insurance,
        language=language,
    )
    qvec = model.encode([query_text], convert_to_numpy=True)[0].tolist()

    conditions = []
    if city:
        conditions.append(providers_table.c.address_city == city)
    if state:
        conditions.append(providers_table.c.address_state == state)
    if specialty:
        conditions.append(providers_table.c.specialty.ilike(f"%{specialty}%"))
    if name_contains:
        conditions.append(providers_table.c.full_name.ilike(f"%{name_contains}%"))
    if accepting_new_patients is not None:
        conditions.append(providers_table.c.accepting_new_patients.is_(accepting_new_patients))
    if min_rating is not None:
        conditions.append(providers_table.c.rating >= float(min_rating))
    if insurance:
        conditions.append(providers_table.c.insurance_accepted.contains([insurance]))
    if language:
        conditions.append(providers_table.c.languages.contains([language]))

    where_clause = and_(*conditions) if conditions else None

    vec_param = bindparam("query_vec", qvec, type_=Vector(384))
    similarity = providers_table.c.embedding.op("<->")(vec_param)

    stmt = (
        select(
            providers_table.c.id,
            providers_table.c.full_name,
            providers_table.c.specialty,
            providers_table.c.phone,
            providers_table.c.email,
            providers_table.c.address_street,
            providers_table.c.address_city,
            providers_table.c.address_state,
            providers_table.c.address_postal_code,
            providers_table.c.accepting_new_patients,
            providers_table.c.rating,
            providers_table.c.insurance_accepted,
            providers_table.c.languages,
        )
        .order_by(similarity)
        .limit(limit)
    )
    if where_clause is not None:
        stmt = stmt.where(where_clause)

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(stmt, {"query_vec": qvec}).fetchall()

    results: List[Dict[str, Any]] = []
    for r in rows:
        results.append(
            {
                "id": r.id,
                "full_name": r.full_name,
                "specialty": r.specialty,
                "phone": r.phone,
                "email": r.email,
                "address": {
                    "street": r.address_street,
                    "city": r.address_city,
                    "state": r.address_state,
                    "postal_code": r.address_postal_code,
                },
                "accepting_new_patients": r.accepting_new_patients,
                "rating": r.rating,
                "insurance_accepted": r.insurance_accepted or [],
                "languages": r.languages or [],
            }
        )
    return results


def search_providers(
    *,
    city: Optional[str] = None,
    state: Optional[str] = None,
    specialty: Optional[str] = None,
    name_contains: Optional[str] = None,
    accepting_new_patients: Optional[bool] = None,
    min_rating: Optional[float] = None,
    insurance: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Search for healthcare providers using semantic search with pgvector.
    
    Args:
        city: Filter by city name
        state: Filter by state name
        specialty: Filter by medical specialty
        name_contains: Filter by provider name (partial match)
        accepting_new_patients: Filter by whether accepting new patients
        min_rating: Filter by minimum rating
        insurance: Filter by insurance accepted
        language: Filter by language spoken
        limit: Maximum number of results to return
        
    Returns:
        List of provider dictionaries matching the search criteria
    """
    return semantic_search_providers(
        city=city,
        state=state,
        specialty=specialty,
        name_contains=name_contains,
        accepting_new_patients=accepting_new_patients,
        min_rating=min_rating,
        insurance=insurance,
        language=language,
        limit=limit,
    )