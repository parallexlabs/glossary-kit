from __future__ import annotations

from glossary_kit.rules.catalog import explain_rule, list_rules


def test_list_rules_returns_sorted_catalog() -> None:
    rules = list_rules()
    codes = [r.code for r in rules]
    assert codes == sorted(codes)
    assert "GLOS-DEF-001" in codes
    assert "DICT-BIND-001" in codes


def test_explain_rule_known_code() -> None:
    rule = explain_rule("glos-def-001")
    assert rule is not None
    assert rule.code == "GLOS-DEF-001"
    assert rule.severity == "error"


def test_explain_rule_unknown_code() -> None:
    assert explain_rule("GLOS-NOPE-999") is None
