from __future__ import annotations

import hashlib
import posixpath
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
UNRESERVED_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


def _with_default_scheme(url: str) -> str:
    stripped = url.strip()
    if stripped.startswith("//"):
        return f"https:{stripped}"
    if "://" not in stripped:
        return f"https://{stripped}"
    return stripped


def _decode_unreserved_path(path: str) -> str:
    def replace(match: re.Match[str]) -> str:
        value = chr(int(match.group(0)[1:], 16))
        return value if value in UNRESERVED_CHARS else match.group(0).upper()

    return re.sub(r"%[0-9a-fA-F]{2}", replace, path)


def canonicalize_url(url: str) -> str:
    parsed = urlsplit(_with_default_scheme(url))
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.hostname.lower() if parsed.hostname else parsed.netloc.lower()
    if parsed.port and not ((scheme == "https" and parsed.port == 443) or (scheme == "http" and parsed.port == 80)):
        netloc = f"{netloc}:{parsed.port}"
    path = posixpath.normpath(_decode_unreserved_path(parsed.path or "/"))
    if parsed.path.endswith("/") and not path.endswith("/"):
        path += "/"
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in TRACKING_KEYS and not key.startswith(TRACKING_PREFIXES)
    ]
    query = urlencode(sorted(query_items))
    return urlunsplit((scheme, netloc, path, query, ""))


def content_hash(content: str | bytes) -> str:
    if isinstance(content, bytes):
        data = content.strip()
    else:
        data = content.strip().encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def slugify_url(url: str, max_length: int = 90) -> str:
    parsed = urlsplit(canonicalize_url(url))
    value = f"{parsed.netloc}{parsed.path}"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:max_length].strip("-") or "source"
