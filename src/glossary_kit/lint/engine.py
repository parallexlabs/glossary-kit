from __future__ import annotations

import re

from glossary_kit.diagnostics.models import Diagnostic, Severity
from glossary_kit.domain.models import Glossary, TermStatus


def lint_glossary(glossary: Glossary, profile: str = "standard") -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    strict = profile == "strict"

    for idx, term in enumerate(glossary.terms):
        base = f"terms[{idx}]"
        definition = term.definition.strip()
        label = term.preferred_label.strip()

        if not definition:
            diagnostics.append(
                Diagnostic(
                    code="GLOS-DEF-001",
                    severity=Severity.ERROR,
                    path=f"{base}.definition",
                    message="Definition must not be empty",
                    rule_id="GLOS-DEF-001",
                )
            )
            continue

        if definition.lower() == label.lower():
            diagnostics.append(
                Diagnostic(
                    code="GLOS-DEF-002",
                    severity=Severity.ERROR,
                    path=f"{base}.definition",
                    message="Definition must not be identical to preferred label (tautology)",
                    rule_id="GLOS-DEF-002",
                )
            )

        if label.endswith("s") and not label.endswith("ss") and len(label) > 3:
            diagnostics.append(
                Diagnostic(
                    code="GLOS-DEF-003",
                    severity=Severity.WARNING,
                    path=f"{base}.preferred_label",
                    message=(
                        "Preferred label appears plural; "
                        "ISO/IEC 11179-4 recommends singular form"
                    ),
                    rule_id="GLOS-DEF-003",
                )
            )

        token_pattern = re.compile(rf"\b{re.escape(label)}\b", re.IGNORECASE)
        if token_pattern.search(definition) and definition.lower() != label.lower():
            diagnostics.append(
                Diagnostic(
                    code="GLOS-DEF-004",
                    severity=Severity.WARNING,
                    path=f"{base}.definition",
                    message="Definition contains preferred label as standalone token",
                    rule_id="GLOS-DEF-004",
                )
            )

        neg_patterns = (r"^not a\b", r"^does not\b", r"^is not\b")
        if any(re.search(p, definition, re.IGNORECASE) for p in neg_patterns):
            diagnostics.append(
                Diagnostic(
                    code="GLOS-DEF-005",
                    severity=Severity.WARNING,
                    path=f"{base}.definition",
                    message=(
                        "Definition uses negative phrasing only; "
                        "prefer affirmative formulation"
                    ),
                    rule_id="GLOS-DEF-005",
                )
            )

        if term.abbreviation:
            abbr_pattern = re.compile(rf"\b{re.escape(term.abbreviation)}\b")
            if not abbr_pattern.search(definition):
                diagnostics.append(
                    Diagnostic(
                        code="GLOS-LEX-001",
                        severity=Severity.WARNING,
                        path=f"{base}.abbreviation",
                        message=f"Abbreviation '{term.abbreviation}' not expanded in definition",
                        rule_id="GLOS-LEX-001",
                    )
                )

        if term.status == TermStatus.DEPRECATED and not term.replaced_by:
            diagnostics.append(
                Diagnostic(
                    code="GLOS-GOV-003",
                    severity=Severity.WARNING,
                    path=f"{base}.replaced_by",
                    message="Deprecated terms should link to a replacement term or rationale",
                    rule_id="GLOS-GOV-003",
                )
            )

        if strict and term.status == TermStatus.APPROVED and not term.domain:
            diagnostics.append(
                Diagnostic(
                    code="GLOS-GOV-STRICT-001",
                    severity=Severity.WARNING,
                    path=f"{base}.domain",
                    message="Strict profile recommends domain for approved terms",
                    rule_id="GLOS-GOV-STRICT-001",
                )
            )

    return diagnostics
