# Changelog

All notable changes to Glossary Kit are documented here.

## [0.1.0] - 2026-09-28

### Added

- Initial MVP release: validate, lint, check, export (SKOS, JSON-LD, CSV, site), templates, assess
- JSON Schema v1.0.0 and Pydantic v2 models
- Rule catalogue with GLOS-* and DICT-* diagnostic codes
- Sample glossary with 60 paraphrased terms from open Canadian sources
- Governance templates and maturity rubric (6 dimensions)
- GitHub Actions CI (ruff, mypy, pyright, pytest with ≥80% coverage, wheel smoke test, site accessibility checks)
- CLI entry points `glossary-kit` and `glossaryctl`
- Comprehensive test suite covering lint rules, validation, dictionary checks, exporters, site semantics, CLI exit codes, and SARIF/JSON diagnostics

### Changed

- Replaced flaky `@axe-core/cli` CI step with deterministic Python accessibility checks (landmarks, headings, table semantics, search index, non-colour-only status cues)

### Notes

- Definition-quality lint is ISO/IEC 11179-4-inspired, not ISO certification
- Schema version: 1.0.0
