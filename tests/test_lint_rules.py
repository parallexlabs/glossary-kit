from __future__ import annotations

from tests.helpers import make_glossary, make_term

from glossary_kit.lint.engine import lint_glossary


def _codes(glossary: object) -> set[str]:
    from glossary_kit.domain.models import Glossary

    assert isinstance(glossary, Glossary)
    return {d.code for d in lint_glossary(glossary)}


def test_glos_def_001_passes_with_definition() -> None:
    glossary = make_glossary(make_term(definition="Valid definition text."))
    assert "GLOS-DEF-001" not in _codes(glossary)


def test_glos_def_001_fails_on_empty_definition() -> None:
    glossary = make_glossary(make_term(definition="   "))
    assert "GLOS-DEF-001" in _codes(glossary)


def test_glos_def_002_passes_when_definition_differs() -> None:
    glossary = make_glossary(
        make_term(preferred_label="Widget", definition="A physical control device.")
    )
    assert "GLOS-DEF-002" not in _codes(glossary)


def test_glos_def_002_fails_on_tautology() -> None:
    glossary = make_glossary(
        make_term(preferred_label="Widget", definition="Widget")
    )
    assert "GLOS-DEF-002" in _codes(glossary)


def test_glos_def_003_passes_with_singular_label() -> None:
    glossary = make_glossary(make_term(preferred_label="Record"))
    assert "GLOS-DEF-003" not in _codes(glossary)


def test_glos_def_003_fails_on_plural_label() -> None:
    glossary = make_glossary(make_term(preferred_label="Records"))
    assert "GLOS-DEF-003" in _codes(glossary)


def test_glos_def_004_passes_without_self_reference() -> None:
    glossary = make_glossary(
        make_term(preferred_label="Dataset", definition="A structured collection of values.")
    )
    assert "GLOS-DEF-004" not in _codes(glossary)


def test_glos_def_004_fails_when_definition_contains_label() -> None:
    glossary = make_glossary(
        make_term(
            preferred_label="Dataset",
            definition="A Dataset is a structured collection of values.",
        )
    )
    assert "GLOS-DEF-004" in _codes(glossary)


def test_glos_def_005_passes_with_affirmative_phrasing() -> None:
    glossary = make_glossary(
        make_term(definition="A structured collection of related records.")
    )
    assert "GLOS-DEF-005" not in _codes(glossary)


def test_glos_def_005_fails_on_negative_phrasing() -> None:
    glossary = make_glossary(make_term(definition="Is not a database table."))
    assert "GLOS-DEF-005" in _codes(glossary)


def test_glos_lex_001_passes_when_abbreviation_expanded() -> None:
    glossary = make_glossary(
        make_term(abbreviation="API", definition="An API exposes programmatic access.")
    )
    assert "GLOS-LEX-001" not in _codes(glossary)


def test_glos_lex_001_fails_when_abbreviation_missing() -> None:
    glossary = make_glossary(
        make_term(abbreviation="API", definition="Programmatic access endpoint.")
    )
    assert "GLOS-LEX-001" in _codes(glossary)


def test_glos_gov_003_passes_when_deprecated_has_replacement() -> None:
    glossary = make_glossary(
        make_term(id="old", status="deprecated", replaced_by="new"),
        make_term(id="new"),
    )
    assert "GLOS-GOV-003" not in _codes(glossary)


def test_glos_gov_003_fails_when_deprecated_without_replacement() -> None:
    glossary = make_glossary(make_term(status="deprecated"))
    assert "GLOS-GOV-003" in _codes(glossary)


def test_glos_gov_strict_001_passes_in_standard_profile() -> None:
    glossary = make_glossary(
        make_term(status="approved", steward="s", source_url="https://example.com")
    )
    diags = lint_glossary(glossary, profile="standard")
    assert not any(d.code == "GLOS-GOV-STRICT-001" for d in diags)


def test_glos_gov_strict_001_fails_in_strict_profile_without_domain() -> None:
    glossary = make_glossary(
        make_term(
            id="approved",
            status="approved",
            steward="s",
            source_url="https://example.com",
            domain=None,
        )
    )
    diags = lint_glossary(glossary, profile="strict")
    assert any(d.code == "GLOS-GOV-STRICT-001" for d in diags)
