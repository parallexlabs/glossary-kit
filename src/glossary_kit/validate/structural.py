from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

import jsonschema
from pydantic import ValidationError

from glossary_kit.diagnostics.models import Diagnostic, Severity
from glossary_kit.domain.models import Glossary, PublicationVisibility, TermStatus
from glossary_kit.domain.urls import is_safe_http_url
from glossary_kit.exports.slugs import validate_slug_safe_ids
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


def pydantic_errors_to_diagnostics(exc: ValidationError) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for err in exc.errors():
        if err["loc"]:
            loc = ".".join(str(p) for p in err["loc"])
        elif "at least one term" in err["msg"].lower():
            loc = "terms"
        else:
            loc = "root"
        diagnostics.append(
            Diagnostic(
                code="GLOS-STRUCT-001",
                severity=Severity.ERROR,
                path=loc,
                message=err["msg"],
                rule_id="GLOS-STRUCT-001",
            )
        )
    return diagnostics


def _validate_dictionary_bindings(glossary: Glossary) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    ids = glossary.term_ids()
    header_map: dict[str, tuple[str, int]] = {}

    for idx, term in enumerate(glossary.terms):
        base = f"terms[{idx}]"
        for bind_idx, binding in enumerate(term.dictionary_bindings):
            bind_path = f"{base}.dictionary_bindings[{bind_idx}]"
            if binding.term_id not in ids:
                diagnostics.append(
                    Diagnostic(
                        code="DICT-BIND-002",
                        severity=Severity.ERROR,
                        path=f"{bind_path}.term_id",
                        message=(
                            f"Dictionary binding references unknown term_id "
                            f"'{binding.term_id}'"
                        ),
                        rule_id="DICT-BIND-002",
                    )
                )
            if binding.term_id != term.id:
                diagnostics.append(
                    Diagnostic(
                        code="DICT-BIND-002",
                        severity=Severity.ERROR,
                        path=f"{bind_path}.term_id",
                        message=(
                            f"Dictionary binding term_id '{binding.term_id}' "
                            f"does not match owning term '{term.id}'"
                        ),
                        rule_id="DICT-BIND-002",
                    )
                )
            header_key = binding.header.lower()
            if header_key in header_map:
                _prev_term, prev_idx = header_map[header_key]
                diagnostics.append(
                    Diagnostic(
                        code="DICT-BIND-003",
                        severity=Severity.ERROR,
                        path=f"{bind_path}.header",
                        message=(
                            f"Duplicate dictionary binding header '{binding.header}' "
                            f"(also at terms[{prev_idx}].dictionary_bindings)"
                        ),
                        rule_id="DICT-BIND-003",
                    )
                )
            else:
                header_map[header_key] = (term.id, idx)

    return diagnostics


def _validate_slug_safe_term_ids(glossary: Glossary) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    messages = validate_slug_safe_ids([t.id for t in glossary.terms])
    for message in messages:
        diagnostics.append(
            Diagnostic(
                code="GLOS-STRUCT-004",
                severity=Severity.ERROR,
                path="terms",
                message=message,
                rule_id="GLOS-STRUCT-004",
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
        for rel_idx, rel in enumerate(term.related_terms):
            if rel not in ids:
                diagnostics.append(
                    Diagnostic(
                        code="GLOS-REL-001",
                        severity=Severity.ERROR,
                        path=f"{base}.related_terms[{rel_idx}]",
                        message=f"Related term '{rel}' does not exist",
                        rule_id="GLOS-REL-001",
                    )
                )
                continue
            rel_term = glossary.term_by_id(rel)
            if rel_term is not None:
                term_vis = (
                    term.publication.visibility
                    if term.publication
                    else PublicationVisibility.PUBLIC
                )
                rel_vis = (
                    rel_term.publication.visibility
                    if rel_term.publication
                    else PublicationVisibility.PUBLIC
                )
                if (
                    term_vis == PublicationVisibility.PUBLIC
                    and rel_vis == PublicationVisibility.INTERNAL
                ):
                    diagnostics.append(
                        Diagnostic(
                            code="GLOS-REL-003",
                            severity=Severity.ERROR,
                            path=f"{base}.related_terms[{rel_idx}]",
                            message=(
                                f"Public term references internal related term '{rel}'"
                            ),
                            rule_id="GLOS-REL-003",
                        )
                    )

        for url_field in ("source_url", "licence_url"):
            url_val = getattr(term, url_field)
            if url_val and not is_safe_http_url(url_val):
                diagnostics.append(
                    Diagnostic(
                        code="GLOS-STRUCT-001",
                        severity=Severity.ERROR,
                        path=f"{base}.{url_field}",
                        message=(
                            f"Unsafe or malformed URL in {url_field} "
                            f"(only http/https absolute URLs allowed)"
                        ),
                        rule_id="GLOS-STRUCT-001",
                    )
                )

        for src_idx, source in enumerate(term.sources):
            if source.url and not is_safe_http_url(source.url):
                diagnostics.append(
                    Diagnostic(
                        code="GLOS-STRUCT-001",
                        severity=Severity.ERROR,
                        path=f"{base}.sources[{src_idx}].url",
                        message=(
                            "Unsafe or malformed source URL "
                            "(only http/https absolute URLs allowed)"
                        ),
                        rule_id="GLOS-STRUCT-001",
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
    diagnostics.extend(_validate_dictionary_bindings(glossary))
    diagnostics.extend(_validate_slug_safe_term_ids(glossary))
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
        return None, pydantic_errors_to_diagnostics(exc)

    raw_data: dict[str, Any]
    if path.suffix.lower() == ".csv":
        raw_data = glossary.model_dump(mode="json")
    else:
        import yaml

        raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    diagnostics = validate_json_schema(raw_data) if isinstance(raw_data, dict) else []
    diagnostics.extend(validate_structure(glossary))
    return glossary, diagnostics
