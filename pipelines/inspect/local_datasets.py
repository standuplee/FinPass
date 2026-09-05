"""Profile local FinPass source datasets without persisting sample values."""

import csv
import hashlib
import io
import json
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from zipfile import ZipFile


def schema_paths(value: Any, prefix: str = "$") -> Iterable[Tuple[str, str]]:
    if isinstance(value, dict):
        yield prefix, "object"
        for key, nested in value.items():
            yield from schema_paths(nested, "%s.%s" % (prefix, key))
    elif isinstance(value, list):
        yield prefix, "array"
        for nested in value[:1]:
            yield from schema_paths(nested, "%s[]" % prefix)
    elif value is None:
        yield prefix, "null"
    elif isinstance(value, bool):
        yield prefix, "boolean"
    elif isinstance(value, int):
        yield prefix, "integer"
    elif isinstance(value, float):
        yield prefix, "number"
    else:
        yield prefix, "string"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def profile_zip(path: Path, full_json_validation: bool) -> Dict[str, Any]:
    extension_counts: Counter = Counter()
    schema_counts: Counter = Counter()
    schema_definitions: Dict[str, List[List[str]]] = {}
    invalid_json = 0
    csv_profiles: List[Dict[str, Any]] = []
    content_hashes: List[str] = []

    with ZipFile(path) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        for item in files:
            with archive.open(item) as source:
                content_hashes.append(hashlib.sha256(source.read()).hexdigest())
            suffix = Path(item.filename.strip()).suffix.lower() or "<none>"
            extension_counts[suffix] += 1
            if suffix == ".json" and (full_json_validation or not schema_counts):
                try:
                    with archive.open(item) as source:
                        payload = json.load(source)
                    signature_items = sorted(set(schema_paths(payload)))
                    signature = hashlib.sha256(
                        json.dumps(signature_items, ensure_ascii=False).encode("utf-8")
                    ).hexdigest()[:12]
                    schema_counts[signature] += 1
                    schema_definitions.setdefault(signature, [list(entry) for entry in signature_items])
                except (UnicodeDecodeError, json.JSONDecodeError):
                    invalid_json += 1
            elif suffix == ".csv":
                with archive.open(item) as source:
                    reader = csv.reader(io.TextIOWrapper(source, encoding="utf-8-sig", newline=""))
                    header = next(reader)
                    row_count = sum(1 for _ in reader)
                csv_profiles.append(
                    {"file": item.filename, "rows": row_count, "columns": header}
                )

    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "content_set_sha256": hashlib.sha256(
            "\n".join(sorted(content_hashes)).encode("utf-8")
        ).hexdigest(),
        "file_count": len(files),
        "uncompressed_bytes": sum(item.file_size for item in files),
        "extensions": dict(sorted(extension_counts.items())),
        "invalid_json": invalid_json,
        "json_schemas": dict(sorted(schema_counts.items())),
        "schema_definitions": schema_definitions,
        "csv_profiles": csv_profiles,
    }


def profile_aihub(root: Path, full_json_validation: bool) -> Dict[str, Any]:
    archives = [profile_zip(path, full_json_validation) for path in sorted(root.rglob("*.zip"))]
    content_groups: Dict[str, List[str]] = {}
    for archive in archives:
        content_groups.setdefault(archive["content_set_sha256"], []).append(archive["path"])
    duplicate_groups = [paths for paths in content_groups.values() if len(paths) > 1]
    return {
        "root": str(root),
        "archive_count": len(archives),
        "compressed_bytes": sum(item["bytes"] for item in archives),
        "contained_file_count": sum(item["file_count"] for item in archives),
        "invalid_json": sum(item["invalid_json"] for item in archives),
        "duplicate_content_groups": duplicate_groups,
        "archives": archives,
    }


def profile_bpi(path: Path) -> Dict[str, Any]:
    activity_counts: Counter = Counter()
    origin_counts: Counter = Counter()
    lifecycle_counts: Counter = Counter()
    cases: Set[str] = set()
    row_count = 0
    missing_timestamp = 0
    first_timestamp = None
    last_timestamp = None

    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        columns = reader.fieldnames or []
        for row in reader:
            row_count += 1
            cases.add(row["case:concept:name"])
            activity_counts[row["concept:name"]] += 1
            origin_counts[row["EventOrigin"]] += 1
            lifecycle_counts[row["lifecycle:transition"]] += 1
            timestamp = row["time:timestamp"]
            if not timestamp:
                missing_timestamp += 1
            else:
                first_timestamp = min(first_timestamp, timestamp) if first_timestamp else timestamp
                last_timestamp = max(last_timestamp, timestamp) if last_timestamp else timestamp

    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "rows": row_count,
        "cases": len(cases),
        "columns": columns,
        "activity_counts": dict(activity_counts.most_common()),
        "origin_counts": dict(origin_counts.most_common()),
        "lifecycle_counts": dict(lifecycle_counts.most_common()),
        "missing_timestamp": missing_timestamp,
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
    }


def profile_banking77(root: Path) -> Dict[str, Any]:
    splits: Dict[str, Any] = {}
    all_labels: Set[str] = set()
    for path in sorted(root.glob("*.jsonl")):
        labels: Counter = Counter()
        rows = 0
        columns: Set[str] = set()
        invalid_json = 0
        with path.open(encoding="utf-8") as source:
            for line in source:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    invalid_json += 1
                    continue
                rows += 1
                columns.update(row)
                labels[row["label_text"]] += 1
                all_labels.add(row["label_text"])
        splits[path.stem] = {
            "rows": rows,
            "columns": sorted(columns),
            "invalid_json": invalid_json,
            "label_counts": dict(labels.most_common()),
            "sha256": sha256_file(path),
        }
    return {"root": str(root), "label_count": len(all_labels), "splits": splits}


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/profiles/dataset-profile.json"),
    )
    parser.add_argument("--sample-json", action="store_true")
    args = parser.parse_args()

    profile = {
        "profile_version": "1.0",
        "full_json_validation": not args.sample_json,
        "datasets": {
            "aihub_consulting": profile_aihub(
                args.raw_root / "aihub-consulting", not args.sample_json
            ),
            "aihub_financial_product": profile_aihub(
                args.raw_root / "aihub-financial-product", not args.sample_json
            ),
            "bpi2017": profile_bpi(args.raw_root / "bpi2017" / "bpi_2017_cleaned.csv"),
            "banking77": profile_banking77(args.raw_root / "banking77"),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % args.output)


if __name__ == "__main__":
    main()
