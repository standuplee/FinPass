"""Apply the reviewed FinPass scope taxonomy to local Banking77 splits."""

import hashlib
import json
import os
import uuid
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterator, Tuple

DATASET_ID = "mteb/banking77"
DATASET_REVISION = "18072d2"
NORMALIZER_VERSION = "1.0"
NORMALIZED_AT = "2026-09-05T00:00:00+00:00"
ID_NAMESPACE = uuid.UUID("088e060c-ffb3-4845-acbc-0243994f318f")
VALID_SCOPES = {"DIRECT", "RELATED", "OUT_OF_SCOPE"}


def load_mapping(path: Path) -> Dict[str, Dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["dataset_id"] != DATASET_ID or payload["dataset_revision"] != DATASET_REVISION:
        raise ValueError("taxonomy dataset identity does not match the normalizer")
    labels = payload["labels"]
    if len(labels) != 77:
        raise ValueError("Banking77 taxonomy must contain exactly 77 labels")
    for label, mapping in labels.items():
        if mapping.get("scope") not in VALID_SCOPES:
            raise ValueError("%s has an invalid scope" % label)
        if mapping["scope"] != "OUT_OF_SCOPE" and not mapping.get("internal_intent"):
            raise ValueError("%s requires an internal_intent" % label)
    return labels


def rows(path: Path) -> Iterator[Tuple[int, Dict[str, Any]]]:
    with path.open(encoding="utf-8") as source:
        for index, line in enumerate(source):
            yield index, json.loads(line)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(raw_root: Path, mapping_path: Path, output: Path) -> Dict[str, Any]:
    mapping = load_mapping(mapping_path)
    output.mkdir(parents=True, exist_ok=True)
    split_counts: Dict[str, int] = {}
    scope_counts: Counter = Counter()
    label_counts: Counter = Counter()
    observed_labels = set()
    outputs: Dict[str, Path] = {}

    for split in ("train", "test"):
        source_path = raw_root / (split + ".jsonl")
        temp_path = output / (split + ".jsonl.tmp")
        final_path = output / (split + ".jsonl")
        count = 0
        with temp_path.open("w", encoding="utf-8") as stream:
            for index, row in rows(source_path):
                label = row["label_text"]
                if label not in mapping:
                    raise ValueError("unmapped Banking77 label: %s" % label)
                taxonomy = mapping[label]
                observed_labels.add(label)
                scope_counts[taxonomy["scope"]] += 1
                label_counts[label] += 1
                record_key = "%s:%s:%s:%s" % (split, index, label, row["text"])
                record = {
                    "intent_example_id": str(uuid.uuid5(ID_NAMESPACE, record_key)),
                    "text": row["text"],
                    "source_label_id": row["label"],
                    "source_label": label,
                    "finpass_scope": taxonomy["scope"],
                    "internal_intent": taxonomy.get("internal_intent"),
                    "journey_step": taxonomy.get("journey_step"),
                    "provenance": {
                        "dataset_id": DATASET_ID,
                        "dataset_revision": DATASET_REVISION,
                        "source_split": split,
                        "source_row": index,
                        "normalizer_version": NORMALIZER_VERSION,
                        "normalized_at": NORMALIZED_AT,
                    },
                }
                stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                count += 1
        os.replace(temp_path, final_path)
        outputs[split] = final_path
        split_counts[split] = count

    missing = set(mapping) - observed_labels
    if missing:
        raise ValueError("taxonomy labels absent from source data: %s" % sorted(missing))

    label_scope_counts = Counter(item["scope"] for item in mapping.values())
    report = {
        "dataset_id": DATASET_ID,
        "dataset_revision": DATASET_REVISION,
        "normalizer_version": NORMALIZER_VERSION,
        "normalized_at": NORMALIZED_AT,
        "split_counts": split_counts,
        "label_count": len(observed_labels),
        "label_scope_counts": dict(sorted(label_scope_counts.items())),
        "example_scope_counts": dict(sorted(scope_counts.items())),
        "label_counts": dict(sorted(label_counts.items())),
        "outputs": {key: str(path) for key, path in outputs.items()},
        "output_sha256": {key: file_sha256(path) for key, path in outputs.items()},
    }
    (output / "quality-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/banking77"))
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path("knowledge/taxonomy/banking77-map.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/intents/banking77")
    )
    args = parser.parse_args()
    print(json.dumps(normalize(args.raw_root, args.mapping, args.output), indent=2))


if __name__ == "__main__":
    main()
