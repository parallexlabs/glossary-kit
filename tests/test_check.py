from __future__ import annotations

from pathlib import Path

from tests.helpers import FIXTURES, make_glossary, make_term

from glossary_kit.check.dictionary import check_dictionary_csv, check_frictionless_schema
from glossary_kit.domain.models import DictionaryBinding
from glossary_kit.ingest.loader import load_glossary


def test_check_dictionary_passes_when_headers_match(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(
            id="alpha",
            preferred_label="Alpha",
            dictionary_bindings=[DictionaryBinding(header="col_a", term_id="alpha")],
        ),
        make_term(
            id="beta",
            preferred_label="Beta",
            dictionary_bindings=[DictionaryBinding(header="col_b", term_id="beta")],
        ),
    )
    csv_path = tmp_path / "dictionary_clean.csv"
    csv_path.write_text("col_a,col_b\n1,2\n", encoding="utf-8")
    diags = check_dictionary_csv(csv_path, glossary)
    assert not any(d.severity.value == "error" for d in diags)


def test_check_dictionary_unmapped_header(
    minimal_glossary_path: Path, dictionary_csv_path: Path
) -> None:
    glossary = load_glossary(minimal_glossary_path)
    diagnostics = check_dictionary_csv(dictionary_csv_path, glossary)
    errors = [d for d in diagnostics if d.severity.value == "error"]
    assert any("unknown_col" in d.path for d in errors)
    assert any(d.code == "DICT-HEAD-001" for d in errors)


def test_check_dictionary_fuzzy_suggestion(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(
            id="alpha",
            preferred_label="Alpha term",
            dictionary_bindings=[DictionaryBinding(header="col_a", term_id="alpha")],
        )
    )
    csv_path = tmp_path / "dict.csv"
    csv_path.write_text("col_a,alpha_term\n1,2\n", encoding="utf-8")
    diags = check_dictionary_csv(csv_path, glossary, fuzzy=True)
    assert any(d.severity.value == "suggestion" for d in diags)
    assert any("did you mean" in d.message for d in diags)


def test_check_dictionary_missing_binding_header() -> None:
    glossary = make_glossary(
        make_term(
            dictionary_bindings=[DictionaryBinding(header="missing_header", term_id="term-1")]
        )
    )
    csv_path = FIXTURES / "dictionary.csv"
    diags = check_dictionary_csv(csv_path, glossary)
    assert any(d.code == "DICT-BIND-001" for d in diags)


def test_check_dictionary_unreadable_csv(tmp_path: Path) -> None:
    glossary = make_glossary()
    missing = tmp_path / "nope.csv"
    diags = check_dictionary_csv(missing, glossary)
    assert len(diags) == 1
    assert diags[0].code == "DICT-HEAD-001"


def test_check_frictionless_unmapped_field(
    minimal_glossary_path: Path, table_schema_path: Path
) -> None:
    glossary = load_glossary(minimal_glossary_path)
    diagnostics = check_frictionless_schema(table_schema_path, glossary)
    assert any(d.code == "DICT-FRIC-001" for d in diagnostics)


def test_check_frictionless_passes_with_mapped_fields(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(
            id="alpha",
            preferred_label="Alpha",
            dictionary_bindings=[DictionaryBinding(header="col_a", term_id="alpha")],
        )
    )
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        "fields:\n  - name: col_a\n    type: string\n  - name: Alpha\n    type: string\n",
        encoding="utf-8",
    )
    diags = check_frictionless_schema(schema, glossary)
    assert not any(d.severity.value == "error" for d in diags)


def test_check_frictionless_invalid_yaml(tmp_path: Path) -> None:
    glossary = make_glossary()
    bad = tmp_path / "bad.yaml"
    bad.write_text("fields: [", encoding="utf-8")
    diags = check_frictionless_schema(bad, glossary)
    assert diags[0].code == "DICT-FRIC-001"


def test_check_frictionless_non_mapping_root(tmp_path: Path) -> None:
    glossary = make_glossary()
    bad = tmp_path / "list.yaml"
    bad.write_text("- not-a-map\n", encoding="utf-8")
    diags = check_frictionless_schema(bad, glossary)
    assert "mapping" in diags[0].message


def test_check_frictionless_missing_fields_array(tmp_path: Path) -> None:
    glossary = make_glossary()
    bad = tmp_path / "nofields.yaml"
    bad.write_text("fields: not-a-list\n", encoding="utf-8")
    diags = check_frictionless_schema(bad, glossary)
    assert diags[0].path == "fields"
