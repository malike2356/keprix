"""jamovi import bridge."""

from __future__ import annotations

import csv
import io
from typing import Any


def parse_csv_package(csv_text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    return [dict(row) for row in reader]
