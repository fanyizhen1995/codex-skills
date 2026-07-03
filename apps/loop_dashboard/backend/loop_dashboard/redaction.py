from __future__ import annotations

import re


_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(Authorization\s*:\s*Bearer\s+)([^\s]+)"), r"\1[REDACTED]"),
    (re.compile(r"\bghp_[A-Za-z0-9_]{8,}\b"), "[REDACTED]"),
    (
        re.compile(r"(?i)\b(token|password|secret|api_key)(\s*[=:]\s*)([^\s,;&]+)"),
        r"\1\2[REDACTED]",
    ),
)


def redact_text(text: str) -> str:
    redacted = text
    for pattern, replacement in _REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted
