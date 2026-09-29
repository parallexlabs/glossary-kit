from __future__ import annotations

import csv
from pathlib import Path

from glossary_kit.domain.models import Glossary
from glossary_kit.ingest.loader import glossary_to_csv_rows


def export_csv(glossary: Glossary, output: Path, profile: str = "human") -> None:
    rows = glossary_to_csv_rows(glossary, profile=profile)
    if not rows:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in sorted(rows, key=lambda r: r["id"]):
            writer.writerow(row)
