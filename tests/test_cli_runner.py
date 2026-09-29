from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from glossary_kit.cli.main import app
from glossary_kit.domain.models import Glossary
from glossary_kit.ingest.loader import load_glossary

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "validate" in result.stdout


def _out(result: object) -> str:
    from typer.testing import Result

    assert isinstance(result, Result)
    return (result.stdout or "") + (result.stderr or "")


def test_cli_validate_success(minimal_glossary_path: Path) -> None:
    result = runner.invoke(app, ["validate", str(minimal_glossary_path)])
    assert result.exit_code == 0
    assert "Validation passed" in _out(result)


def test_cli_validate_structural_failure(minimal_glossary_path: Path, tmp_path: Path) -> None:
    data = yaml.safe_load(minimal_glossary_path.read_text(encoding="utf-8"))
    data["terms"].append(
        {
            "id": "alpha",
            "preferred_label": "Duplicate",
            "definition": "dup id",
            "status": "draft",
            "language": "en",
        }
    )
    bad = tmp_path / "dup.yaml"
    bad.write_text(yaml.dump(data), encoding="utf-8")
    result = runner.invoke(app, ["validate", str(bad)])
    assert result.exit_code == 1
    assert "GLOS-STRUCT-002" in _out(result)


def test_cli_validate_missing_file(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", str(tmp_path / "missing.yaml")])
    assert result.exit_code == 3


def test_cli_lint_text(minimal_glossary_path: Path) -> None:
    result = runner.invoke(app, ["lint", str(minimal_glossary_path)])
    assert result.exit_code == 0


def test_cli_lint_json(minimal_glossary_path: Path) -> None:
    result = runner.invoke(app, ["lint", str(minimal_glossary_path), "--format", "json"])
    assert result.exit_code == 0
    assert "[" in result.stdout


def test_cli_lint_sarif_failure(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
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
    result = runner.invoke(app, ["lint", str(bad), "--format", "sarif"])
    assert result.exit_code == 1
    assert '"version": "2.1.0"' in result.stdout


def test_cli_lint_bad_profile(minimal_glossary_path: Path) -> None:
    result = runner.invoke(app, ["lint", str(minimal_glossary_path), "--profile", "nope"])
    assert result.exit_code == 2


def test_cli_check_csv(
    minimal_glossary_path: Path, dictionary_csv_path: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "check",
            str(dictionary_csv_path),
            "--glossary",
            str(minimal_glossary_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 1


def test_cli_check_frictionless(
    minimal_glossary_path: Path, table_schema_path: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "check",
            str(table_schema_path),
            "--glossary",
            str(minimal_glossary_path),
            "--frictionless",
        ],
    )
    assert result.exit_code == 1


def test_cli_export_commands(minimal_glossary_path: Path, tmp_path: Path) -> None:
    skos = tmp_path / "g.ttl"
    result = runner.invoke(app, ["export", "skos", str(minimal_glossary_path), "-o", str(skos)])
    assert result.exit_code == 0
    assert skos.exists()

    jsonld = tmp_path / "g.jsonld"
    result = runner.invoke(
        app, ["export", "jsonld", str(minimal_glossary_path), "-o", str(jsonld)]
    )
    assert result.exit_code == 0

    csv_out = tmp_path / "g.csv"
    result = runner.invoke(
        app, ["export", "csv", str(minimal_glossary_path), "-o", str(csv_out)]
    )
    assert result.exit_code == 0

    site = tmp_path / "site"
    result = runner.invoke(
        app, ["export", "site", str(minimal_glossary_path), "-o", str(site)]
    )
    assert result.exit_code == 0
    assert (site / "index.html").exists()


def test_cli_export_csv_bad_profile(minimal_glossary_path: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "export",
            "csv",
            str(minimal_glossary_path),
            "-o",
            str(tmp_path / "x.csv"),
            "--profile",
            "x",
        ],
    )
    assert result.exit_code == 2


def test_cli_templates_and_assess(sample_glossary_path: Path, tmp_path: Path) -> None:
    gov = tmp_path / "gov"
    result = runner.invoke(app, ["templates", "-o", str(gov)])
    assert result.exit_code == 0

    html = tmp_path / "maturity.html"
    result = runner.invoke(app, ["assess", str(sample_glossary_path), "-o", str(html)])
    assert result.exit_code == 0
    assert html.with_suffix(".json").exists()


def test_cli_aliases(sample_glossary_path: Path, tmp_path: Path) -> None:
    gov = tmp_path / "gov2"
    result = runner.invoke(app, ["governance", "init", "-o", str(gov)])
    assert result.exit_code == 0

    html = tmp_path / "report.html"
    result = runner.invoke(app, ["report", "maturity", str(sample_glossary_path), "-o", str(html)])
    assert result.exit_code == 0


def test_cli_rules_commands() -> None:
    result = runner.invoke(app, ["rules", "list"])
    assert result.exit_code == 0
    assert "GLOS-DEF-001" in result.stdout

    result = runner.invoke(app, ["rules", "explain", "GLOS-DEF-001"])
    assert result.exit_code == 0
    assert "Definition must not be empty" in _out(result)

    result = runner.invoke(app, ["rules", "explain", "NOPE"])
    assert result.exit_code == 2


def test_cli_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "glossary-kit" in _out(result)


def test_cli_ingest_error_paths(tmp_path: Path) -> None:
    missing = str(tmp_path / "missing.yaml")
    for args in (
        ["lint", missing],
        ["check", str(tmp_path / "d.csv"), "--glossary", missing],
        ["export", "skos", missing, "-o", str(tmp_path / "x.ttl")],
        ["export", "jsonld", missing, "-o", str(tmp_path / "x.jsonld")],
        ["export", "csv", missing, "-o", str(tmp_path / "x.csv")],
        ["export", "site", missing, "-o", str(tmp_path / "site")],
        ["assess", missing],
    ):
        result = runner.invoke(app, args)
        assert result.exit_code == 3, args


def test_cli_validate_emits_success_for_valid_glossary(minimal_glossary_path: Path) -> None:
    result = runner.invoke(app, ["validate", str(minimal_glossary_path)])
    assert result.exit_code == 0


def test_validate_glossary_path_validation_error_branch(
    minimal_glossary_path: Path, tmp_path: Path
) -> None:
    from glossary_kit.validate.structural import validate_glossary_path

    load_glossary(minimal_glossary_path)

    def _raise_validation(_path: Path) -> Glossary:
        raise ValidationError.from_exception_data(
            "Glossary",
            [
                {
                    "type": "missing",
                    "loc": ("terms", 0, "definition"),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

    with patch("glossary_kit.validate.structural.load_glossary", side_effect=_raise_validation):
        loaded, diags = validate_glossary_path(tmp_path / "ignored.yaml")
    assert loaded is None
    assert diags[0].code == "GLOS-STRUCT-001"
