"""Index normalized RAG documents into PostgreSQL pgvector."""

import hashlib
import json
from pathlib import Path

from app.infrastructure.database import SessionLocal
from app.modules.journey.models import RagDocumentModel

ROOT = Path(__file__).resolve().parents[3]
SOURCES = [ROOT / "data/processed/consultations/rag_documents.jsonl"]


def embedding(text: str) -> list[float]:
    """Deterministic local placeholder; replace with provider embeddings in Phase 3."""
    value = text.encode()
    digest = hashlib.sha256(value).digest() + hashlib.sha256(b"finpass:" + value).digest()
    return [((digest[index] / 255) * 2) - 1 for index in range(64)]


def main() -> None:
    session = SessionLocal()
    count = 0
    skipped = 0
    try:
        for source in SOURCES:
            if not source.exists():
                continue
            for line in source.read_text(encoding="utf-8").splitlines():
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                session.merge(
                    RagDocumentModel(
                        id=item["document_id"],
                        source_type=item["source_type"],
                        text=item["text"],
                        metadata_json=item.get("metadata", {}),
                        embedding=embedding(item["text"]),
                    )
                )
                count += 1
                if count % 500 == 0:
                    session.commit()
        session.commit()
    finally:
        session.close()
    print(f"indexed {count} RAG documents; skipped {skipped} malformed records")


if __name__ == "__main__":
    main()
