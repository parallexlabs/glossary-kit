from __future__ import annotations

import json

from glossary_kit.diagnostics.models import (
    Diagnostic,
    Severity,
    format_diagnostics_json,
    format_diagnostics_sarif,
    format_diagnostics_text,
)


def _sample_diags() -> list[Diagnostic]:
    return [
        Diagnostic(
            code="GLOS-DEF-001",
            severity=Severity.ERROR,
            path="terms[0].definition",
            message="Definition must not be empty",
            rule_id="GLOS-DEF-001",
        ),
        Diagnostic(
            code="GLOS-DEF-003",
            severity=Severity.WARNING,
            path="terms[1].preferred_label",
            message="Preferred label appears plural",
            rule_id="GLOS-DEF-003",
        ),
        Diagnostic(
            code="DICT-HEAD-001",
            severity=Severity.SUGGESTION,
            path="headers.col",
            message="Did you mean col_a?",
            rule_id="DICT-HEAD-001",
        ),
    ]


def test_format_diagnostics_text() -> None:
    text = format_diagnostics_text(_sample_diags())
    assert "[ERROR] GLOS-DEF-001 at terms[0].definition" in text
    assert "[WARNING] GLOS-DEF-003" in text
    assert "[SUGGESTION] DICT-HEAD-001" in text


def test_format_diagnostics_json_is_valid() -> None:
    payload = json.loads(format_diagnostics_json(_sample_diags()))
    assert len(payload) == 3
    assert payload[0]["severity"] == "error"
    assert payload[0]["code"] == "GLOS-DEF-001"


def test_diagnostic_to_dict() -> None:
    diag = _sample_diags()[0]
    data = diag.to_dict()
    assert data["rule_id"] == "GLOS-DEF-001"
    assert data["severity"] == "error"


def test_format_diagnostics_sarif_structure() -> None:
    sarif = json.loads(format_diagnostics_sarif(_sample_diags()))
    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "glossary-kit"
    assert len(run["results"]) == 1
    assert run["results"][0]["ruleId"] == "GLOS-DEF-001"


def test_format_diagnostics_sarif_omits_warnings() -> None:
    sarif = json.loads(format_diagnostics_sarif(_sample_diags()))
    rule_ids = {r["ruleId"] for r in sarif["runs"][0]["results"]}
    assert "GLOS-DEF-003" not in rule_ids


def test_format_diagnostics_sarif_custom_tool_name() -> None:
    sarif = json.loads(format_diagnostics_sarif(_sample_diags(), tool_name="custom-tool"))
    assert sarif["runs"][0]["tool"]["driver"]["name"] == "custom-tool"
