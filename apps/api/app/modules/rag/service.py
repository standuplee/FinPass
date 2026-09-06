import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.journey.models import RagDocumentModel


def embedding(text: str) -> list[float]:
    """Deterministic fallback embedding until a provider is configured."""
    value = text.encode()
    digest = hashlib.sha256(value).digest() + hashlib.sha256(b"finpass:" + value).digest()
    return [((digest[index] / 255) * 2) - 1 for index in range(64)]


def search(
    session: Session,
    query: str,
    *,
    source_type: str = "CONSULTATION_CASE",
    journey_step: str | None = None,
    limit: int = 3,
) -> list[RagDocumentModel]:
    statement = (
        select(RagDocumentModel)
        .where(RagDocumentModel.source_type == source_type)
        .order_by(RagDocumentModel.embedding.cosine_distance(embedding(query)))
        .limit(limit * 5)
    )
    documents = session.scalars(statement).all()
    if journey_step:
        filtered = [
            document
            for document in documents
            if journey_step in document.text or journey_step in str(document.metadata_json)
        ]
        if filtered:
            documents = filtered
    return documents[:limit]
