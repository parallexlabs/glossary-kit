from __future__ import annotations

import json
import re
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from glossary_kit.domain.models import Glossary, ReuseStatus, Term


def export_site(glossary: Glossary, output: Path) -> None:
    template_dir = Path(str(files("glossary_kit.resources.html")))
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["slug"] = _slug

    public_terms = sorted(glossary.public_terms(), key=lambda t: t.preferred_label.lower())
    output.mkdir(parents=True, exist_ok=True)
    terms_dir = output / "terms"
    terms_dir.mkdir(exist_ok=True)

    search_index = [
        {
            "id": t.id,
            "label": t.preferred_label,
            "definition": t.definition[:200],
            "url": f"terms/{_slug(t.id)}.html",
        }
        for t in public_terms
    ]
    (output / "search-index.json").write_text(
        json.dumps(search_index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

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
    (output / "index.html").write_text(index_html, encoding="utf-8")

    label_by_id = {t.id: t.preferred_label for t in public_terms}
    for term in public_terms:
        demo_flag = _demo_banner(term)
        related_links = [
            (rel, label_by_id[rel], _slug(rel))
            for rel in term.related_terms
            if rel in label_by_id
        ]
        html = term_tpl.render(
            **base_ctx,
            term=term,
            demo_banner=demo_flag,
            related_links=related_links,
        )
        (terms_dir / f"{_slug(term.id)}.html").write_text(html, encoding="utf-8")


def _slug(term_id: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", term_id.lower())


def _demo_banner(term: Term) -> str | None:
    if term.demo:
        return "Demo term — licence not verified for text reuse"
    if term.reuse_status == ReuseStatus.LICENCE_NOT_VERIFIED:
        return "Licence not verified — demo only"
    if term.reuse_status == ReuseStatus.EXCLUDED:
        return "Excluded from reuse — demo placeholder"
    return None
