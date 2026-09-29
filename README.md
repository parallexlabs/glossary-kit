# Glossary Kit

Open-source glossary-as-code toolkit from **ParalleX Labs Inc.** for public-sector data governance teams. Glossary Kit combines structural validation, ISO/IEC 11179-4-inspired definition linting, Frictionless dictionary checks, governance templates, maturity self-assessment, and accessible static site export in one CLI package.

This is a **showcase project**. Sample glossary definitions are paraphrased from openly licensed Canadian government sources. No clients, deployments, or procurement outcomes are claimed.

## Quickstart

```bash
pip install -e ".[dev]"

# Validate and lint a glossary
glossary-kit validate examples/sample_glossary.yaml
glossary-kit lint examples/sample_glossary.yaml --format json

# Export artefacts
glossary-kit export skos examples/sample_glossary.yaml -o dist/glossary.ttl
glossary-kit export site examples/sample_glossary.yaml -o dist/site

# Full demo pipeline
make demo
```

Both `glossary-kit` and `glossaryctl` entry points are available.

## CLI reference

| Command | Description |
|---------|-------------|
| `validate <glossary>` | JSON Schema + Pydantic structural validation |
| `lint <glossary> [--profile standard\|strict] [--format text\|json\|sarif]` | Definition-quality and governance lint |
| `check <dictionary.csv> --glossary <glossary>` | CSV header alignment |
| `check <schema.yaml> --glossary <glossary> --frictionless` | Frictionless Table Schema alignment |
| `export skos\|jsonld\|csv\|site` | Deterministic exporters |
| `templates -o <dir>` | Governance template pack (alias: `governance init`) |
| `assess <glossary> [-o report.html]` | Maturity report JSON + HTML (alias: `report maturity`) |
| `rules list` / `rules explain <code>` | Rule catalogue |

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Validation or lint failure |
| 2 | CLI or configuration error |
| 3 | Unreadable input |

## Schema

Primary format: YAML glossary with `metadata` and `terms`. Published JSON Schema: `$id` `https://glossary-kit.dev/schema/glossary/1.0.0`, version `1.0.0`.

Required term fields: `id`, `preferred_label`, `definition`, `status`, `language`.

## Rule catalogue

Rules are **ISO/IEC 11179-4-inspired** — they do not certify ISO conformance.

| Code | Severity | Standard mapping |
|------|----------|------------------|
| GLOS-STRUCT-001 | error | Required fields (ISO/IEC 11179-3/4) |
| GLOS-STRUCT-002 | error | Unique term id |
| GLOS-STRUCT-003 | error | Duplicate label / synonym conflict (SKOS) |
| GLOS-REL-001 | error | Resolvable references (SKOS / ISO 1087) |
| GLOS-REL-002 | error | Acyclic replaces graph |
| GLOS-GOV-001 | error | Steward on approved terms (ISO/IEC 38505-1) |
| GLOS-GOV-002 | error | Source on approved terms |
| GLOS-GOV-003 | warning | Deprecated terms should link to replacement |
| GLOS-DEF-001 | error | Non-empty definition |
| GLOS-DEF-002 | error | No tautology |
| GLOS-DEF-003 | warning | Singular label heuristic |
| GLOS-DEF-004 | warning | Self-reference in definition |
| GLOS-DEF-005 | warning | Affirmative phrasing |
| GLOS-LEX-001 | warning | Abbreviation expansion |
| DICT-HEAD-001 | error | CSV header mapping (Frictionless) |
| DICT-FRIC-001 | error | Frictionless field mapping |
| DICT-BIND-001 | error | Explicit dictionary bindings |

Run `glossary-kit rules explain GLOS-DEF-001` for details.

## Sample data licence obligations

The sample glossary (`examples/sample_glossary.yaml`) includes paraphrased definitions from:

- [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada)
- [Statistics Canada Open Licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence)

BC security classification terms (43–46) are included with `reuse_status: licence_not_verified` and `demo: true` because text reuse from BC policy PDFs is unclear.

## Limitations

- No catalogue platform integration (OpenMetadata, DataHub) in MVP
- No NLP genus–differentia enforcement
- Maturity report reflects metadata evidence only — not organizational compliance
- WCAG 2.2 AA is an engineering target; jurisdictional compliance mapping is separate
- Operates offline; no network calls by default

## Development

```bash
make install
make test
make lint
make typecheck
```

## Licence

Apache-2.0 — see [LICENSE](LICENSE). Sample content remains under its respective source licences.
