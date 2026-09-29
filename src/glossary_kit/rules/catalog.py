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
        "ISO/IEC 11179-3/4",
        "Required fields present (id, label, definition, status, language)",
    ),
    "GLOS-STRUCT-002": RuleInfo(
        "GLOS-STRUCT-002",
        "Unique term id",
        "error",
        "ISO/IEC 11179",
        "Term id must be unique within the glossary",
    ),
    "GLOS-STRUCT-003": RuleInfo(
        "GLOS-STRUCT-003",
        "Unique preferred label",
        "error",
        "SKOS",
        "Duplicate preferred label or synonym conflict",
    ),
    "GLOS-REL-001": RuleInfo(
        "GLOS-REL-001",
        "Resolvable references",
        "error",
        "SKOS / ISO 1087",
        "Related, replaces, and replaced_by links must resolve",
    ),
    "GLOS-REL-002": RuleInfo(
        "GLOS-REL-002",
        "Acyclic replaces",
        "error",
        "SKOS",
        "No cycles in replaces relation graph",
    ),
    "GLOS-GOV-001": RuleInfo(
        "GLOS-GOV-001",
        "Steward required",
        "error",
        "ISO/IEC 38505-1",
        "Approved terms must have a steward",
    ),
    "GLOS-GOV-002": RuleInfo(
        "GLOS-GOV-002",
        "Source required",
        "error",
        "ISO/IEC 11179 / GC open data",
        "Approved terms must have source URL or citation",
    ),
    "GLOS-GOV-003": RuleInfo(
        "GLOS-GOV-003",
        "Deprecated replacement",
        "warning",
        "DAMA-DMBOK (lifecycle)",
        "Deprecated terms should have replaced_by link or documented rationale",
    ),
    "GLOS-DEF-001": RuleInfo(
        "GLOS-DEF-001",
        "Non-empty definition",
        "error",
        "ISO/IEC 11179-4-inspired",
        "Definition must not be empty",
    ),
    "GLOS-DEF-002": RuleInfo(
        "GLOS-DEF-002",
        "No tautology",
        "error",
        "ISO/IEC 11179-4-inspired",
        "Definition must not equal preferred label",
    ),
    "GLOS-DEF-003": RuleInfo(
        "GLOS-DEF-003",
        "Singular label",
        "warning",
        "ISO/IEC 11179-4-inspired",
        "Preferred label should use singular form (heuristic)",
    ),
    "GLOS-DEF-004": RuleInfo(
        "GLOS-DEF-004",
        "Self-reference",
        "warning",
        "ISO 704",
        "Definition should not contain preferred label as token",
    ),
    "GLOS-DEF-005": RuleInfo(
        "GLOS-DEF-005",
        "Affirmative phrasing",
        "warning",
        "ISO/IEC 11179-4-inspired",
        "Avoid definitions that only negate",
    ),
    "GLOS-LEX-001": RuleInfo(
        "GLOS-LEX-001",
        "Abbreviation expansion",
        "warning",
        "ISO 704",
        "Abbreviation should appear in definition",
    ),
    "DICT-HEAD-001": RuleInfo(
        "DICT-HEAD-001",
        "CSV header mapping",
        "error",
        "Frictionless",
        "CSV headers must map to glossary terms or bindings",
    ),
    "DICT-FRIC-001": RuleInfo(
        "DICT-FRIC-001",
        "Frictionless field mapping",
        "error",
        "Frictionless Table Schema",
        "Frictionless fields must map to glossary terms",
    ),
    "DICT-BIND-001": RuleInfo(
        "DICT-BIND-001",
        "Explicit bindings",
        "error",
        "Project convention",
        "Explicit dictionary_bindings must match CSV headers",
    ),
}


def list_rules() -> list[RuleInfo]:
    return [RULES[k] for k in sorted(RULES)]


def explain_rule(code: str) -> RuleInfo | None:
    return RULES.get(code.upper())
