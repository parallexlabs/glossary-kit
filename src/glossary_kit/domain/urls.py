from __future__ import annotations

from urllib.parse import urlparse

ALLOWED_URL_SCHEMES = frozenset({"http", "https"})


def is_safe_http_url(url: str) -> bool:
    """Return True when url is an absolute http(s) URL with a host."""
    if not url or not url.strip():
        return False
    value = url.strip()
    if value.startswith("//"):
        return False
    parsed = urlparse(value)
    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_URL_SCHEMES:
        return False
    return bool(parsed.netloc)
