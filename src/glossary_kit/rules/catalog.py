from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleInfo:
    code: str
    name: str
    severity: str
    standard: str
    description: str


RULES: dict[str, RuleInfo] = {
    "GLOS-STRUCT-001": RuleInfo(
        "GLOS-STRUCT-001",
        "Required fields",
        "error",
        "ISO/IEC 11179-3/4-informed",
        "Required fields present (id, label, definition, status, language)",
    ),
    "GLOS-STRUCT-002": RuleInfo(
        "GLOS-STRUCT-002",
        "Unique term id",
        "error",
        "ISO/IEC 11179-informed",
        "Term id must be unique within the glossary",
    ),
    "GLOS-STRUCT-003": RuleInfo(
        "GLOS-STRUCT-003",
        "Unique preferred label",
        "error",
        "SKOS-informed",
        "Duplicate preferred label or synonym conflict",
    ),
    "GLOS-STRUCT-004": RuleInfo(
        "GLOS-STRUCT-004",
        "Slug-safe term ids",
        "error",
        "Project convention",
        "Term ids must be slug-safe and must not collide after slugging",
    ),
    "GLOS-REL-001": RuleInfo(
        "GLOS-REL-001",
        "Resolvable references",
        "error",
        "SKOS / ISO 1087-informed",
        "Related, replaces, and replaced_by links must resolve",
    ),
    "GLOS-REL-002": RuleInfo(
        "GLOS-REL-002",
        "Acyclic replaces",
        "error",
        "SKOS-informed",
        "No cycles in replaces relation graph",
    ),
    "GLOS-REL-003": RuleInfo(
        "GLOS-REL-003",
        "Public related targets",
        "error",
        "SKOS-informed",
        "Public terms must not reference internal related terms",
    ),
    "GLOS-GOV-001": RuleInfo(
        "GLOS-GOV-001",
        "Steward required",
        "error",
        "ISO/IEC 38505-1-informed",
        "Approved terms must have a steward",
    ),
    "GLOS-GOV-002": RuleInfo(
        "GLOS-GOV-002",
        "Source required",
        "error",
        "ISO/IEC 11179 / GC open data-informed",
        "Approved terms must have source URL or citation",
    ),
    "GLOS-GOV-003": RuleInfo(
        "GLOS-GOV-003",
        "Deprecated replacement",
        "warning",
        "DAMA-DMBOK-informed (lifecycle)",
        "Deprecated terms should have replaced_by link or documented rationale",
    ),
    "GLOS-DEF-001": RuleInfo(
        "GLOS-DEF-001",
        "Non-empty definition",
        "error",
        "ISO/IEC 11179-4-informed",
        "Definition must not be empty",
    ),
    "GLOS-DEF-002": RuleInfo(
        "GLOS-DEF-002",
        "No tautology",
        "error",
        "ISO/IEC 11179-4-informed",
        "Definition must not equal preferred label",
    ),
    "GLOS-DEF-003": RuleInfo(
        "GLOS-DEF-003",
        "Singular label",
        "warning",
        "ISO/IEC 11179-4-informed (strict profile)",
        "Preferred label should use singular form (heuristic, strict profile only)",
    ),
    "GLOS-DEF-004": RuleInfo(
        "GLOS-DEF-004",
        "Self-reference",
        "warning",
        "ISO 704-informed",
        "Definition should not contain preferred label as token",
    ),
    "GLOS-DEF-005": RuleInfo(
        "GLOS-DEF-005",
        "Affirmative phrasing",
        "warning",
        "ISO/IEC 11179-4-informed",
        "Avoid definitions that only negate",
    ),
    "GLOS-LEX-001": RuleInfo(
        "GLOS-LEX-001",
        "Abbreviation expansion",
        "warning",
        "ISO 704-informed",
        "Abbreviation should be expanded in definition using parentheses",
    ),
    "DICT-HEAD-001": RuleInfo(
        "DICT-HEAD-001",
        "CSV header mapping",
        "error",
        "Frictionless-informed",
        "CSV headers must map to glossary terms or bindings",
    ),
    "DICT-FRIC-001": RuleInfo(
        "DICT-FRIC-001",
        "Frictionless field mapping",
        "error",
        "Frictionless Table Schema-informed",
        "Frictionless fields must map to glossary terms",
    ),
    "DICT-FRIC-002": RuleInfo(
        "DICT-FRIC-002",
        "Frictionless field shape",
        "error",
        "Frictionless Table Schema-informed",
        "Frictionless field entries must be well-formed mappings with supported types",
    ),
    "DICT-BIND-001": RuleInfo(
        "DICT-BIND-001",
        "Explicit bindings",
        "error",
        "Project convention",
        "Explicit dictionary_bindings must match CSV headers",
    ),
    "DICT-BIND-002": RuleInfo(
        "DICT-BIND-002",
        "Binding term reference",
        "error",
        "Project convention",
        "Dictionary binding term_id must reference the owning term",
    ),
    "DICT-BIND-003": RuleInfo(
        "DICT-BIND-003",
        "Duplicate binding header",
        "error",
        "Project convention",
        "Dictionary binding headers must be unique across terms",
    ),
}


def list_rules() -> list[RuleInfo]:
    return [RULES[k] for k in sorted(RULES)]


def explain_rule(code: str) -> RuleInfo | None:
    return RULES.get(code.upper())
