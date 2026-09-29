from __future__ import annotations

from pathlib import Path

import pytest
from tests.helpers import make_glossary, make_term

from glossary_kit.assess.maturity import (
    assess_maturity,
    load_rubric,
    write_maturity_html,
    write_maturity_json,
)
from glossary_kit.domain.models import TermStatus
from glossary_kit.ingest.loader import (
    IngestError,
    load_glossary,
    load_glossary_csv,
    load_glossary_yaml,
)


def test_load_minimal_glossary(minimal_glossary_path: Path) -> None:
    glossary = load_glossary(minimal_glossary_path)
    assert len(glossary.terms) == 2
    assert glossary.metadata.schema_version == "1.0.0"


def test_load_glossary_yaml_direct(minimal_glossary_path: Path) -> None:
    glossary = load_glossary_yaml(minimal_glossary_path)
    assert glossary.metadata.title == "Minimal Test Glossary"


def test_load_glossary_unsupported_suffix(tmp_path: Path) -> None:
    bad = tmp_path / "file.txt"
    bad.write_text("hello", encoding="utf-8")
    with pytest.raises(IngestError, match="Unsupported glossary format"):
        load_glossary(bad)


def test_load_glossary_yaml_not_mapping(tmp_path: Path) -> None:
    bad = tmp_path / "list.yaml"
    bad.write_text("- item\n", encoding="utf-8")
    with pytest.raises(IngestError, match="Expected mapping"):
        load_glossary_yaml(bad)


def test_load_glossary_yaml_unreadable(tmp_path: Path) -> None:
    with pytest.raises(IngestError, match="Cannot read glossary file"):
        load_glossary_yaml(tmp_path / "missing.yaml")


def test_load_glossary_csv_roundtrip_fields(minimal_glossary_path: Path, tmp_path: Path) -> None:
    from glossary_kit.exports.csv_export import export_csv

    glossary = load_glossary(minimal_glossary_path)
    csv_path = tmp_path / "terms.csv"
    export_csv(glossary, csv_path, profile="roundtrip")
    imported = load_glossary_csv(csv_path)
    assert len(imported.terms) == len(glossary.terms)


def test_load_glossary_csv_empty(tmp_path: Path) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("id,preferred_label\n", encoding="utf-8")
    with pytest.raises(IngestError, match="CSV file is empty"):
        load_glossary_csv(csv_path)


def test_load_glossary_csv_unreadable(tmp_path: Path) -> None:
    with pytest.raises(IngestError, match="Cannot read CSV file"):
        load_glossary_csv(tmp_path / "missing.csv")


def test_glossary_term_helpers() -> None:
    glossary = make_glossary(make_term(id="a"), make_term(id="b", preferred_label="Beta"))
    assert glossary.term_ids() == {"a", "b"}
    assert glossary.term_by_id("b") is not None
    assert glossary.term_by_id("missing") is None
    assert len(glossary.public_terms()) == 2


def test_term_synonym_coercion_string() -> None:
    term = make_term(synonyms="one|two|three")  # type: ignore[arg-type]
    assert term.synonyms == ["one", "two", "three"]


def test_assess_produces_dimensions(sample_glossary_path: Path) -> None:
    glossary = load_glossary(sample_glossary_path)
    report = assess_maturity(glossary)
    assert len(report["dimensions"]) >= 5
    assert report["total_score"] >= 0
    assert "disclaimer" in report


def test_assess_sparse_glossary_reports_gaps() -> None:
    glossary = make_glossary(make_term(steward=None, source_url=None, domain=None))
    report = assess_maturity(glossary)
    assert report["gaps"]
    assert report["percentage"] <= 100


def test_assess_lifecycle_and_publication_dimensions() -> None:
    glossary = make_glossary(
        make_term(id="old", status=TermStatus.DEPRECATED, replaced_by="new"),
        make_term(id="new", status=TermStatus.APPROVED, steward="s", source_url="https://x.example"),
    )
    report = assess_maturity(glossary)
    dim_ids = {d["id"] for d in report["dimensions"]}
    assert "lifecycle" in dim_ids
    assert "publication" in dim_ids


def test_load_rubric_has_dimensions() -> None:
    rubric = load_rubric()
    assert isinstance(rubric["dimensions"], list)


def test_write_maturity_outputs(tmp_path: Path) -> None:
    glossary = make_glossary(make_term())
    report = assess_maturity(glossary)
    html_path = tmp_path / "maturity.html"
    json_path = tmp_path / "maturity.json"
    write_maturity_html(report, html_path)
    write_maturity_json(report, json_path)
    assert "Glossary Maturity Report" in html_path.read_text()
    assert json_path.read_text().startswith("{")


def test_validate_structure_passes(minimal_glossary_path: Path) -> None:
    from glossary_kit.validate.structural import validate_structure

    glossary = load_glossary(minimal_glossary_path)
    diagnostics = validate_structure(glossary)
    assert not any(d.severity.value == "error" for d in diagnostics)


def test_lint_empty_definition() -> None:
    from glossary_kit.lint.engine import lint_glossary

    glossary = make_glossary(make_term(definition="   "))
    diagnostics = lint_glossary(glossary)
    assert any(d.code == "GLOS-DEF-001" for d in diagnostics)
