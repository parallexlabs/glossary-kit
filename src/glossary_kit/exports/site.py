from __future__ import annotations

import json
import shutil
import tempfile
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from glossary_kit.domain.models import Glossary, ReuseStatus, Term
from glossary_kit.exports.slugs import term_slug, validate_slug_safe_ids


class SiteExportError(Exception):
    """Raised when site export cannot complete safely."""


def export_site(glossary: Glossary, output: Path) -> None:
    slug_errors = validate_slug_safe_ids([t.id for t in glossary.terms])
    if slug_errors:
        msg = "; ".join(slug_errors)
        raise SiteExportError(msg)

    template_dir = Path(str(files("glossary_kit.resources.html")))
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["slug"] = term_slug

    public_terms = sorted(glossary.public_terms(), key=lambda t: t.preferred_label.lower())

    search_index = [
        {
            "id": t.id,
            "label": t.preferred_label,
            "definition": t.definition[:200],
            "url": f"terms/{term_slug(t.id)}.html",
        }
        for t in public_terms
    ]

    index_tpl = env.get_template("index.html")
    term_tpl = env.get_template("term.html")
    base_ctx = {
        "title": glossary.metadata.title,
        "description": glossary.metadata.description or "",
        "attribution": glossary.metadata.attribution or "",
    }

    letters: dict[str, list[Term]] = {}
    for term in public_terms:
        letter = term.preferred_label[0].upper() if term.preferred_label else "#"
        letters.setdefault(letter, []).append(term)

    index_html = index_tpl.render(
        **base_ctx,
        terms=public_terms,
        letters=sorted(letters.items()),
    )

    label_by_id = {t.id: t.preferred_label for t in public_terms}
    term_pages: dict[str, str] = {}
    for term in public_terms:
        demo_flag = _demo_banner(term)
        related_links = [
            (rel, label_by_id[rel], term_slug(rel))
            for rel in term.related_terms
            if rel in label_by_id
        ]
        html = term_tpl.render(
            **base_ctx,
            term=term,
            demo_banner=demo_flag,
            related_links=related_links,
        )
        term_pages[f"terms/{term_slug(term.id)}.html"] = html

    manifest = ["index.html", "search-index.json", *sorted(term_pages.keys())]

    with tempfile.TemporaryDirectory(prefix="glossary-kit-site-") as tmp:
        staging = Path(tmp)
        terms_dir = staging / "terms"
        terms_dir.mkdir(parents=True, exist_ok=True)
        (staging / "index.html").write_text(index_html, encoding="utf-8")
        (staging / "search-index.json").write_text(
            json.dumps(search_index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for rel_path, html in term_pages.items():
            (staging / rel_path).write_text(html, encoding="utf-8")
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        output.mkdir(parents=True, exist_ok=True)
        _remove_stale_site_files(output, manifest)
        for rel_path in manifest:
            src = staging / rel_path
            dest = output / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        shutil.copy2(staging / "manifest.json", output / "manifest.json")


def _remove_stale_site_files(output: Path, manifest: list[str]) -> None:
    manifest_set = set(manifest) | {"manifest.json"}
    if (output / "manifest.json").exists():
        try:
            previous = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            if isinstance(previous, list):
                for rel_path in previous:
                    stale = output / rel_path
                    if stale.is_file() and rel_path not in manifest_set:
                        stale.unlink()
        except (OSError, json.JSONDecodeError):
            pass

    terms_dir = output / "terms"
    if terms_dir.is_dir():
        for html_file in terms_dir.glob("*.html"):
            rel = f"terms/{html_file.name}"
            if rel not in manifest_set:
                html_file.unlink()


def _demo_banner(term: Term) -> str | None:
    if term.demo:
        return "Demo term — licence not verified for text reuse"
    if term.reuse_status == ReuseStatus.LICENCE_NOT_VERIFIED:
        return "Licence not verified — demo only"
    if term.reuse_status == ReuseStatus.EXCLUDED:
        return "Excluded from reuse — demo placeholder"
    return None
