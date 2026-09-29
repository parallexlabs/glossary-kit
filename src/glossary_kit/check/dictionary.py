from __future__ import annotations

import csv
from pathlib import Path

import yaml

from glossary_kit.diagnostics.models import Diagnostic, Severity
from glossary_kit.domain.models import Glossary


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

    binding_map: dict[str, str] = {}
    label_map: dict[str, str] = {}
    for term in glossary.terms:
        label_map[term.preferred_label.lower()] = term.id
        for binding in term.dictionary_bindings:
            binding_map[binding.header.lower()] = binding.term_id

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
                            f"Explicit binding header '{binding.header}' "
                            f"not found in CSV"
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

    fields = data.get("fields", [])
    if not isinstance(fields, list):
        return [
            Diagnostic(
                code="DICT-FRIC-001",
                severity=Severity.ERROR,
                path="fields",
                message="Frictionless schema missing fields array",
                rule_id="DICT-FRIC-001",
            )
        ]

    glossary_headers = {t.preferred_label.lower() for t in glossary.terms}
    binding_headers = {
        b.header.lower()
        for t in glossary.terms
        for b in t.dictionary_bindings
    }
    known = glossary_headers | binding_headers

    for idx, field in enumerate(fields):
        if not isinstance(field, dict):
            continue
        name = str(field.get("name", ""))
        ftype = field.get("type", "string")
        if name.lower() not in known:
            diagnostics.append(
                Diagnostic(
                    code="DICT-FRIC-001",
                    severity=Severity.ERROR,
                    path=f"fields[{idx}].name",
                    message=(
                        f"Frictionless field '{name}' (type: {ftype}) "
                        f"not mapped to glossary term"
                    ),
                    rule_id="DICT-FRIC-001",
                )
            )

    return diagnostics


def _fuzzy_match(header: str, candidates: list[str]) -> str | None:
    h = header.lower().replace("_", " ").replace("-", " ")
    for c in candidates:
        if h in c or c in h:
            return c
    return None
