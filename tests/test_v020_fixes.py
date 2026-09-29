from __future__ import annotations

import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest
import rdflib
import yaml
from tests.helpers import make_glossary, make_term

from glossary_kit.check.dictionary import (
    FRICTIONLESS_LOGICAL_TYPES,
    check_frictionless_schema,
    frictionless_type_matches,
)
from glossary_kit.domain.models import (
    DictionaryBinding,
    Publication,
    PublicationVisibility,
    Source,
    Term,
)
from glossary_kit.domain.urls import is_safe_http_url
from glossary_kit.exports.rdf import export_jsonld, export_skos_turtle
from glossary_kit.exports.site import SiteExportError, export_site
from glossary_kit.exports.slugs import term_slug, validate_slug_safe_ids
from glossary_kit.lint.engine import lint_glossary
from glossary_kit.validate.structural import (
    get_json_schema,
    validate_glossary_path,
    validate_structure,
)


class _HtmlAuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.headings: list[tuple[str, str]] = []
        self.labels: list[tuple[str, str]] = []
        self.search_forms: list[dict[str, str]] = []
        self._current_heading: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs if k}
        if "id" in attr_map:
            self.ids.append(attr_map["id"])
        if tag in {"h1", "h2", "h3"}:
            self._current_heading = tag
        if tag == "label" and "for" in attr_map:
            self.labels.append((attr_map["for"], ""))
        if tag == "form" and attr_map.get("role") == "search":
            self.search_forms.append(attr_map)

    def handle_data(self, data: str) -> None:
        if self._current_heading and data.strip():
            self.headings.append((self._current_heading, data.strip()))
            self._current_heading = None


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "glossary_kit.cli.main", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_jsonld_emits_per_term_language_tags(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(
            id="bonjour",
            preferred_label="Bonjour",
            definition="Salutation en français.",
            language="fr",
            synonyms=["Salut"],
        )
    )
    out = tmp_path / "g.jsonld"
    export_jsonld(glossary, out)
    doc = json.loads(out.read_text())
    concept = next(n for n in doc["@graph"] if n["@id"] == "gloss:bonjour")
    assert concept["prefLabel"] == {"@value": "Bonjour", "@language": "fr"}
    assert concept["definition"]["@language"] == "fr"
    assert concept["altLabel"][0]["@language"] == "fr"


def test_jsonld_expansion_preserves_french_literals_with_rdflib(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(
            id="bonjour",
            preferred_label="Bonjour",
            definition="Salutation en français.",
            language="fr",
        )
    )
    out = tmp_path / "g.jsonld"
    export_jsonld(glossary, out)
    graph = rdflib.Graph()
    graph.parse(data=out.read_text(), format="json-ld")
    literals = [o for o in graph.objects() if isinstance(o, rdflib.Literal)]
    fr_literals = [lit for lit in literals if lit.language == "fr"]
    assert fr_literals
    assert any("Bonjour" in str(lit) for lit in fr_literals)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com/path", True),
        ("http://example.org", True),
        ("javascript:alert(1)", False),
        ("data:text/html,hi", False),
        ("vbscript:msgbox(1)", False),
        ("//evil.example/xss", False),
        ("not-a-url", False),
        ("https:", False),
    ],
)
def test_is_safe_http_url_rejects_dangerous_schemes(url: str, expected: bool) -> None:
    assert is_safe_http_url(url) is expected


def test_term_model_rejects_javascript_source_url() -> None:
    with pytest.raises(Exception, match="URL must be an absolute"):
        make_term(source_url="javascript:alert(1)")


def test_term_model_rejects_protocol_relative_licence_url() -> None:
    with pytest.raises(Exception, match="URL must be an absolute"):
        make_term(licence_url="//evil.example/licence")


def test_source_model_rejects_data_url() -> None:
    with pytest.raises(Exception, match="URL must be an absolute"):
        Term(
            id="x",
            preferred_label="X",
            definition="Definition text.",
            status="draft",
            language="en",
            sources=[Source(url="data:text/plain,secret")],
        )


def test_validate_glossary_path_reports_pydantic_json_paths(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        yaml.dump(
            {
                "metadata": {"title": "t", "schema_version": "1.0.0"},
                "terms": [],
            }
        ),
        encoding="utf-8",
    )
    glossary, diags = validate_glossary_path(bad)
    assert glossary is None
    assert diags[0].code == "GLOS-STRUCT-001"
    assert "terms" in diags[0].path


def test_cli_validate_reports_struct_path_for_empty_terms(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        """metadata:
  title: t
  schema_version: '1.0.0'
terms: []
""",
        encoding="utf-8",
    )
    result = _run_cli("validate", str(bad))
    assert result.returncode == 1
    assert "terms" in result.stdout + result.stderr


def test_cli_validate_unsafe_url_reports_path(tmp_path: Path) -> None:
    bad = tmp_path / "unsafe.yaml"
    bad.write_text(
        """metadata:
  title: t
  schema_version: '1.0.0'
terms:
  - id: alpha
    preferred_label: Alpha
    definition: A term.
    status: draft
    language: en
    source_url: javascript:alert(1)
""",
        encoding="utf-8",
    )
    result = _run_cli("validate", str(bad))
    assert result.returncode == 1
    output = result.stdout + result.stderr
    assert "source_url" in output


def test_frictionless_reports_malformed_field_index(tmp_path: Path) -> None:
    glossary = make_glossary(make_term(id="alpha", preferred_label="Alpha"))
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        "fields:\n  - not-a-map\n  - name: Alpha\n    type: string\n",
        encoding="utf-8",
    )
    diags = check_frictionless_schema(schema, glossary)
    assert any(d.code == "DICT-FRIC-002" and d.path == "fields[0]" for d in diags)


def test_frictionless_reports_unsupported_logical_type(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(
            id="alpha",
            preferred_label="Alpha",
            dictionary_bindings=[DictionaryBinding(header="col_a", term_id="alpha")],
        )
    )
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        "fields:\n  - name: col_a\n    type: geopoint\n",
        encoding="utf-8",
    )
    diags = check_frictionless_schema(schema, glossary)
    assert any(d.path == "fields[0].type" and d.code == "DICT-FRIC-002" for d in diags)


@pytest.mark.parametrize(
    ("value", "logical_type", "expected"),
    [
        ("hello", "string", True),
        (42, "integer", True),
        (3.14, "number", True),
        (True, "boolean", True),
        ("2024-01-15", "date", True),
        ("2024-01-15T10:00:00Z", "datetime", True),
        ("2024-01-15", "integer", False),
        ("not-a-date", "date", False),
    ],
)
def test_frictionless_logical_type_matches(
    value: object, logical_type: str, expected: bool
) -> None:
    assert logical_type in FRICTIONLESS_LOGICAL_TYPES
    assert frictionless_type_matches(value, logical_type) is expected


def test_dictionary_binding_unknown_term_id_fails_validation() -> None:
    glossary = make_glossary(
        make_term(
            id="alpha",
            dictionary_bindings=[DictionaryBinding(header="col_a", term_id="ghost")],
        )
    )
    codes = {d.code for d in validate_structure(glossary)}
    assert "DICT-BIND-002" in codes


def test_dictionary_binding_duplicate_header_fails_validation() -> None:
    glossary = make_glossary(
        make_term(
            id="alpha",
            dictionary_bindings=[DictionaryBinding(header="shared", term_id="alpha")],
        ),
        make_term(
            id="beta",
            preferred_label="Beta",
            dictionary_bindings=[DictionaryBinding(header="shared", term_id="beta")],
        ),
    )
    codes = {d.code for d in validate_structure(glossary)}
    assert "DICT-BIND-003" in codes


def test_slug_collision_detected() -> None:
    messages = validate_slug_safe_ids(["a_b", "a-b"])
    assert messages
    assert any("collides" in message for message in messages)


def test_export_site_fails_on_slug_collision(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(id="a_b", preferred_label="A underscore B"),
        make_term(id="a-b", preferred_label="A hyphen B"),
    )
    with pytest.raises(SiteExportError, match="collides"):
        export_site(glossary, tmp_path / "site")


def test_export_site_removes_stale_term_pages(tmp_path: Path) -> None:
    glossary = make_glossary(make_term(id="alpha", preferred_label="Alpha"))
    out = tmp_path / "site"
    export_site(glossary, out)
    stale = out / "terms" / "removed.html"
    stale.write_text("<html>stale</html>", encoding="utf-8")
    export_site(glossary, out)
    assert not stale.exists()


def test_skos_omits_internal_related_targets(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(id="public", related_terms=["internal"]),
        make_term(
            id="internal",
            preferred_label="Internal",
            publication=Publication(visibility=PublicationVisibility.INTERNAL),
        ),
    )
    out = tmp_path / "g.ttl"
    export_skos_turtle(glossary, out)
    text = out.read_text()
    assert "internal" not in text or "gloss:internal" not in text


def test_skos_exports_gloss_replaces_and_replaced_by(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(id="old", preferred_label="Old", status="deprecated", replaced_by="new"),
        make_term(id="new", preferred_label="New", replaces="old"),
    )
    out = tmp_path / "g.ttl"
    export_skos_turtle(glossary, out)
    text = out.read_text()
    assert "gloss:replaces" in text
    assert "gloss:replacedBy" in text
    assert "changeNote" not in text


def test_jsonld_exports_gloss_replaces_properties(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(id="old", preferred_label="Old", status="deprecated", replaced_by="new"),
        make_term(id="new", preferred_label="New", replaces="old"),
    )
    out = tmp_path / "g.jsonld"
    export_jsonld(glossary, out)
    doc = json.loads(out.read_text())
    new_node = next(n for n in doc["@graph"] if n["@id"] == "gloss:new")
    old_node = next(n for n in doc["@graph"] if n["@id"] == "gloss:old")
    assert new_node["replaces"] == "gloss:old"
    assert old_node["replacedBy"] == "gloss:new"


def test_term_pages_have_single_h1_with_term_label(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(id="alpha", preferred_label="Alpha label"),
        make_term(id="beta", preferred_label="Beta label"),
    )
    out = tmp_path / "site"
    export_site(glossary, out)
    for html_file in (out / "terms").glob("*.html"):
        parser = _HtmlAuditParser()
        parser.feed(html_file.read_text())
        h1s = [text for tag, text in parser.headings if tag == "h1"]
        assert len(h1s) == 1
        assert h1s[0] in {"Alpha label", "Beta label"}


def test_index_search_form_is_inside_main(tmp_path: Path) -> None:
    glossary = make_glossary(make_term(id="alpha", preferred_label="Alpha"))
    out = tmp_path / "site"
    export_site(glossary, out)
    html = (out / "index.html").read_text()
    main_start = html.index('<main id="main"')
    main_end = html.index("</main>", main_start)
    search_form = html.index('role="search"', main_start)
    assert main_start < search_form < main_end


def test_site_pages_have_unique_ids_and_accessible_search_label(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(id="alpha", preferred_label="Alpha"),
        make_term(id="beta", preferred_label="Beta"),
    )
    out = tmp_path / "site"
    export_site(glossary, out)
    for page in [out / "index.html", *(out / "terms").glob("*.html")]:
        parser = _HtmlAuditParser()
        parser.feed(page.read_text())
        assert len(parser.ids) == len(set(parser.ids))
        if page.name == "index.html":
            assert ("search-input", "") in parser.labels
            assert parser.search_forms


def test_site_css_includes_focus_visible_and_contrast_tokens(tmp_path: Path) -> None:
    glossary = make_glossary(make_term())
    out = tmp_path / "site"
    export_site(glossary, out)
    html = (out / "index.html").read_text()
    assert ":focus-visible" in html
    assert "--focus:" in html
    assert "--text:" in html


def test_json_schema_nested_objects_forbid_additional_properties() -> None:
    schema = get_json_schema()
    source_item = schema["$defs"]["term"]["properties"]["sources"]["items"]
    assert source_item["additionalProperties"] is False
    binding_item = schema["$defs"]["term"]["properties"]["dictionary_bindings"]["items"]
    assert binding_item["additionalProperties"] is False
    assert schema["$defs"]["term"]["properties"]["definition"]["minLength"] == 1


def test_json_schema_rejects_empty_definition() -> None:
    from glossary_kit.validate.structural import validate_json_schema

    data = {
        "metadata": {"title": "t", "schema_version": "1.0.0"},
        "terms": [
            {
                "id": "alpha",
                "preferred_label": "Alpha",
                "definition": "",
                "status": "draft",
                "language": "en",
            }
        ],
    }
    diags = validate_json_schema(data)
    assert diags


def test_glos_lex_001_requires_parenthetical_expansion() -> None:
    glossary = make_glossary(
        make_term(abbreviation="API", definition="An API exposes programmatic access.")
    )
    assert "GLOS-LEX-001" in {d.code for d in lint_glossary(glossary)}


def test_glos_lex_001_passes_with_parenthetical_expansion() -> None:
    glossary = make_glossary(
        make_term(
            abbreviation="API",
            definition="Application Programming Interface (API) exposes programmatic access.",
        )
    )
    assert "GLOS-LEX-001" not in {d.code for d in lint_glossary(glossary)}


def test_glos_def_003_plural_only_in_strict_profile() -> None:
    glossary = make_glossary(make_term(preferred_label="Records"))
    assert "GLOS-DEF-003" not in {d.code for d in lint_glossary(glossary, profile="standard")}
    assert "GLOS-DEF-003" in {d.code for d in lint_glossary(glossary, profile="strict")}


def test_public_term_cannot_reference_internal_related_term() -> None:
    glossary = make_glossary(
        make_term(id="public", related_terms=["internal"]),
        make_term(
            id="internal",
            preferred_label="Internal",
            publication=Publication(visibility=PublicationVisibility.INTERNAL),
        ),
    )
    assert "GLOS-REL-003" in {d.code for d in validate_structure(glossary)}


def test_term_slug_matches_site_output() -> None:
    assert term_slug("a_b") == "a-b"
    assert term_slug("Alpha-Term") == "alpha-term"
