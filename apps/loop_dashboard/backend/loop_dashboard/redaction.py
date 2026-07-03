from __future__ import annotations

import re


_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bghp_[A-Za-z0-9_]{8,}\b"), "[REDACTED]"),
    (
        re.compile(
            r"(?i)([\"']?\b(?:api[\s_-]*key|access[\s_-]*token|client[\s_-]*secret|token|password|secret)\b[\"']?\s*[=:]\s*[\"']?)([^\"'\s,;&}]+)([\"']?)"
        ),
        r"\1[REDACTED]\3",
    ),
)


def redact_text(text: str) -> str:
    redacted = _redact_authorization(text)
    for pattern, replacement in _REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _redact_authorization(text: str) -> str:
    pattern = re.compile(r"(?im)(Authorization[ \t]*:[ \t]*)([^\r\n]+)")

    def replace(match: re.Match[str]) -> str:
        prefix = match.group(1)
        value = match.group(2).strip()
        if value.lower().startswith("bearer "):
            return f"{prefix}Bearer [REDACTED]"
        return f"{prefix}[REDACTED]"

    return pattern.sub(replace, text)
