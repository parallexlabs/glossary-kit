from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

GOVERNANCE_TEMPLATES = (
    "stewardship_policy.md.j2",
    "raci_matrix.md.j2",
    "change_request.md.j2",
    "decision_log.md.j2",
)


def init_governance_templates(output: Path) -> list[Path]:
    template_dir = Path(str(files("glossary_kit.resources.templates") / "governance"))
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=(), default=False),
    )
    output.mkdir(parents=True, exist_ok=True)
    ctx = {
        "organization": "[Organization Name]",
        "glossary_title": "[Glossary Title]",
        "effective_date": "[YYYY-MM-DD]",
    }
    written: list[Path] = []
    for name in GOVERNANCE_TEMPLATES:
        tpl = env.get_template(name)
        out_name = name.replace(".j2", "")
        out_path = output / out_name
        out_path.write_text(tpl.render(**ctx), encoding="utf-8")
        written.append(out_path)
    return written
