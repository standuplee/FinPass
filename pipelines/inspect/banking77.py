"""Download, validate, and snapshot the pinned MTEB Banking77 dataset."""

import json
from argparse import ArgumentParser
from pathlib import Path

from datasets import DatasetDict, load_dataset

DATASET_ID = "mteb/banking77"
DATASET_REVISION = "18072d2"
EXPECTED_COLUMNS = {"text", "label", "label_text"}
EXPECTED_ROWS = {"train": 10_003, "test": 3_080}
EXPECTED_LABELS = 77


def load_and_validate() -> DatasetDict:
    dataset = load_dataset(DATASET_ID, revision=DATASET_REVISION)
    if not isinstance(dataset, DatasetDict):
        raise TypeError("Banking77 must load as a DatasetDict")

    if set(dataset) != set(EXPECTED_ROWS):
        raise ValueError(f"unexpected splits: {sorted(dataset)}")

    for split, expected_rows in EXPECTED_ROWS.items():
        actual_columns = set(dataset[split].column_names)
        if actual_columns != EXPECTED_COLUMNS:
            raise ValueError(f"{split}: unexpected columns {sorted(actual_columns)}")
        if len(dataset[split]) != expected_rows:
            raise ValueError(f"{split}: expected {expected_rows}, got {len(dataset[split])}")

    labels = set(dataset["train"]["label_text"]) | set(dataset["test"]["label_text"])
    if len(labels) != EXPECTED_LABELS:
        raise ValueError(f"expected {EXPECTED_LABELS} labels, got {len(labels)}")
    return dataset


def export(dataset: DatasetDict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for split, split_dataset in dataset.items():
        split_dataset.to_parquet(output / f"{split}.parquet")

    labels = sorted(set(dataset["train"]["label_text"]) | set(dataset["test"]["label_text"]))
    profile = {
        "dataset_id": DATASET_ID,
        "revision": DATASET_REVISION,
        "splits": {split: len(values) for split, values in dataset.items()},
        "columns": dataset["train"].column_names,
        "label_count": len(labels),
        "labels": labels,
        "fingerprints": {
            split: values._fingerprint  # Dataset provenance metadata.
            for split, values in dataset.items()
        },
    }
    (output / "profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/intents/banking77"),
    )
    args = parser.parse_args()
    export(load_and_validate(), args.output)


if __name__ == "__main__":
    main()
