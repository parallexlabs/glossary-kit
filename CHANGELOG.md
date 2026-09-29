# Changelog

All notable changes to Glossary Kit are documented here.

## [0.2.0] - 2026-09-28

### Fixed

- JSON-LD exports now emit per-term language-tagged literals (`@value` + `@language`) instead of a fixed English `@context` default
- URL fields (`source_url`, `licence_url`, `Source.url`) reject `javascript:`, `data:`, `vbscript:`, protocol-relative and malformed URLs at ingest time
- `validate` now maps Pydantic `ValidationError` locations to `GLOS-STRUCT-001` diagnostics with JSON paths; `INPUT-001` is reserved for unreadable input only
- Frictionless checker validates field shape, reports malformed field indices, and documents logical-type comparison for `string`, `integer`, `number`, `boolean`, `date`, and `datetime`
- Dictionary bindings are validated for unknown `term_id`, duplicate headers, and owner mismatches (`DICT-BIND-002`, `DICT-BIND-003`)
- Site export detects slug collisions, writes atomically via a staging directory, removes stale manifest-listed pages, and writes `manifest.json`
- Public RDF exports omit `skos:related` to internal terms; public terms referencing internal related terms raise `GLOS-REL-003`
- `replaces` / `replaced_by` export as `gloss:replaces` and `gloss:replacedBy` URI properties (documented extension) instead of opaque `skos:changeNote` strings
- Term pages use the term label as the sole `h1`; index search controls are a `role="search"` form inside `<main>`

### Changed

- GLOS-DEF-003 plural-label heuristic runs only in the `strict` lint profile
- GLOS-LEX-001 now requires parenthetical abbreviation expansion in definitions
- Rule catalogue standard mappings use “informed by” wording
- JSON Schema nested objects use `additionalProperties: false`, URLs use an `http(s)` pattern, and `definition` requires `minLength: 1`
- Site accessibility CI checks deterministic HTML semantics (landmarks, heading order, search form placement, unique IDs, labelled search input, focus-visible CSS tokens, table captions) rather than claiming axe-core zero-critical-violation coverage
- Minimum test coverage raised to 90%

### Added

- New diagnostics: `GLOS-STRUCT-004`, `GLOS-REL-003`, `DICT-FRIC-002`, `DICT-BIND-002`, `DICT-BIND-003`
- Regression tests in `tests/test_v020_fixes.py` for language tags, URL safety, CLI paths, bindings, slugs, RDF, site semantics, and schema parity

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

- Definition-quality lint is ISO/IEC 11179-4-informed, not ISO certification
- Schema version: 1.0.0
