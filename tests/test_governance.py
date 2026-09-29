from __future__ import annotations

from pathlib import Path

from glossary_kit.governance.templates import GOVERNANCE_TEMPLATES, init_governance_templates


def test_init_governance_templates_writes_all_files(tmp_path: Path) -> None:
    out = tmp_path / "gov"
    written = init_governance_templates(out)
    assert len(written) == len(GOVERNANCE_TEMPLATES)
    for path in written:
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "[Organization Name]" in text
        assert "[Glossary Title]" in text


def test_governance_template_names() -> None:
    assert "stewardship_policy.md" in [n.replace(".j2", "") for n in GOVERNANCE_TEMPLATES]
