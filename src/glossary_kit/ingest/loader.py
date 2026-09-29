from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import yaml

from glossary_kit.domain.models import Glossary


class IngestError(Exception):
    """Raised when input files cannot be read or parsed."""


def load_glossary_yaml(path: Path) -> Glossary:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"Cannot read glossary file: {path}"
        raise IngestError(msg) from exc
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        msg = f"Invalid YAML in {path}"
        raise IngestError(msg) from exc
    if not isinstance(data, dict):
        msg = f"Expected mapping at root of {path}"
        raise IngestError(msg)
    try:
        return Glossary.model_validate(data)
    except Exception as exc:
        msg = f"Glossary validation failed for {path}: {exc}"
        raise IngestError(msg) from exc


def load_glossary_csv(path: Path) -> Glossary:
    try:
        with path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
    except OSError as exc:
        msg = f"Cannot read CSV file: {path}"
        raise IngestError(msg) from exc

    if not rows:
        msg = "CSV file is empty"
        raise IngestError(msg)

    terms: list[dict[str, Any]] = []
    for row in rows:
        term: dict[str, Any] = {
            "id": row.get("id", "").strip(),
            "preferred_label": row.get("preferred_label", "").strip(),
            "definition": row.get("definition", "").strip(),
            "status": row.get("status", "draft").strip(),
            "language": row.get("language", "en").strip() or "en",
        }
        for field in (
            "abbreviation",
            "domain",
            "steward",
            "version",
            "source_url",
            "licence",
            "licence_url",
            "definition_method",
            "reuse_status",
        ):
            val = row.get(field, "").strip()
            if val:
                term[field] = val
        syns = row.get("synonyms", "").strip()
        if syns:
            term["synonyms"] = [s.strip() for s in syns.split("|") if s.strip()]
        rel = row.get("related_terms", "").strip()
        if rel:
            term["related_terms"] = [s.strip() for s in rel.split("|") if s.strip()]
        terms.append(term)

    data = {
        "metadata": {
            "title": path.stem,
            "description": f"Imported from {path.name}",
            "schema_version": "1.0.0",
        },
        "terms": terms,
    }
    try:
        return Glossary.model_validate(data)
    except Exception as exc:
        msg = f"CSV import validation failed: {exc}"
        raise IngestError(msg) from exc


def load_glossary(path: Path) -> Glossary:
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return load_glossary_yaml(path)
    if suffix == ".csv":
        return load_glossary_csv(path)
    msg = f"Unsupported glossary format: {suffix}"
    raise IngestError(msg)


def glossary_to_csv_rows(glossary: Glossary, profile: str = "human") -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for t in glossary.terms:
        row = {
            "id": t.id,
            "preferred_label": t.preferred_label,
            "definition": t.definition,
            "status": t.status.value,
            "language": t.language,
            "abbreviation": t.abbreviation or "",
            "domain": t.domain or "",
            "steward": t.steward or "",
            "version": t.version or "",
            "synonyms": "|".join(t.synonyms),
            "related_terms": "|".join(t.related_terms),
            "source_url": t.source_url or "",
            "licence": t.licence or "",
        }
        if profile == "roundtrip":
            row["licence_url"] = t.licence_url or ""
            row["definition_method"] = t.definition_method or ""
            row["reuse_status"] = t.reuse_status.value if t.reuse_status else ""
        rows.append(row)
    return rows
