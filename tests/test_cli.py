from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "glossary_kit.cli.main", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_version() -> None:
    result = _run_cli("--version")
    assert result.returncode == 0
    assert "glossary-kit" in result.stdout or "glossary-kit" in result.stderr


def test_cli_validate_success(minimal_glossary_path: Path) -> None:
    result = _run_cli("validate", str(minimal_glossary_path))
    assert result.returncode == 0


def test_cli_validate_failure_exit_code(minimal_glossary_path: Path, tmp_path: Path) -> None:
    import yaml

    data = yaml.safe_load(minimal_glossary_path.read_text(encoding="utf-8"))
    data["terms"].append(
        {
            "id": "alpha",
            "preferred_label": "Duplicate id",
            "definition": "Second alpha",
            "status": "draft",
            "language": "en",
        }
    )
    bad = tmp_path / "dup.yaml"
    bad.write_text(yaml.dump(data), encoding="utf-8")
    result = _run_cli("validate", str(bad))
    assert result.returncode == 1


def test_cli_validate_unreadable_exit_code(tmp_path: Path) -> None:
    result = _run_cli("validate", str(tmp_path / "missing.yaml"))
    assert result.returncode == 3


def test_cli_lint_json(minimal_glossary_path: Path) -> None:
    result = _run_cli("lint", str(minimal_glossary_path), "--format", "json")
    assert result.returncode in (0, 1)
    assert "[" in (result.stdout or result.stderr)


def test_cli_lint_sarif_on_failure(tmp_path: Path) -> None:
    bad = tmp_path / "lint.yaml"
    bad.write_text(
        """metadata:
  title: t
  schema_version: '1.0.0'
terms:
  - id: x
    preferred_label: Widgets
    definition: '   '
    status: draft
    language: en
""",
        encoding="utf-8",
    )
    result = _run_cli("lint", str(bad), "--format", "sarif")
    assert result.returncode == 1
    assert '"version": "2.1.0"' in result.stdout


def test_cli_lint_unknown_profile(minimal_glossary_path: Path) -> None:
    result = _run_cli("lint", str(minimal_glossary_path), "--profile", "invalid")
    assert result.returncode == 2


def test_cli_rules_list() -> None:
    result = _run_cli("rules", "list")
    assert result.returncode == 0
    assert "GLOS-DEF-001" in result.stdout


def test_cli_rules_explain_known() -> None:
    result = _run_cli("rules", "explain", "GLOS-DEF-001")
    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "Definition must not be empty" in output


def test_cli_rules_explain_unknown() -> None:
    result = _run_cli("rules", "explain", "GLOS-NOPE-999")
    assert result.returncode == 2


def test_cli_check_csv_failure(
    minimal_glossary_path: Path, dictionary_csv_path: Path
) -> None:
    result = _run_cli(
        "check",
        str(dictionary_csv_path),
        "--glossary",
        str(minimal_glossary_path),
        "--format",
        "json",
    )
    assert result.returncode == 1
    assert "DICT-HEAD-001" in result.stdout


def test_cli_check_frictionless(
    minimal_glossary_path: Path, table_schema_path: Path
) -> None:
    result = _run_cli(
        "check",
        str(table_schema_path),
        "--glossary",
        str(minimal_glossary_path),
        "--frictionless",
    )
    assert result.returncode == 1


def test_cli_check_missing_glossary(dictionary_csv_path: Path, tmp_path: Path) -> None:
    result = _run_cli(
        "check",
        str(dictionary_csv_path),
        "--glossary",
        str(tmp_path / "missing.yaml"),
    )
    assert result.returncode == 3


def test_cli_export_skos(minimal_glossary_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.ttl"
    result = _run_cli("export", "skos", str(minimal_glossary_path), "-o", str(out))
    assert result.returncode == 0
    assert out.exists()


def test_cli_export_jsonld(minimal_glossary_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.jsonld"
    result = _run_cli("export", "jsonld", str(minimal_glossary_path), "-o", str(out))
    assert result.returncode == 0


def test_cli_export_csv_unknown_profile(minimal_glossary_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.csv"
    result = _run_cli(
        "export", "csv", str(minimal_glossary_path), "-o", str(out), "--profile", "bad"
    )
    assert result.returncode == 2


def test_cli_export_site(minimal_glossary_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "site"
    result = _run_cli("export", "site", str(minimal_glossary_path), "-o", str(out))
    assert result.returncode == 0
    assert (out / "index.html").exists()


def test_cli_templates(tmp_path: Path) -> None:
    out = tmp_path / "gov"
    result = _run_cli("templates", "-o", str(out))
    assert result.returncode == 0
    assert any(out.iterdir())


def test_cli_assess(sample_glossary_path: Path, tmp_path: Path) -> None:
    html = tmp_path / "report.html"
    result = _run_cli("assess", str(sample_glossary_path), "-o", str(html))
    assert result.returncode == 0
    assert html.exists()
    assert html.with_suffix(".json").exists()


def test_cli_governance_init_alias(tmp_path: Path) -> None:
    out = tmp_path / "gov"
    result = _run_cli("governance", "init", "-o", str(out))
    assert result.returncode == 0


def test_cli_report_maturity_alias(sample_glossary_path: Path, tmp_path: Path) -> None:
    html = tmp_path / "maturity.html"
    result = _run_cli("report", "maturity", str(sample_glossary_path), "-o", str(html))
    assert result.returncode == 0


def test_sample_glossary_validate(sample_glossary_path: Path) -> None:
    result = _run_cli("validate", str(sample_glossary_path))
    assert result.returncode == 0
    assert "60 terms" in result.stdout or "60 terms" in result.stderr


def test_cli_export_missing_input(tmp_path: Path) -> None:
    missing = str(tmp_path / "missing.yaml")
    out = str(tmp_path / "x.ttl")
    result = _run_cli("export", "skos", missing, "-o", out)
    assert result.returncode == 3
