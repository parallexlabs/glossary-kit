from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

import jsonschema
from pydantic import ValidationError

from glossary_kit.diagnostics.models import Diagnostic, Severity
from glossary_kit.domain.models import Glossary, TermStatus
from glossary_kit.ingest.loader import IngestError, load_glossary


def _schema_path() -> Path:
    return Path(str(files("glossary_kit.resources.jsonschema") / "glossary.schema.json"))


def get_json_schema() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_schema_path().read_text(encoding="utf-8")))


def validate_json_schema(data: dict[str, Any]) -> list[Diagnostic]:
    schema = get_json_schema()
    validator = jsonschema.Draft202012Validator(schema)
    diagnostics: list[Diagnostic] = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.path) or "root"
        diagnostics.append(
            Diagnostic(
                code="GLOS-STRUCT-001",
                severity=Severity.ERROR,
                path=path,
                message=error.message,
                rule_id="GLOS-STRUCT-001",
            )
        )
    return diagnostics


def validate_structure(glossary: Glossary) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    seen_ids: dict[str, int] = {}
    seen_labels: dict[tuple[str, str], int] = {}

    for idx, term in enumerate(glossary.terms):
        base = f"terms[{idx}]"
        for field in ("id", "preferred_label", "definition", "status", "language"):
            val = getattr(term, field, None)
            if val is None or (isinstance(val, str) and not val.strip()):
                diagnostics.append(
                    Diagnostic(
                        code="GLOS-STRUCT-001",
                        severity=Severity.ERROR,
                        path=f"{base}.{field}",
                        message=f"Required field '{field}' is missing or empty",
                        rule_id="GLOS-STRUCT-001",
                    )
                )

        if term.id in seen_ids:
            diagnostics.append(
                Diagnostic(
                    code="GLOS-STRUCT-002",
                    severity=Severity.ERROR,
                    path=f"{base}.id",
                    message=f"Duplicate term id '{term.id}' (also at terms[{seen_ids[term.id]}])",
                    rule_id="GLOS-STRUCT-002",
                )
            )
        else:
            seen_ids[term.id] = idx

        label_key = (term.language.lower(), term.preferred_label.lower())
        if label_key in seen_labels:
            diagnostics.append(
                Diagnostic(
                    code="GLOS-STRUCT-003",
                    severity=Severity.ERROR,
                    path=f"{base}.preferred_label",
                    message=(
                        f"Duplicate preferred label '{term.preferred_label}' "
                        f"for language '{term.language}'"
                    ),
                    rule_id="GLOS-STRUCT-003",
                )
            )
        else:
            seen_labels[label_key] = idx

        for syn_idx, syn in enumerate(term.synonyms):
            if syn.lower() == term.preferred_label.lower():
                diagnostics.append(
                    Diagnostic(
                        code="GLOS-STRUCT-003",
                        severity=Severity.ERROR,
                        path=f"{base}.synonyms[{syn_idx}]",
                        message=f"Synonym '{syn}' is identical to preferred_label",
                        rule_id="GLOS-STRUCT-003",
                    )
                )

        ids = glossary.term_ids()
        for rel in term.related_terms:
            if rel not in ids:
                diagnostics.append(
                    Diagnostic(
                        code="GLOS-REL-001",
                        severity=Severity.ERROR,
                        path=f"{base}.related_terms",
                        message=f"Related term '{rel}' does not exist",
                        rule_id="GLOS-REL-001",
                    )
                )

        if term.replaces and term.replaces not in ids:
            diagnostics.append(
                Diagnostic(
                    code="GLOS-REL-001",
                    severity=Severity.ERROR,
                    path=f"{base}.replaces",
                    message=f"Replaces target '{term.replaces}' does not exist",
                    rule_id="GLOS-REL-001",
                )
            )
        if term.replaced_by and term.replaced_by not in ids:
            diagnostics.append(
                Diagnostic(
                    code="GLOS-REL-001",
                    severity=Severity.ERROR,
                    path=f"{base}.replaced_by",
                    message=f"Replaced_by target '{term.replaced_by}' does not exist",
                    rule_id="GLOS-REL-001",
                )
            )

        if term.status == TermStatus.APPROVED:
            if not term.steward:
                diagnostics.append(
                    Diagnostic(
                        code="GLOS-GOV-001",
                        severity=Severity.ERROR,
                        path=f"{base}.steward",
                        message="Approved term must have a steward",
                        rule_id="GLOS-GOV-001",
                    )
                )
            has_source = bool(term.source_url) or any(
                s.url or s.citation for s in term.sources
            )
            if not has_source:
                diagnostics.append(
                    Diagnostic(
                        code="GLOS-GOV-002",
                        severity=Severity.ERROR,
                        path=f"{base}.sources",
                        message="Approved term must have source URL or citation",
                        rule_id="GLOS-GOV-002",
                    )
                )

    diagnostics.extend(_check_replaces_cycles(glossary))
    return diagnostics


def _check_replaces_cycles(glossary: Glossary) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    graph: dict[str, str | None] = {}
    for term in glossary.terms:
        graph[term.id] = term.replaces

    for start in graph:
        visited: set[str] = set()
        current: str | None = start
        while current and current in graph:
            if current in visited:
                diagnostics.append(
                    Diagnostic(
                        code="GLOS-REL-002",
                        severity=Severity.ERROR,
                        path="terms[?].replaces",
                        message=f"Cycle detected in replaces chain involving '{current}'",
                        rule_id="GLOS-REL-002",
                    )
                )
                break
            visited.add(current)
            current = graph.get(current)
    return diagnostics


def validate_glossary_path(path: Path) -> tuple[Glossary | None, list[Diagnostic]]:
    try:
        glossary = load_glossary(path)
    except IngestError as exc:
        return None, [
            Diagnostic(
                code="INPUT-001",
                severity=Severity.ERROR,
                path=str(path),
                message=str(exc),
            )
        ]
    except ValidationError as exc:
        diagnostics: list[Diagnostic] = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"])
            diagnostics.append(
                Diagnostic(
                    code="GLOS-STRUCT-001",
                    severity=Severity.ERROR,
                    path=loc,
                    message=err["msg"],
                    rule_id="GLOS-STRUCT-001",
                )
            )
        return None, diagnostics

    raw_data: dict[str, Any]
    if path.suffix.lower() == ".csv":
        raw_data = glossary.model_dump(mode="json")
    else:
        import yaml

        raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    diagnostics = validate_json_schema(raw_data) if isinstance(raw_data, dict) else []
    diagnostics.extend(validate_structure(glossary))
    return glossary, diagnostics
