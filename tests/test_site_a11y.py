from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

from glossary_kit.exports.site import export_site
from glossary_kit.ingest.loader import load_glossary


class LandmarkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.landmarks: list[tuple[str, dict[str, str | None]]] = []
        self.labels: list[tuple[str, str]] = []
        self.search_controls: list[str] = []
        self.demo_banners: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: v for k, v in attrs if k and v is not None}
        role = attr_map.get("role")
        if role in {"banner", "main", "contentinfo", "navigation", "note"}:
            self.landmarks.append((role, attr_map))
        if tag == "label" and "for" in attr_map:
            self.labels.append((attr_map["for"], ""))
        if tag == "input" and attr_map.get("type") == "search":
            self.search_controls.append(attr_map.get("id", ""))
        if "demo-banner" in attr_map.get("class", ""):
            self._capture_demo = True
        else:
            self._capture_demo = False

    def handle_data(self, data: str) -> None:
        if getattr(self, "_capture_demo", False) and data.strip():
            self.demo_banners.append(data.strip())


def _export_sample_site(tmp_path: Path) -> Path:
    root = Path(__file__).parent.parent
    glossary = load_glossary(root / "examples" / "sample_glossary.yaml")
    out = tmp_path / "site"
    export_site(glossary, out)
    return out


def test_site_has_required_landmarks(tmp_path: Path) -> None:
    site = _export_sample_site(tmp_path)
    parser = LandmarkParser()
    parser.feed((site / "index.html").read_text())
    roles = {role for role, _ in parser.landmarks}
    assert "banner" in roles
    assert "main" in roles
    assert "contentinfo" in roles
    assert "navigation" in roles


def test_site_skip_link_targets_main(tmp_path: Path) -> None:
    site = _export_sample_site(tmp_path)
    html = (site / "index.html").read_text()
    assert 'class="skip-link" href="#main"' in html
    assert 'id="main" role="main"' in html


def test_site_search_input_has_label_and_live_region(tmp_path: Path) -> None:
    site = _export_sample_site(tmp_path)
    parser = LandmarkParser()
    parser.feed((site / "index.html").read_text())
    assert ("search-input", "") in parser.labels
    html = (site / "index.html").read_text()
    assert 'id="search-status" aria-live="polite"' in html
    assert 'aria-controls="search-results search-status"' in html


def test_site_search_index_matches_public_terms(tmp_path: Path) -> None:
    site = _export_sample_site(tmp_path)
    index = json.loads((site / "search-index.json").read_text())
    assert len(index) >= 50
    for entry in index:
        assert {"id", "label", "definition", "url"} <= set(entry.keys())
        assert entry["url"].endswith(".html")


def test_site_headings_have_ids_for_sections(tmp_path: Path) -> None:
    site = _export_sample_site(tmp_path)
    html = (site / "index.html").read_text()
    assert re.search(r'id="heading-[A-Z]"', html)
    assert re.search(r'aria-labelledby="heading-[A-Z]"', html)


def test_site_lists_use_list_role(tmp_path: Path) -> None:
    site = _export_sample_site(tmp_path)
    html = (site / "index.html").read_text()
    assert 'role="list"' in html


def test_site_demo_banner_is_not_colour_only(tmp_path: Path) -> None:
    root = Path(__file__).parent.parent
    glossary = load_glossary(root / "examples" / "sample_glossary.yaml")
    site = tmp_path / "site"
    export_site(glossary, site)
    for term_html in (site / "terms").glob("*.html"):
        parser = LandmarkParser()
        parser.feed(term_html.read_text())
        if parser.demo_banners:
            for text in parser.demo_banners:
                assert len(text) > 10


def test_term_page_definition_list_semantics(minimal_glossary_path: Path, tmp_path: Path) -> None:
    glossary = load_glossary(minimal_glossary_path)
    site = tmp_path / "site"
    export_site(glossary, site)
    term_html = (site / "terms" / "alpha.html").read_text()
    assert "<dl>" in term_html
    assert "<dt>Identifier</dt>" in term_html
    assert "<dd>" in term_html


def test_maturity_report_table_accessibility(sample_glossary_path: Path, tmp_path: Path) -> None:
    from glossary_kit.assess.maturity import assess_maturity, write_maturity_html

    glossary = load_glossary(sample_glossary_path)
    report = assess_maturity(glossary)
    html_path = tmp_path / "maturity.html"
    write_maturity_html(report, html_path)
    html = html_path.read_text()
    assert "<caption>Dimension scores</caption>" in html
    assert "<thead>" in html
    assert "<tbody>" in html
    assert "disclaimer" in html.lower()
