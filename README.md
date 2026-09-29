# Glossary Kit

Open-source glossary-as-code toolkit from **ParalleX Labs Inc.** for public-sector data governance teams. Glossary Kit combines structural validation, ISO/IEC 11179-4-inspired definition linting, Frictionless dictionary checks, governance templates, maturity self-assessment, and accessible static site export in one CLI package.

Sample glossary definitions are paraphrased from openly licensed Canadian government sources. No clients, deployments, or procurement outcomes are claimed.

## Open by design

**We build in the open.** ParalleX Labs Inc. publishes its tools, methods and learning materials under open licences, so public-interest teams can use them, check how they work and adapt them freely. Open work is easier to trust, because anyone can see exactly how a result is produced. Code is licensed under Apache-2.0.

**Our own work, and only ours.** Everything in this repository was created by ParalleX Labs Inc. from public data and synthetic examples. It contains no client data, no client projects, and no one else's confidential information or intellectual property.

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

Rules are **ISO/IEC 11179-4-informed**; they do not certify ISO conformance.

| Code | Severity | Standard mapping |
|------|----------|------------------|
| GLOS-STRUCT-001 | error | Required fields (ISO/IEC 11179-3/4-informed) |
| GLOS-STRUCT-002 | error | Unique term id |
| GLOS-STRUCT-003 | error | Duplicate label / synonym conflict (SKOS-informed) |
| GLOS-STRUCT-004 | error | Slug-safe term ids |
| GLOS-REL-001 | error | Resolvable references (SKOS / ISO 1087-informed) |
| GLOS-REL-002 | error | Acyclic replaces graph |
| GLOS-REL-003 | error | Public terms must not reference internal related terms |
| GLOS-GOV-001 | error | Steward on approved terms (ISO/IEC 38505-1-informed) |
| GLOS-GOV-002 | error | Source on approved terms |
| GLOS-GOV-003 | warning | Deprecated terms should link to replacement |
| GLOS-DEF-001 | error | Non-empty definition |
| GLOS-DEF-002 | error | No tautology |
| GLOS-DEF-003 | warning | Singular label heuristic (strict profile only) |
| GLOS-DEF-004 | warning | Self-reference in definition |
| GLOS-DEF-005 | warning | Affirmative phrasing |
| GLOS-LEX-001 | warning | Abbreviation expansion in parentheses |
| DICT-HEAD-001 | error | CSV header mapping (Frictionless-informed) |
| DICT-FRIC-001 | error | Frictionless field mapping |
| DICT-FRIC-002 | error | Frictionless field shape / logical type |
| DICT-BIND-001 | error | Explicit dictionary bindings |
| DICT-BIND-002 | error | Binding term reference |
| DICT-BIND-003 | error | Duplicate binding header |

Run `glossary-kit rules explain GLOS-DEF-001` for details.

## Sample data licence obligations

The sample glossary (`examples/sample_glossary.yaml`) includes paraphrased definitions from:

- [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada)
- [Statistics Canada Open Licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence)

BC security classification terms (43–46) are included with `reuse_status: licence_not_verified` and `demo: true` because text reuse from BC policy PDFs is unclear.

## Limitations

- No catalogue platform integration (OpenMetadata, DataHub) in MVP
- No NLP genus–differentia enforcement
- Maturity report reflects metadata evidence only, not organizational compliance
- Site export accessibility is checked by deterministic HTML semantics tests (landmarks, heading order, search form inside `main`, unique element IDs, labelled search input, focus-visible CSS tokens, table captions on maturity reports). These tests do not run axe-core or assert zero WCAG violations.
- Operates offline; no network calls by default

## Development

```bash
make install
make test
make lint
make typecheck
```

## Licence

Apache-2.0. See [LICENSE](LICENSE). Sample content remains under its respective source licences.
