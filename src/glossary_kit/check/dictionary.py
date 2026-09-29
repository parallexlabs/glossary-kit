from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

import yaml

from glossary_kit.diagnostics.models import Diagnostic, Severity
from glossary_kit.domain.models import Glossary

FRICTIONLESS_LOGICAL_TYPES = frozenset(
    {"string", "integer", "number", "boolean", "date", "datetime"}
)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
)


def build_binding_map(glossary: Glossary) -> dict[str, str]:
    """Return validated header-to-term_id bindings from glossary terms."""
    binding_map: dict[str, str] = {}
    for term in glossary.terms:
        for binding in term.dictionary_bindings:
            header_key = binding.header.lower()
            if header_key in binding_map and binding_map[header_key] != binding.term_id:
                continue
            binding_map[header_key] = binding.term_id
        binding_map[term.preferred_label.lower()] = term.id
    return binding_map


def check_dictionary_csv(
    csv_path: Path,
    glossary: Glossary,
    *,
    fuzzy: bool = False,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    try:
        with csv_path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            headers = reader.fieldnames or []
    except OSError as exc:
        return [
            Diagnostic(
                code="DICT-HEAD-001",
                severity=Severity.ERROR,
                path=str(csv_path),
                message=f"Cannot read dictionary CSV: {exc}",
                rule_id="DICT-HEAD-001",
            )
        ]

    binding_map = build_binding_map(glossary)
    label_map = {t.preferred_label.lower(): t.id for t in glossary.terms}

    for header in headers:
        h_lower = header.lower()
        if h_lower in binding_map:
            continue
        if h_lower in label_map:
            continue
        if fuzzy:
            suggestion = _fuzzy_match(header, list(binding_map.keys()) + list(label_map.keys()))
            if suggestion:
                diagnostics.append(
                    Diagnostic(
                        code="DICT-HEAD-001",
                        severity=Severity.SUGGESTION,
                        path=f"headers.{header}",
                        message=f"Header '{header}' unmapped; did you mean '{suggestion}'?",
                        rule_id="DICT-HEAD-001",
                    )
                )
                continue
        diagnostics.append(
            Diagnostic(
                code="DICT-HEAD-001",
                severity=Severity.ERROR,
                path=f"headers.{header}",
                message=f"CSV header '{header}' has no glossary binding or label match",
                rule_id="DICT-HEAD-001",
            )
        )

    for term in glossary.terms:
        for binding in term.dictionary_bindings:
            if binding.header.lower() not in {h.lower() for h in headers}:
                diagnostics.append(
                    Diagnostic(
                        code="DICT-BIND-001",
                        severity=Severity.ERROR,
                        path=f"terms.{term.id}.dictionary_bindings",
                        message=(
                            f"Explicit binding header '{binding.header}' not found in CSV"
                        ),
                        rule_id="DICT-BIND-001",
                    )
                )

    return diagnostics


def check_frictionless_schema(
    schema_path: Path,
    glossary: Glossary,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    try:
        raw = schema_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except OSError as exc:
        return [
            Diagnostic(
                code="DICT-FRIC-001",
                severity=Severity.ERROR,
                path=str(schema_path),
                message=f"Cannot read Frictionless schema: {exc}",
                rule_id="DICT-FRIC-001",
            )
        ]
    except yaml.YAMLError as exc:
        return [
            Diagnostic(
                code="DICT-FRIC-001",
                severity=Severity.ERROR,
                path=str(schema_path),
                message=f"Invalid YAML: {exc}",
                rule_id="DICT-FRIC-001",
            )
        ]

    if not isinstance(data, dict):
        return [
            Diagnostic(
                code="DICT-FRIC-001",
                severity=Severity.ERROR,
                path=str(schema_path),
                message="Frictionless schema must be a mapping",
                rule_id="DICT-FRIC-001",
            )
        ]

    fields = data.get("fields")
    if fields is None:
        return [
            Diagnostic(
                code="DICT-FRIC-001",
                severity=Severity.ERROR,
                path="fields",
                message="Frictionless schema missing fields array",
                rule_id="DICT-FRIC-001",
            )
        ]
    if not isinstance(fields, list):
        return [
            Diagnostic(
                code="DICT-FRIC-001",
                severity=Severity.ERROR,
                path="fields",
                message="Frictionless schema fields must be an array",
                rule_id="DICT-FRIC-001",
            )
        ]

    glossary_headers = {t.preferred_label.lower() for t in glossary.terms}
    binding_headers = {
        b.header.lower() for t in glossary.terms for b in t.dictionary_bindings
    }
    known = glossary_headers | binding_headers

    for idx, field in enumerate(fields):
        field_path = f"fields[{idx}]"
        if not isinstance(field, dict):
            diagnostics.append(
                Diagnostic(
                    code="DICT-FRIC-002",
                    severity=Severity.ERROR,
                    path=field_path,
                    message="Frictionless field entry must be a mapping",
                    rule_id="DICT-FRIC-002",
                )
            )
            continue

        name = str(field.get("name", "")).strip()
        if not name:
            diagnostics.append(
                Diagnostic(
                    code="DICT-FRIC-002",
                    severity=Severity.ERROR,
                    path=f"{field_path}.name",
                    message="Frictionless field is missing a non-empty name",
                    rule_id="DICT-FRIC-002",
                )
            )
            continue

        ftype = field.get("type", "string")
        if not isinstance(ftype, str) or ftype not in FRICTIONLESS_LOGICAL_TYPES:
            diagnostics.append(
                Diagnostic(
                    code="DICT-FRIC-002",
                    severity=Severity.ERROR,
                    path=f"{field_path}.type",
                    message=(
                        f"Unsupported Frictionless logical type '{ftype}' "
                        f"(expected one of {sorted(FRICTIONLESS_LOGICAL_TYPES)})"
                    ),
                    rule_id="DICT-FRIC-002",
                )
            )
            continue

        if name.lower() not in known:
            diagnostics.append(
                Diagnostic(
                    code="DICT-FRIC-001",
                    severity=Severity.ERROR,
                    path=f"{field_path}.name",
                    message=(
                        f"Frictionless field '{name}' (type: {ftype}) "
                        f"not mapped to glossary term"
                    ),
                    rule_id="DICT-FRIC-001",
                )
            )

        constraints = field.get("constraints")
        if constraints is not None and not isinstance(constraints, dict):
            diagnostics.append(
                Diagnostic(
                    code="DICT-FRIC-002",
                    severity=Severity.ERROR,
                    path=f"{field_path}.constraints",
                    message="Frictionless field constraints must be a mapping",
                    rule_id="DICT-FRIC-002",
                )
            )

    return diagnostics


def frictionless_type_matches(value: Any, logical_type: str) -> bool:
    """Documented logical-type comparison for Frictionless Table Schema fields."""
    if logical_type == "string":
        return isinstance(value, str)
    if logical_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if logical_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if logical_type == "boolean":
        return isinstance(value, bool)
    if logical_type == "date":
        return isinstance(value, str) and bool(_DATE_PATTERN.match(value))
    if logical_type == "datetime":
        return isinstance(value, str) and bool(_DATETIME_PATTERN.match(value))
    return False


def _fuzzy_match(header: str, candidates: list[str]) -> str | None:
    h = header.lower().replace("_", " ").replace("-", " ")
    for c in candidates:
        if h in c or c in h:
            return c
    return None
