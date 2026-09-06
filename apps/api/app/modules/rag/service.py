import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.modules.journey.models import RagDocumentModel


def embedding(text: str) -> list[float]:
    """Use OpenAI embeddings when configured, otherwise remain local and deterministic."""
    settings = get_settings()
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            response = OpenAI(api_key=settings.openai_api_key).embeddings.create(
                model=settings.openai_embedding_model,
                input=text,
                dimensions=64,
            )
            return response.data[0].embedding
        except Exception:
            pass
    return deterministic_embedding(text)


def deterministic_embedding(text: str) -> list[float]:
    """Stable local fallback with the same 64 dimensions as the provider call."""
    value = text.encode()
    digest = hashlib.sha256(value).digest() + hashlib.sha256(b"finpass:" + value).digest()
    return [((digest[index] / 255) * 2) - 1 for index in range(64)]


def search(
    session: Session,
    query: str,
    *,
    source_type: str = "CONSULTATION_CASE",
    journey_step: str | None = None,
    intent: str | None = None,
    limit: int = 3,
) -> list[RagDocumentModel]:
    statement = (
        select(RagDocumentModel)
        .where(RagDocumentModel.source_type == source_type)
        .order_by(RagDocumentModel.embedding.cosine_distance(embedding(query)))
        .limit(limit * 5)
    )
    documents = session.scalars(statement).all()
    if journey_step or intent:
        filtered = [
            document
            for document in documents
            if (
                journey_step is None
                or journey_step in document.text
                or journey_step in str(document.metadata_json)
            )
            and (intent is None or intent in str(document.metadata_json))
        ]
        if filtered:
            documents = filtered
    return documents[:limit]
