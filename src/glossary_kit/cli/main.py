from __future__ import annotations

import sys
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from glossary_kit import __version__
from glossary_kit.assess.maturity import assess_maturity, write_maturity_html, write_maturity_json
from glossary_kit.check.dictionary import check_dictionary_csv, check_frictionless_schema
from glossary_kit.diagnostics.models import (
    Diagnostic,
    Severity,
    format_diagnostics_json,
    format_diagnostics_sarif,
    format_diagnostics_text,
)
from glossary_kit.exports import export_csv, export_jsonld, export_site, export_skos_turtle
from glossary_kit.governance.templates import init_governance_templates
from glossary_kit.ingest.loader import IngestError, load_glossary
from glossary_kit.lint.engine import lint_glossary
from glossary_kit.rules.catalog import explain_rule, list_rules
from glossary_kit.validate.structural import validate_glossary_path

app = typer.Typer(
    name="glossary-kit",
    help="Glossary-as-code toolkit for public-sector data governance",
    no_args_is_help=True,
)
console = Console(stderr=True)

EXIT_SUCCESS = 0
EXIT_VALIDATION = 1
EXIT_CLI = 2
EXIT_INPUT = 3


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"
    SARIF = "sarif"


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"glossary-kit {__version__}")
        raise typer.Exit(EXIT_SUCCESS)


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    """Glossary Kit CLI."""


def _emit(diagnostics: list[Diagnostic], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.JSON:
        typer.echo(format_diagnostics_json(diagnostics))
    elif fmt == OutputFormat.SARIF:
        typer.echo(format_diagnostics_sarif(diagnostics))
    else:
        console.print(format_diagnostics_text(diagnostics))


def _has_errors(diagnostics: list[Diagnostic]) -> bool:
    return any(d.severity == Severity.ERROR for d in diagnostics)


@app.command("validate")
def validate_cmd(
    glossary_path: Annotated[Path, typer.Argument(help="Path to glossary YAML or CSV")],
) -> None:
    """Validate glossary structure (JSON Schema + Pydantic)."""
    glossary, diagnostics = validate_glossary_path(glossary_path)
    if glossary is None and diagnostics:
        _emit(diagnostics, OutputFormat.TEXT)
        raise typer.Exit(EXIT_INPUT if diagnostics[0].code == "INPUT-001" else EXIT_VALIDATION)
    if _has_errors(diagnostics):
        _emit(diagnostics, OutputFormat.TEXT)
        raise typer.Exit(EXIT_VALIDATION)
    if diagnostics:
        _emit(diagnostics, OutputFormat.TEXT)
    console.print(f"Validation passed: {len(glossary.terms if glossary else [])} terms")
    raise typer.Exit(EXIT_SUCCESS)


@app.command("lint")
def lint_cmd(
    glossary_path: Annotated[Path, typer.Argument()],
    profile: Annotated[str, typer.Option(help="Lint profile: standard or strict")] = "standard",
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
) -> None:
    """Run ISO/IEC 11179-4-inspired definition-quality lint rules."""
    if profile not in {"standard", "strict"}:
        console.print(f"Unknown profile: {profile}")
        raise typer.Exit(EXIT_CLI)
    try:
        glossary = load_glossary(glossary_path)
    except IngestError as exc:
        console.print(str(exc))
        raise typer.Exit(EXIT_INPUT) from exc

    _, struct_diags = validate_glossary_path(glossary_path)
    lint_diags = lint_glossary(glossary, profile=profile)
    diagnostics = struct_diags + lint_diags
    _emit(diagnostics, format)
    raise typer.Exit(EXIT_VALIDATION if _has_errors(diagnostics) else EXIT_SUCCESS)


@app.command("check")
def check_cmd(
    dictionary_path: Annotated[Path, typer.Argument(help="Dictionary CSV or Frictionless schema")],
    glossary: Annotated[Path, typer.Option("--glossary", help="Glossary YAML path")],
    frictionless: Annotated[bool, typer.Option(help="Input is Frictionless Table Schema")] = False,
    fuzzy: Annotated[bool, typer.Option(help="Enable fuzzy header suggestions")] = False,
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
) -> None:
    """Check dictionary alignment against glossary."""
    try:
        gloss = load_glossary(glossary)
    except IngestError as exc:
        console.print(str(exc))
        raise typer.Exit(EXIT_INPUT) from exc

    if frictionless or dictionary_path.suffix.lower() in {".yaml", ".yml"}:
        diagnostics = check_frictionless_schema(dictionary_path, gloss)
    else:
        diagnostics = check_dictionary_csv(dictionary_path, gloss, fuzzy=fuzzy)

    _emit(diagnostics, format)
    raise typer.Exit(EXIT_VALIDATION if _has_errors(diagnostics) else EXIT_SUCCESS)


export_app = typer.Typer(help="Export glossary to external formats")
app.add_typer(export_app, name="export")


@export_app.command("skos")
def export_skos_cmd(
    glossary_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path, typer.Option("--output", "-o")],
) -> None:
    """Export SKOS Turtle."""
    try:
        glossary = load_glossary(glossary_path)
    except IngestError as exc:
        console.print(str(exc))
        raise typer.Exit(EXIT_INPUT) from exc
    export_skos_turtle(glossary, output)
    console.print(f"Wrote {output}")
    raise typer.Exit(EXIT_SUCCESS)


@export_app.command("jsonld")
def export_jsonld_cmd(
    glossary_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path, typer.Option("--output", "-o")],
) -> None:
    """Export JSON-LD with SKOS context."""
    try:
        glossary = load_glossary(glossary_path)
    except IngestError as exc:
        console.print(str(exc))
        raise typer.Exit(EXIT_INPUT) from exc
    export_jsonld(glossary, output)
    console.print(f"Wrote {output}")
    raise typer.Exit(EXIT_SUCCESS)


@export_app.command("csv")
def export_csv_cmd(
    glossary_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path, typer.Option("--output", "-o")],
    profile: Annotated[str, typer.Option(help="human or roundtrip")] = "human",
) -> None:
    """Export CSV (human-review or round-trip profile)."""
    if profile not in {"human", "roundtrip"}:
        console.print(f"Unknown profile: {profile}")
        raise typer.Exit(EXIT_CLI)
    try:
        glossary = load_glossary(glossary_path)
    except IngestError as exc:
        console.print(str(exc))
        raise typer.Exit(EXIT_INPUT) from exc
    export_csv(glossary, output, profile=profile)
    console.print(f"Wrote {output}")
    raise typer.Exit(EXIT_SUCCESS)


@export_app.command("site")
def export_site_cmd(
    glossary_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path, typer.Option("--output", "-o")],
) -> None:
    """Export accessible static HTML site."""
    try:
        glossary = load_glossary(glossary_path)
    except IngestError as exc:
        console.print(str(exc))
        raise typer.Exit(EXIT_INPUT) from exc
    export_site(glossary, output)
    console.print(f"Wrote site to {output}")
    raise typer.Exit(EXIT_SUCCESS)


@app.command("templates")
def templates_cmd(
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")],
) -> None:
    """Initialize governance template pack."""
    written = init_governance_templates(output)
    for path in written:
        console.print(f"Wrote {path}")
    raise typer.Exit(EXIT_SUCCESS)


@app.command("assess")
def assess_cmd(
    glossary_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    json_output: Annotated[Path | None, typer.Option("--json", help="JSON report path")] = None,
) -> None:
    """Generate maturity assessment report (JSON + HTML)."""
    try:
        glossary = load_glossary(glossary_path)
    except IngestError as exc:
        console.print(str(exc))
        raise typer.Exit(EXIT_INPUT) from exc

    report = assess_maturity(glossary)
    html_path = output or Path("maturity.html")
    json_path = json_output or html_path.with_suffix(".json")
    write_maturity_html(report, html_path)
    write_maturity_json(report, json_path)
    console.print(f"Wrote {html_path} and {json_path}")
    raise typer.Exit(EXIT_SUCCESS)


rules_app = typer.Typer(help="Rule catalogue")
app.add_typer(rules_app, name="rules")

report_app = typer.Typer(help="Reports (ACCEPTANCE alias)")
app.add_typer(report_app, name="report")

governance_app = typer.Typer(help="Governance (ACCEPTANCE alias)")
app.add_typer(governance_app, name="governance")


@rules_app.command("list")
def rules_list_cmd() -> None:
    """List validation and lint rules."""
    for rule in list_rules():
        typer.echo(f"{rule.code}\t{rule.severity}\t{rule.name}")
    raise typer.Exit(EXIT_SUCCESS)


@rules_app.command("explain")
def rules_explain_cmd(
    code: Annotated[str, typer.Argument(help="Rule code e.g. GLOS-DEF-001")],
) -> None:
    """Explain a rule by code."""
    rule = explain_rule(code)
    if rule is None:
        console.print(f"Unknown rule: {code}")
        raise typer.Exit(EXIT_CLI)
    console.print(f"Code: {rule.code}")
    console.print(f"Name: {rule.name}")
    console.print(f"Severity: {rule.severity}")
    console.print(f"Standard: {rule.standard}")
    console.print(f"Description: {rule.description}")
    raise typer.Exit(EXIT_SUCCESS)


@report_app.command("maturity")
def report_maturity_alias(
    glossary_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    json_output: Annotated[Path | None, typer.Option("--json")] = None,
) -> None:
    """ACCEPTANCE alias for assess."""
    assess_cmd(glossary_path, output, json_output)


@governance_app.command("init")
def governance_init_alias(
    output: Annotated[Path, typer.Option("--output", "-o")],
) -> None:
    """ACCEPTANCE alias for templates."""
    templates_cmd(output)


def app_main() -> None:
    try:
        app()
    except typer.Exit as exc:
        sys.exit(exc.exit_code)


if __name__ == "__main__":
    app_main()
