from __future__ import annotations

import json
from pathlib import Path

import yaml
from tests.helpers import FIXTURES, make_glossary, make_term

from glossary_kit.domain.models import Source, TermStatus
from glossary_kit.validate.structural import (
    get_json_schema,
    validate_glossary_path,
    validate_json_schema,
    validate_structure,
)


def _codes(glossary: object) -> set[str]:
    from glossary_kit.domain.models import Glossary

    assert isinstance(glossary, Glossary)
    return {d.code for d in validate_structure(glossary)}


def test_glos_struct_001_passes_with_required_fields() -> None:
    glossary = make_glossary(make_term())
    assert "GLOS-STRUCT-001" not in _codes(glossary)


def test_glos_struct_001_fails_on_empty_id() -> None:
    glossary = make_glossary(make_term(id=""))
    assert "GLOS-STRUCT-001" in _codes(glossary)


def test_glos_struct_002_fails_on_duplicate_id() -> None:
    glossary = make_glossary(
        make_term(id="dup", preferred_label="First"),
        make_term(id="dup", preferred_label="Second"),
    )
    assert "GLOS-STRUCT-002" in _codes(glossary)


def test_glos_struct_003_fails_on_duplicate_label() -> None:
    glossary = make_glossary(
        make_term(id="a", preferred_label="Same label"),
        make_term(id="b", preferred_label="Same label"),
    )
    assert "GLOS-STRUCT-003" in _codes(glossary)


def test_glos_struct_003_fails_on_synonym_matching_label() -> None:
    glossary = make_glossary(
        make_term(preferred_label="Alpha", synonyms=["Alpha"])
    )
    assert "GLOS-STRUCT-003" in _codes(glossary)


def test_glos_rel_001_fails_on_missing_related_term() -> None:
    glossary = make_glossary(make_term(related_terms=["missing-id"]))
    assert "GLOS-REL-001" in _codes(glossary)


def test_glos_rel_001_fails_on_missing_replaces_target() -> None:
    glossary = make_glossary(make_term(replaces="ghost"))
    assert "GLOS-REL-001" in _codes(glossary)


def test_glos_rel_001_fails_on_missing_replaced_by_target() -> None:
    glossary = make_glossary(make_term(replaced_by="ghost"))
    assert "GLOS-REL-001" in _codes(glossary)


def test_glos_rel_002_fails_on_replaces_cycle() -> None:
    glossary = make_glossary(
        make_term(id="a", replaces="b"),
        make_term(id="b", replaces="a"),
    )
    assert "GLOS-REL-002" in _codes(glossary)


def test_glos_gov_001_fails_on_approved_without_steward() -> None:
    glossary = make_glossary(
        make_term(status=TermStatus.APPROVED, steward=None, source_url="https://example.com")
    )
    assert "GLOS-GOV-001" in _codes(glossary)


def test_glos_gov_002_fails_on_approved_without_source() -> None:
    glossary = make_glossary(
        make_term(status=TermStatus.APPROVED, steward="owner", source_url=None, sources=[])
    )
    assert "GLOS-GOV-002" in _codes(glossary)


def test_glos_gov_002_passes_with_source_citation() -> None:
    glossary = make_glossary(
        make_term(
            status=TermStatus.APPROVED,
            steward="owner",
            source_url=None,
            sources=[Source(citation="Internal policy 2024")],
        )
    )
    assert "GLOS-GOV-002" not in _codes(glossary)


def test_validate_json_schema_rejects_missing_metadata(tmp_path: Path) -> None:
    bad = {"terms": []}
    diags = validate_json_schema(bad)
    assert diags
    assert all(d.code == "GLOS-STRUCT-001" for d in diags)


def test_get_json_schema_has_version() -> None:
    schema = get_json_schema()
    assert schema["$id"] == "https://glossary-kit.dev/schema/glossary/1.0.0"


def test_validate_glossary_path_unreadable(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    glossary, diags = validate_glossary_path(missing)
    assert glossary is None
    assert diags[0].code == "INPUT-001"


def test_validate_glossary_path_invalid_yaml(tmp_path: Path) -> None:
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("metadata: [\n", encoding="utf-8")
    glossary, diags = validate_glossary_path(bad_yaml)
    assert glossary is None
    assert diags[0].code == "INPUT-001"


def test_validate_glossary_path_pydantic_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        yaml.dump({"metadata": {"title": "t", "schema_version": "1.0.0"}, "terms": []}),
        encoding="utf-8",
    )
    glossary, diags = validate_glossary_path(bad)
    assert glossary is None
    assert diags[0].code == "INPUT-001"


def test_validate_glossary_path_success(minimal_glossary_path: Path) -> None:
    glossary, diags = validate_glossary_path(minimal_glossary_path)
    assert glossary is not None
    assert not any(d.severity.value == "error" for d in diags)


def test_validate_json_schema_rejects_bad_schema_version() -> None:
    data = yaml.safe_load((FIXTURES / "minimal_glossary.yaml").read_text(encoding="utf-8"))
    data["metadata"]["schema_version"] = 123  # type: ignore[index]
    diags = validate_json_schema(data)
    assert diags
    assert all(d.code == "GLOS-STRUCT-001" for d in diags)


def test_validate_glossary_path_csv_uses_model_dump(
    minimal_glossary_path: Path, tmp_path: Path
) -> None:
    from glossary_kit.ingest.loader import load_glossary

    glossary = load_glossary(minimal_glossary_path)
    csv_path = tmp_path / "glossary.csv"
    csv_path.write_text("id,preferred_label,definition,status,language\n", encoding="utf-8")
    from glossary_kit.exports.csv_export import export_csv

    export_csv(glossary, csv_path, profile="human")
    loaded, _diags = validate_glossary_path(csv_path)
    assert loaded is not None
    assert isinstance(json.loads(json.dumps(loaded.model_dump(mode="json"))), dict)
