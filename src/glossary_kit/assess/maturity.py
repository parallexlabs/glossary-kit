from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from glossary_kit.domain.models import Glossary, TermStatus


def load_rubric() -> dict[str, Any]:
    path = Path(str(files("glossary_kit.resources.rubric") / "maturity.yaml"))
    return cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def assess_maturity(glossary: Glossary) -> dict[str, Any]:
    rubric = load_rubric()
    dimensions = rubric.get("dimensions", [])
    scores: list[dict[str, Any]] = []
    gaps: list[str] = []

    for dim in dimensions:
        dim_id = dim["id"]
        score, evidence, dim_gaps = _score_dimension(glossary, dim)
        scores.append(
            {
                "id": dim_id,
                "name": dim["name"],
                "score": score,
                "max_score": dim.get("max_score", 4),
                "evidence": evidence,
                "guidance": dim.get("guidance", ""),
            }
        )
        gaps.extend(dim_gaps)

    total = sum(s["score"] for s in scores)
    max_total = sum(s["max_score"] for s in scores)
    return {
        "glossary_title": glossary.metadata.title,
        "schema_version": glossary.metadata.schema_version,
        "dimensions": scores,
        "total_score": total,
        "max_score": max_total,
        "percentage": round(100 * total / max_total, 1) if max_total else 0,
        "gaps": gaps,
        "disclaimer": (
            "This report reflects glossary metadata evidence only. "
            "It does not certify organizational compliance."
        ),
    }


def _score_dimension(glossary: Glossary, dim: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    dim_id = dim["id"]
    evidence: list[str] = []
    gaps: list[str] = []
    score = 0

    if dim_id == "definitions":
        approved = [t for t in glossary.terms if t.status == TermStatus.APPROVED]
        with_def = [t for t in approved if t.definition.strip()]
        if with_def:
            score += 2
            evidence.append(f"{len(with_def)}/{len(approved)} approved terms have definitions")
        else:
            gaps.append("No approved terms with definitions")
        non_empty = len([t for t in glossary.terms if len(t.definition) > 20])
        if non_empty > len(glossary.terms) * 0.8:
            score += 2
            evidence.append("Most definitions exceed minimal length")
        else:
            gaps.append("Many definitions are very short")

    elif dim_id == "stewardship":
        stewards = len([t for t in glossary.terms if t.steward])
        if stewards:
            score += min(4, stewards // max(1, len(glossary.terms) // 4))
            evidence.append(f"{stewards} terms have assigned stewards")
        else:
            gaps.append("No stewards assigned")

    elif dim_id == "provenance":
        with_source = len([t for t in glossary.terms if t.source_url])
        if with_source > len(glossary.terms) * 0.5:
            score += 3
            evidence.append(f"{with_source} terms include source_url")
        else:
            gaps.append("Many terms lack source_url")
        with_licence = len([t for t in glossary.terms if t.licence])
        if with_licence:
            score += 1
            evidence.append(f"{with_licence} terms document licence")

    elif dim_id == "relationships":
        with_rel = len([t for t in glossary.terms if t.related_terms])
        if with_rel:
            score += 2
            evidence.append(f"{with_rel} terms have related_terms")
        domains = len({t.domain for t in glossary.terms if t.domain})
        if domains >= 3:
            score += 2
            evidence.append(f"{domains} distinct domains represented")
        else:
            gaps.append("Limited domain coverage")

    elif dim_id == "lifecycle":
        statuses = {t.status for t in glossary.terms}
        if TermStatus.APPROVED in statuses:
            score += 2
            evidence.append("Approved status used")
        if TermStatus.DEPRECATED in statuses or any(t.replaced_by for t in glossary.terms):
            score += 2
            evidence.append("Deprecation or replacement modeled")
        else:
            gaps.append("No deprecated terms or replacement links")

    elif dim_id == "publication":
        if glossary.metadata.attribution:
            score += 2
            evidence.append("Glossary-level attribution present")
        public = len(glossary.public_terms())
        score += min(2, public // max(1, len(glossary.terms) // 2))
        evidence.append(f"{public} terms marked public")

    return min(score, dim.get("max_score", 4)), evidence, gaps


def write_maturity_json(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_maturity_html(report: dict[str, Any], output: Path) -> None:
    template_dir = Path(str(files("glossary_kit.resources.html")))
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("maturity.html")
    html = tpl.render(report=report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
