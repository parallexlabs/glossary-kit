from __future__ import annotations

import re

SLUG_SAFE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def term_slug(term_id: str) -> str:
    """Map a term id to a filesystem-safe slug."""
    return re.sub(r"[^a-z0-9-]", "-", term_id.lower())


def validate_slug_safe_ids(term_ids: list[str]) -> list[str]:
    """Return diagnostic messages for ids that are not slug-safe or collide after slugging."""
    messages: list[str] = []
    slug_to_id: dict[str, str] = {}
    for term_id in term_ids:
        if not SLUG_SAFE_ID_PATTERN.match(term_id):
            messages.append(
                f"Term id '{term_id}' must match slug-safe pattern "
                f"{SLUG_SAFE_ID_PATTERN.pattern}"
            )
        slug = term_slug(term_id)
        if slug in slug_to_id and slug_to_id[slug] != term_id:
            messages.append(
                f"Term id '{term_id}' collides with '{slug_to_id[slug]}' "
                f"after slugging (both map to '{slug}')"
            )
        else:
            slug_to_id[slug] = term_id
    return messages
