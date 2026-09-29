# Contributing

Thank you for contributing to Glossary Kit.

## Setup

```bash
pip install -e ".[dev]"
```

## Quality checks

Before submitting changes, run:

```bash
ruff check src tests
mypy src/glossary_kit
pyright src/glossary_kit
pytest
```

## Guidelines

- Keep changes focused and match existing code style.
- Add tests for new behaviour.
- Update `CHANGELOG.md` for user-visible changes.
- Cite public sources for factual claims in documentation.
- Do not include secrets or PII in sample data.
- Label definition-quality rules as ISO/IEC 11179-4-inspired, not certifying conformance.

## Schema changes

Breaking schema changes require a new `schema_version` and updated JSON Schema under `src/glossary_kit/resources/jsonschema/`.
