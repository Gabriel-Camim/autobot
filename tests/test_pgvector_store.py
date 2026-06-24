from config import Settings
from pgvector_store import pgvector_index_type, pgvector_status


def test_pgvector_large_embeddings_use_exact_search():
    settings = Settings(_env_file=None, VECTORSTORE_BACKEND="pgvector", PGVECTOR_DIMENSION=3072)

    assert pgvector_index_type(settings) == "exact"


def test_non_pgvector_status_reports_no_vector_index():
    settings = Settings(_env_file=None, VECTORSTORE_BACKEND="chroma")

    status = pgvector_status(settings)

    assert status["backend"] == "chroma"
    assert status["index_type"] == "none"
