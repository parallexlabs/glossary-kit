from __future__ import annotations

from pathlib import Path

from glossary_kit.domain.models import Glossary, GlossaryMetadata, Term, TermStatus

FIXTURES = Path(__file__).parent / "fixtures"


def make_term(**overrides: object) -> Term:
    defaults: dict[str, object] = {
        "id": "term-1",
        "preferred_label": "Example term",
        "definition": "A concept used in automated tests.",
        "status": TermStatus.DRAFT,
        "language": "en",
    }
    defaults.update(overrides)
    return Term(**defaults)  # type: ignore[arg-type]


def make_glossary(*terms: Term, **metadata_overrides: object) -> Glossary:
    meta_defaults: dict[str, object] = {
        "title": "Test Glossary",
        "schema_version": "1.0.0",
    }
    meta_defaults.update(metadata_overrides)
    term_list = list(terms) if terms else [make_term()]
    return Glossary(metadata=GlossaryMetadata(**meta_defaults), terms=term_list)  # type: ignore[arg-type]
