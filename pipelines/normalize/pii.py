"""Conservative structured-PII redaction used before further review."""

import re
from collections import Counter
from typing import Counter as CounterType, Dict, Tuple

PATTERNS = {
    "email": re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.IGNORECASE),
    "resident_id": re.compile(r"(?<!\d)\d{6}\s*[- ]\s*[1-4]\d{6}(?!\d)"),
    "phone": re.compile(r"(?<!\d)(?:01[016789]|0[2-6][1-5]?)\s*[-.) ]\s*\d{3,4}\s*[- ]\s*\d{4}(?!\d)"),
    "card_number": re.compile(r"(?<!\d)(?:\d[ -]?){15}\d(?!\d)"),
    "account_number": re.compile(r"(?<!\d)\d{2,6}[- ]\d{2,6}[- ]\d{2,6}(?:[- ]\d{1,4})?(?!\d)"),
}


def redact_text(value: object) -> Tuple[str, Dict[str, int]]:
    text = "" if value is None else str(value)
    counts: CounterType[str] = Counter()
    for name, pattern in PATTERNS.items():
        text, count = pattern.subn("[%s]" % name.upper(), text)
        if count:
            counts[name] += count
    return text, dict(counts)


def contains_structured_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern in PATTERNS.values())
