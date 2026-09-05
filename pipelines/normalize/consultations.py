"""Normalize AI-Hub financial consultations into safe, joined JSONL tables."""

import hashlib
import json
import os
import uuid
from argparse import ArgumentParser
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Set, Tuple
from zipfile import ZipFile

from pipelines.normalize.pii import contains_structured_pii, redact_text

DATASET_ID = "AIHUB_FINANCIAL_CONSULTING_25"
NORMALIZER_VERSION = "1.0"
DATASET_SNAPSHOT_AT = "2026-09-05T00:00:00+00:00"
ID_NAMESPACE = uuid.UUID("2c28559f-d08d-4c4d-8a17-d436ed77bc70")


def archive_metadata(path: Path) -> Tuple[str, str, str]:
    name = path.name
    split = "train" if name.startswith("T") else "validation"
    kind = "label" if name[1:2] == "L" else "source"
    domain = name.split("_", 1)[1].split(".", 1)[0]
    return split, kind, domain


def json_records(path: Path) -> Iterator[Tuple[str, bytes, Dict[str, Any]]]:
    with ZipFile(path) as archive:
        for item in archive.infolist():
            if item.is_dir() or not item.filename.strip().lower().endswith(".json"):
                continue
            payload = archive.read(item)
            yield item.filename, payload, json.loads(payload)


def stable_id(record_type: str, domain: str, source_id: str, child_id: str = "") -> str:
    value = "%s:%s:%s:%s" % (record_type, domain, source_id, child_id)
    return str(uuid.uuid5(ID_NAMESPACE, value))


def sanitize_fields(values: Dict[str, object], redactions: Counter) -> Dict[str, str]:
    output: Dict[str, str] = {}
    for key, value in values.items():
        sanitized, counts = redact_text(value)
        output[key] = sanitized
        redactions.update(counts)
    return output


def write_jsonl(stream: Any, record: Dict[str, Any]) -> None:
    stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_source_keys(archives: Iterable[Path]) -> Tuple[Set[Tuple[str, str]], Set[Tuple[str, str]]]:
    train: Set[Tuple[str, str]] = set()
    validation: Set[Tuple[str, str]] = set()
    for archive in archives:
        split, kind, domain = archive_metadata(archive)
        if kind != "source":
            continue
        target = train if split == "train" else validation
        for _, _, payload in json_records(archive):
            target.add((domain, str(payload["source"]["source_id"])))
    return train, validation


def normalize(raw_root: Path, output: Path) -> Dict[str, Any]:
    archives = sorted(raw_root.rglob("*.zip"))
    train_keys, validation_keys = collect_source_keys(archives)
    overlap = train_keys & validation_keys
    normalized_at = DATASET_SNAPSHOT_AT
    stats: Counter = Counter()
    redactions: Counter = Counter()
    output.mkdir(parents=True, exist_ok=True)

    temp_paths = {
        "consultations": output / "consultations.jsonl.tmp",
        "qa": output / "consultation_qa.jsonl.tmp",
        "rag": output / "rag_documents.jsonl.tmp",
    }

    with ExitStack() as stack:
        streams = {
            key: stack.enter_context(path.open("w", encoding="utf-8"))
            for key, path in temp_paths.items()
        }
        for archive in archives:
            split, kind, domain = archive_metadata(archive)
            for source_file, source_bytes, payload in json_records(archive):
                source = payload["source"]
                consulting = payload["consulting"]
                source_id = str(source["source_id"])
                key = (domain, source_id)
                if split == "validation" and key in overlap:
                    stats["excluded_validation_overlap_%s" % kind] += 1
                    continue

                provenance = {
                    "dataset_id": DATASET_ID,
                    "dataset_version": "downloaded-2026-09-05",
                    "source_split": split,
                    "source_archive": archive.name,
                    "source_file": source_file,
                    "source_record_id": source_id,
                    "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
                    "normalizer_version": NORMALIZER_VERSION,
                    "normalized_at": normalized_at,
                }

                if kind == "source":
                    text = sanitize_fields(
                        {"consulting_content": source.get("consulting_content")}, redactions
                    )
                    residual = contains_structured_pii(text["consulting_content"])
                    record = {
                        "consultation_id": stable_id("consultation", domain, source_id),
                        "domain": domain,
                        "institution": source.get("source_institution"),
                        "source_date": str(source.get("source_date", "")),
                        "customer_segment": {
                            "gender": source.get("client_gender"),
                            "age": source.get("client_age"),
                            "client_type": source.get("consulting_client_type"),
                        },
                        "consulting_category": consulting.get("consulting_category"),
                        "consulting_topic": consulting.get("consulting_topic"),
                        "consulting_content": text["consulting_content"],
                        "pii_scan_status": "FAILED" if residual else "REGEX_PASSED",
                        "provenance": provenance,
                    }
                    write_jsonl(streams["consultations"], record)
                    stats["consultations"] += 1
                    stats["pii_residual_failures"] += int(residual)
                    continue

                summary_fields = sanitize_fields(
                    {"consulting_summary": consulting.get("consulting_summary")}, redactions
                )
                for item in payload.get("qa_data", []):
                    qa_id = str(item["qa_id"])
                    safe = sanitize_fields(
                        {
                            "consulting_situation": item.get("consulting_situation"),
                            "consulting_purpose": item.get("consulting_purpose"),
                            "core_financial_terms": item.get("core_financial_terms"),
                            "question": item.get("input", {}).get("question"),
                            "answer": item.get("input", {}).get("answer"),
                            "follow_up_question": item.get("input", {}).get("follow_up_question"),
                            "output": item.get("output"),
                        },
                        redactions,
                    )
                    all_text = "\n".join(list(summary_fields.values()) + list(safe.values()))
                    residual = contains_structured_pii(all_text)
                    record = {
                        "consultation_qa_id": stable_id("qa", domain, source_id, qa_id),
                        "consultation_id": stable_id("consultation", domain, source_id),
                        "domain": domain,
                        "task_category": item.get("task_category"),
                        "qa_topic": item.get("qa_topic"),
                        "consulting_summary": summary_fields["consulting_summary"],
                        **safe,
                        "pii_scan_status": "FAILED" if residual else "REGEX_PASSED",
                        "provenance": {**provenance, "source_child_id": qa_id},
                    }
                    write_jsonl(streams["qa"], record)
                    stats["qa"] += 1
                    stats["pii_residual_failures"] += int(residual)

                    if domain == "은행" and not residual:
                        rag_text = "\n".join(
                            value
                            for value in [
                                summary_fields["consulting_summary"],
                                safe["consulting_situation"],
                                safe["question"],
                                safe["answer"],
                                safe["output"],
                            ]
                            if value
                        )
                        rag_record = {
                            "document_id": stable_id("rag", domain, source_id, qa_id),
                            "source_type": "CONSULTATION_CASE",
                            "text": rag_text,
                            "metadata": {
                                "domain": domain,
                                "consulting_topic": consulting.get("consulting_topic"),
                                "task_category": item.get("task_category"),
                                "source_split": split,
                                "source_qa_id": record["consultation_qa_id"],
                            },
                        }
                        write_jsonl(streams["rag"], rag_record)
                        stats["rag_documents"] += 1

    final_paths = {
        "consultations": output / "consultations.jsonl",
        "qa": output / "consultation_qa.jsonl",
        "rag": output / "rag_documents.jsonl",
    }
    for key, temp_path in temp_paths.items():
        os.replace(temp_path, final_paths[key])

    report = {
        "dataset_id": DATASET_ID,
        "normalizer_version": NORMALIZER_VERSION,
        "normalized_at": normalized_at,
        "source_archives": len(archives),
        "train_source_keys": len(train_keys),
        "validation_source_keys": len(validation_keys),
        "cross_split_overlap_keys": len(overlap),
        "counts": dict(sorted(stats.items())),
        "structured_pii_redactions": dict(sorted(redactions.items())),
        "pii_scope": "regex-only; NER and manual review still required before production use",
        "outputs": {key: str(path) for key, path in final_paths.items()},
        "output_sha256": {key: file_sha256(path) for key, path in final_paths.items()},
    }
    (output / "quality-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--raw-root", type=Path, default=Path("data/raw/aihub-consulting")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/consultations")
    )
    args = parser.parse_args()
    print(json.dumps(normalize(args.raw_root, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
