from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

import rdflib
from tests.helpers import make_glossary, make_term

from glossary_kit.assess.maturity import assess_maturity, write_maturity_html, write_maturity_json
from glossary_kit.domain.models import Publication, PublicationVisibility, ReuseStatus
from glossary_kit.exports import export_csv, export_jsonld, export_site, export_skos_turtle
from glossary_kit.ingest.loader import load_glossary, load_glossary_csv


def test_export_skos_deterministic(minimal_glossary_path: Path, tmp_path: Path) -> None:
    glossary = load_glossary(minimal_glossary_path)
    out1 = tmp_path / "a.ttl"
    out2 = tmp_path / "b.ttl"
    export_skos_turtle(glossary, out1)
    export_skos_turtle(glossary, out2)
    assert out1.read_text() == out2.read_text()
    graph = rdflib.Graph()
    graph.parse(data=out1.read_text(), format="turtle")
    assert len(graph) > 0


def test_export_skos_includes_synonyms_and_relations(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(
            id="alpha",
            preferred_label="Alpha",
            synonyms=["Alias"],
            related_terms=["beta"],
            source_url="https://example.com/a",
        ),
        make_term(id="beta", preferred_label="Beta", replaces="alpha"),
    )
    out = tmp_path / "g.ttl"
    export_skos_turtle(glossary, out)
    text = out.read_text()
    assert "altLabel" in text or "skos:altLabel" in text
    graph = rdflib.Graph()
    graph.parse(data=text, format="turtle")
    assert len(graph) > 0


def test_export_jsonld_deterministic(minimal_glossary_path: Path, tmp_path: Path) -> None:
    glossary = load_glossary(minimal_glossary_path)
    out1 = tmp_path / "a.jsonld"
    out2 = tmp_path / "b.jsonld"
    export_jsonld(glossary, out1)
    export_jsonld(glossary, out2)
    assert out1.read_text() == out2.read_text()
    data = json.loads(out1.read_text())
    assert "@context" in data
    assert "@graph" in data


def test_export_jsonld_context_and_graph_shape(minimal_glossary_path: Path, tmp_path: Path) -> None:
    glossary = load_glossary(minimal_glossary_path)
    out = tmp_path / "g.jsonld"
    export_jsonld(glossary, out)
    doc = json.loads(out.read_text())
    ctx = doc["@context"]
    assert ctx["@vocab"] == "http://www.w3.org/2004/02/skos/core#"
    assert ctx["gloss"] == "https://glossary-kit.dev/scheme/"
    assert "prefLabel" not in ctx or "@language" not in ctx.get("prefLabel", {})
    concepts = [n for n in doc["@graph"] if n.get("@type") == "Concept"]
    assert concepts


def test_export_jsonld_includes_synonyms_and_related(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(id="alpha", synonyms=["Alias"], related_terms=["beta"]),
        make_term(id="beta", preferred_label="Beta"),
    )
    out = tmp_path / "g.jsonld"
    export_jsonld(glossary, out)
    doc = json.loads(out.read_text())
    alpha = next(n for n in doc["@graph"] if n["@id"] == "gloss:alpha")
    assert alpha["altLabel"] == [{"@value": "Alias", "@language": "en"}]
    assert alpha["related"] == ["gloss:beta"]


def test_export_csv_human(minimal_glossary_path: Path, tmp_path: Path) -> None:
    glossary = load_glossary(minimal_glossary_path)
    out = tmp_path / "out.csv"
    export_csv(glossary, out, profile="human")
    text = out.read_text()
    assert "alpha" in text
    assert "preferred_label" in text


def test_export_csv_roundtrip(minimal_glossary_path: Path, tmp_path: Path) -> None:
    glossary = load_glossary(minimal_glossary_path)
    out = tmp_path / "roundtrip.csv"
    export_csv(glossary, out, profile="roundtrip")
    reloaded = load_glossary_csv(out)
    assert {t.id for t in reloaded.terms} == {t.id for t in glossary.terms}
    for original, imported in zip(
        sorted(glossary.terms, key=lambda t: t.id),
        sorted(reloaded.terms, key=lambda t: t.id),
        strict=True,
    ):
        assert original.preferred_label == imported.preferred_label
        assert original.definition == imported.definition


def test_export_csv_empty_terms_writes_blank_file(tmp_path: Path) -> None:
    from glossary_kit.domain.models import Glossary, GlossaryMetadata

    glossary = Glossary.model_construct(
        metadata=GlossaryMetadata(title="t", schema_version="1.0.0"),
        terms=[],
    )
    out = tmp_path / "empty.csv"
    export_csv(glossary, out, profile="human")
    assert out.read_text() == ""


def test_export_site_structure(minimal_glossary_path: Path, tmp_path: Path) -> None:
    glossary = load_glossary(minimal_glossary_path)
    out = tmp_path / "site"
    export_site(glossary, out)
    assert (out / "index.html").exists()
    assert (out / "search-index.json").exists()
    index = (out / "index.html").read_text()
    assert "skip-link" in index
    assert 'aria-live="polite"' in index
    assert (out / "terms" / "alpha.html").exists()


def test_export_site_search_index_content(minimal_glossary_path: Path, tmp_path: Path) -> None:
    glossary = load_glossary(minimal_glossary_path)
    out = tmp_path / "site"
    export_site(glossary, out)
    index = json.loads((out / "search-index.json").read_text())
    assert len(index) == len(glossary.public_terms())
    assert index[0]["label"]
    assert index[0]["url"].startswith("terms/")


def test_export_site_demo_banners(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(id="demo", demo=True),
        make_term(id="unverified", reuse_status=ReuseStatus.LICENCE_NOT_VERIFIED),
        make_term(id="excluded", reuse_status=ReuseStatus.EXCLUDED),
    )
    out = tmp_path / "site"
    export_site(glossary, out)
    demo_html = (out / "terms" / "demo.html").read_text()
    assert "Licence not verified" in demo_html or "Demo term" in demo_html
    unverified_html = (out / "terms" / "unverified.html").read_text()
    assert "Licence not verified" in unverified_html


def test_export_site_hides_internal_terms(tmp_path: Path) -> None:
    glossary = make_glossary(
        make_term(id="public"),
        make_term(
            id="internal",
            preferred_label="Internal only",
            publication=Publication(visibility=PublicationVisibility.INTERNAL),
        ),
    )
    out = tmp_path / "site"
    export_site(glossary, out)
    assert (out / "terms" / "public.html").exists()
    assert not (out / "terms" / "internal.html").exists()
    index = json.loads((out / "search-index.json").read_text())
    assert all(entry["id"] != "internal" for entry in index)


class _HeadingCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.headings: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3"}:
            self._current = tag

    def handle_data(self, data: str) -> None:
        if hasattr(self, "_current"):
            self.headings.append((self._current, data.strip()))
            del self._current


def test_export_site_heading_hierarchy(minimal_glossary_path: Path, tmp_path: Path) -> None:
    glossary = load_glossary(minimal_glossary_path)
    out = tmp_path / "site"
    export_site(glossary, out)
    parser = _HeadingCollector()
    parser.feed((out / "index.html").read_text())
    tags = [tag for tag, _ in parser.headings]
    assert "h1" in tags
    assert "h2" in tags


def test_maturity_html_table_semantics(sample_glossary_path: Path, tmp_path: Path) -> None:
    glossary = load_glossary(sample_glossary_path)
    report = assess_maturity(glossary)
    html_path = tmp_path / "maturity.html"
    json_path = tmp_path / "maturity.json"
    write_maturity_html(report, html_path)
    write_maturity_json(report, json_path)
    html = html_path.read_text()
    assert "<caption>Dimension scores</caption>" in html
    assert "<thead>" in html
    assert "<th>Dimension</th>" in html
    saved = json.loads(json_path.read_text())
    assert saved["total_score"] == report["total_score"]
    assert saved["disclaimer"] == report["disclaimer"]
