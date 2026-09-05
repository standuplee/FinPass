"""Normalize AI-Hub product, recommendation, and consumer datasets."""

import csv
import hashlib
import io
import json
import os
import uuid
from argparse import ArgumentParser
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterator, List, Set, Tuple
from zipfile import ZipFile

DATASET_ID = "AIHUB_FINANCIAL_PRODUCT_CONSUMER_36"
DATASET_SNAPSHOT_AT = "2026-09-05T00:00:00+00:00"
NORMALIZER_VERSION = "1.0"
ID_NAMESPACE = uuid.UUID("ced29c76-c135-4487-9394-39d49051f279")
MIN_SEGMENT_COUNT = 20

FIELD_ALIASES = {
    "minimum_insured _premium": "minimum_insured_premium",
    "srarting_age": "starting_age",
}

COMMON_PRODUCT_FIELDS = {
    "product_name",
    "product_full_name",
    "mother_product_name",
    "product_type",
    "company",
    "risk_grade",
    "tax_type",
}

SEGMENT_DIMENSIONS = [
    ("customer_type",),
    ("age",),
    ("gender",),
    ("income_bracket",),
    ("occupation_group",),
    ("risk_grade",),
    ("investment_propensity",),
    ("age", "income_bracket"),
    ("occupation_group", "risk_grade"),
    ("age", "investment_propensity"),
]


def write_jsonl(stream: Any, record: Dict[str, Any]) -> None:
    stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_id(record_type: str, content_hash: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "%s:%s" % (record_type, content_hash)))


def archive_metadata(path: Path) -> Tuple[str, str]:
    split = "train" if path.name.startswith("T") else "validation"
    if "소비자" in path.name:
        return split, "consumer"
    if "CoT" in path.name:
        return split, "recommendation"
    return split, "product"


def json_records(path: Path) -> Iterator[Tuple[str, bytes, Dict[str, Any]]]:
    with ZipFile(path) as archive:
        for item in archive.infolist():
            if item.is_dir() or not item.filename.strip().lower().endswith(".json"):
                continue
            payload = archive.read(item)
            yield item.filename, payload, json.loads(payload)


def normalize_product_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for source_key, value in payload.items():
        key = FIELD_ALIASES.get(source_key, source_key).strip()
        normalized[key] = "" if value is None else str(value).strip()
    return normalized


def product_category(path: Path) -> str:
    if "증권" in path.name:
        return "SECURITIES"
    if "보험" in path.name:
        return "INSURANCE"
    return "UNKNOWN"


def normalize_product_archives(
    archives: List[Path], output: Path, stats: Counter
) -> None:
    records: Dict[str, Dict[str, Any]] = {}
    provenance: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    for archive in archives:
        split, kind = archive_metadata(archive)
        if kind != "product":
            continue
        for source_file, source_bytes, payload in json_records(archive):
            normalized = normalize_product_fields(payload)
            content_hash = hashlib.sha256(canonical_json(normalized).encode("utf-8")).hexdigest()
            attributes = {
                key: value for key, value in normalized.items() if key not in COMMON_PRODUCT_FIELDS
            }
            records.setdefault(
                content_hash,
                {
                    "product_id": stable_id("product", content_hash),
                    "product_category": product_category(archive),
                    "product_name": normalized.get("product_full_name")
                    or normalized.get("product_name", ""),
                    "parent_product_name": normalized.get("mother_product_name", ""),
                    "provider": normalized.get("company", ""),
                    "source_product_type": normalized.get("product_type", ""),
                    "risk_grade": normalized.get("risk_grade", ""),
                    "tax_type": normalized.get("tax_type", ""),
                    "attributes": attributes,
                    "content_sha256": content_hash,
                },
            )
            provenance[content_hash].append(
                {
                    "source_split": split,
                    "source_archive": archive.name,
                    "source_file": source_file,
                    "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
                }
            )
            stats["product_source_records"] += 1

    temp = output / "products.jsonl.tmp"
    with temp.open("w", encoding="utf-8") as stream:
        for content_hash in sorted(records):
            observed = provenance[content_hash]
            record = {
                **records[content_hash],
                "observed_splits": sorted({item["source_split"] for item in observed}),
                "provenance": observed,
                "dataset_id": DATASET_ID,
                "normalizer_version": NORMALIZER_VERSION,
                "normalized_at": DATASET_SNAPSHOT_AT,
            }
            write_jsonl(stream, record)
            stats["products"] += 1
    os.replace(temp, output / "products.jsonl")
    stats["product_duplicates_removed"] = stats["product_source_records"] - stats["products"]


def normalize_recommendations(
    archives: List[Path], output: Path, stats: Counter
) -> None:
    seen: Set[str] = set()
    temp = output / "recommendation_cases.jsonl.tmp"
    with temp.open("w", encoding="utf-8") as stream:
        for archive in archives:
            split, kind = archive_metadata(archive)
            if kind != "recommendation":
                continue
            for source_file, source_bytes, payload in json_records(archive):
                raw_names = payload.get("product_names", [])
                if isinstance(raw_names, str):
                    product_names = [raw_names] if raw_names.strip() else []
                    stats["product_names_type_coercions"] += 1
                else:
                    product_names = [str(name).strip() for name in raw_names if str(name).strip()]
                source_hash = hashlib.sha256(source_bytes).hexdigest()
                record_hash = hashlib.sha256(
                    canonical_json(
                        {
                            "category": payload.get("category"),
                            "query_type": payload.get("query_type"),
                            "question": payload.get("question"),
                            "answer": payload.get("answer"),
                            "product_names": product_names,
                        }
                    ).encode("utf-8")
                ).hexdigest()
                if record_hash in seen:
                    stats["recommendation_duplicates_removed"] += 1
                    continue
                seen.add(record_hash)
                write_jsonl(
                    stream,
                    {
                        "recommendation_case_id": stable_id("recommendation", record_hash),
                        "category": payload.get("category"),
                        "query_type": payload.get("query_type"),
                        "question": payload.get("question"),
                        "answer": payload.get("answer"),
                        "product_names": product_names,
                        "customer_segment": {
                            "gender": payload.get("gender"),
                            "age": payload.get("age"),
                        },
                        "reasoning_available_in_source": any(
                            bool(payload.get(key)) for key in ("cot1", "cot2", "cot3")
                        ),
                        "reasoning_included": False,
                        "provenance": {
                            "dataset_id": DATASET_ID,
                            "source_split": split,
                            "source_archive": archive.name,
                            "source_file": source_file,
                            "source_record_id": str(payload.get("cot_id", "")),
                            "source_sha256": source_hash,
                            "normalizer_version": NORMALIZER_VERSION,
                            "normalized_at": DATASET_SNAPSHOT_AT,
                        },
                    },
                )
                stats["recommendation_cases"] += 1
    os.replace(temp, output / "recommendation_cases.jsonl")


def consumer_rows(archive: Path) -> Iterator[Dict[str, str]]:
    with ZipFile(archive) as source_zip:
        item = next(item for item in source_zip.infolist() if not item.is_dir())
        with source_zip.open(item) as source:
            reader = csv.DictReader(
                io.TextIOWrapper(source, encoding="utf-8-sig", newline="")
            )
            yield from reader


def normalize_consumer_segments(
    archives: List[Path], output: Path, stats: Counter
) -> None:
    consumer_archives = [path for path in archives if archive_metadata(path)[1] == "consumer"]
    train_archive = next(path for path in consumer_archives if archive_metadata(path)[0] == "train")
    validation_archive = next(
        path for path in consumer_archives if archive_metadata(path)[0] == "validation"
    )

    with ZipFile(train_archive) as train_zip, ZipFile(validation_archive) as validation_zip:
        train_item = next(item for item in train_zip.infolist() if not item.is_dir())
        validation_item = next(item for item in validation_zip.infolist() if not item.is_dir())
        if hashlib.sha256(train_zip.read(train_item)).digest() != hashlib.sha256(
            validation_zip.read(validation_item)
        ).digest():
            raise ValueError("consumer train and validation files unexpectedly differ")
    stats["consumer_duplicate_split_files_removed"] = 1

    counters = {dimensions: Counter() for dimensions in SEGMENT_DIMENSIONS}
    for row in consumer_rows(train_archive):
        stats["consumer_source_rows"] += 1
        for dimensions, counter in counters.items():
            values = tuple((row.get(field) or "UNKNOWN").strip() or "UNKNOWN" for field in dimensions)
            counter[values] += 1

    temp = output / "segment_aggregates.jsonl.tmp"
    with temp.open("w", encoding="utf-8") as stream:
        for dimensions in SEGMENT_DIMENSIONS:
            for values, count in sorted(counters[dimensions].items()):
                if count < MIN_SEGMENT_COUNT:
                    stats["consumer_segments_suppressed"] += 1
                    continue
                write_jsonl(
                    stream,
                    {
                        "dimensions": dict(zip(dimensions, values)),
                        "count": count,
                        "minimum_group_size": MIN_SEGMENT_COUNT,
                        "dataset_id": DATASET_ID,
                        "source_split": "train",
                        "normalizer_version": NORMALIZER_VERSION,
                        "normalized_at": DATASET_SNAPSHOT_AT,
                    },
                )
                stats["consumer_segment_aggregates"] += 1
    os.replace(temp, output / "segment_aggregates.jsonl")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(raw_root: Path, output_root: Path) -> Dict[str, Any]:
    archives = sorted(raw_root.rglob("*.zip"))
    product_output = output_root / "financial-products"
    consumer_output = output_root / "consumers"
    product_output.mkdir(parents=True, exist_ok=True)
    consumer_output.mkdir(parents=True, exist_ok=True)
    stats: Counter = Counter()

    normalize_product_archives(archives, product_output, stats)
    normalize_recommendations(archives, product_output, stats)
    normalize_consumer_segments(archives, consumer_output, stats)

    outputs = {
        "products": product_output / "products.jsonl",
        "recommendation_cases": product_output / "recommendation_cases.jsonl",
        "segment_aggregates": consumer_output / "segment_aggregates.jsonl",
    }
    report = {
        "dataset_id": DATASET_ID,
        "normalizer_version": NORMALIZER_VERSION,
        "normalized_at": DATASET_SNAPSHOT_AT,
        "counts": dict(sorted(stats.items())),
        "privacy": {
            "individual_consumer_rows_persisted": False,
            "excluded_consumer_fields": [
                "customer_id",
                "customer_seq",
                "region",
                "marital_status",
                "cross_coverage",
                "disease_history",
                "product_name",
                "product_amt",
                "transaction_keyword",
                "transaction_amt",
            ],
            "minimum_segment_count": MIN_SEGMENT_COUNT,
        },
        "outputs": {key: str(path) for key, path in outputs.items()},
        "output_sha256": {key: file_sha256(path) for key, path in outputs.items()},
    }
    (product_output / "quality-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--raw-root", type=Path, default=Path("data/raw/aihub-financial-product")
    )
    parser.add_argument("--output-root", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    print(json.dumps(normalize(args.raw_root, args.output_root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
