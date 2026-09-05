import json
import sys
from pathlib import Path

from app.contracts.journey import JourneyFixture


def validate_fixture_directory(directory: Path) -> int:
    files = sorted(directory.glob("*.json"))
    if not files:
        raise SystemExit(f"no JSON fixtures found in {directory}")

    for path in files:
        fixture = JourneyFixture.model_validate_json(path.read_text(encoding="utf-8"))
        print(json.dumps({"file": path.name, "events": len(fixture.events), "valid": True}))
    return len(files)


if __name__ == "__main__":
    fixture_directory = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    count = validate_fixture_directory(fixture_directory)
    print(f"validated {count} fixture(s)")
