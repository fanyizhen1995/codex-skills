from __future__ import annotations

import re


_TOKEN_PATTERN = re.compile(r"\bghp_[A-Za-z0-9_]{8,}\b")
_SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)([\"']?[A-Za-z0-9_-]*(?:api[\s_-]*key|access[\s_-]*token|client[\s_-]*secret|token|password|secret)[A-Za-z0-9_-]*[\"']?\s*[=:]\s*)"
    r"(\"(?:\\.|[^\"\\\r\n])*\"|'(?:\\.|[^'\\\r\n])*'|[^\s,;&}\r\n]+)"
)

_SENSITIVE_SEGMENTS = frozenset(
    {"apikey", "authorization", "password", "secret", "token"}
)
_SENSITIVE_SEQUENCES = (("api", "key"), ("access", "token"), ("client", "secret"))


def redact_text(text: str) -> str:
    redacted = _redact_authorization(text)
    redacted = _TOKEN_PATTERN.sub("[REDACTED]", redacted)
    return _SENSITIVE_ASSIGNMENT_PATTERN.sub(_redact_assignment, redacted)


def is_sensitive_key(key: str) -> bool:
    segments = key_segments(key)
    if not segments:
        return False
    compact = "".join(segments)
    if "apikey" in compact:
        return True
    if any(segment in _SENSITIVE_SEGMENTS for segment in segments):
        return True
    for sequence in _SENSITIVE_SEQUENCES:
        size = len(sequence)
        if any(
            tuple(segments[index : index + size]) == sequence
            for index in range(0, len(segments) - size + 1)
        ):
            return True
    return False


def key_segments(key: str) -> list[str]:
    return [
        segment.lower()
        for segment in re.findall(
            r"[A-Z]+(?=[A-Z][a-z]|\d|[^A-Za-z0-9]|$)|[A-Z]?[a-z]+|\d+",
            key.strip(),
        )
    ]


def _redact_authorization(text: str) -> str:
    pattern = re.compile(r"(?im)(Authorization[ \t]*[=:][ \t]*)([^\r\n]+)")

    def replace(match: re.Match[str]) -> str:
        prefix = match.group(1)
        value = match.group(2).strip()
        if value.lower().startswith("bearer "):
            return f"{prefix}Bearer [REDACTED]"
        return f"{prefix}[REDACTED]"

    return pattern.sub(replace, text)


def _redact_assignment(match: re.Match[str]) -> str:
    prefix = match.group(1)
    value = match.group(2)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return f"{prefix}{value[0]}[REDACTED]{value[-1]}"
    return f"{prefix}[REDACTED]"
