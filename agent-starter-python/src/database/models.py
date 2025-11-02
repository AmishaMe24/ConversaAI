from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    MetaData,
    Table,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector


metadata = MetaData()

providers_table = Table(
    "providers",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("full_name", Text),
    Column("specialty", Text),
    Column("phone", Text),
    Column("email", Text),
    Column("address_street", Text),
    Column("address_city", Text),
    Column("address_state", String(2)),
    Column("address_postal_code", String(10)),
    Column("years_experience", Integer),
    Column("accepting_new_patients", Boolean),
    Column("insurance_accepted", JSONB),
    Column("rating", Float),
    Column("license_number", Text),
    Column("board_certified", Boolean),
    Column("languages", JSONB),
    # Vector embedding for semantic search (384 dims for MiniLM-L6-v2)
    Column("embedding", Vector(384)),
)

# Helpful indexes for typical queries
Index("idx_providers_city", providers_table.c.address_city)
Index("idx_providers_state", providers_table.c.address_state)
Index("idx_providers_specialty", providers_table.c.specialty)
Index("idx_providers_accepting", providers_table.c.accepting_new_patients)
Index("idx_providers_rating", providers_table.c.rating)
Index(
    "idx_providers_insurance_gin",
    providers_table.c.insurance_accepted,
    postgresql_using="gin",
)
Index(
    "idx_providers_languages_gin",
    providers_table.c.languages,
    postgresql_using="gin",
)

# HNSW index for fast semantic search over embeddings (L2 distance)
Index(
    "idx_providers_embedding_hnsw",
    providers_table.c.embedding,
    postgresql_using="hnsw",
    postgresql_ops={"embedding": "vector_l2_ops"},
)