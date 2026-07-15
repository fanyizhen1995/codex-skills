from __future__ import annotations

import re


_TOKEN_PATTERN = re.compile(r"\bghp_[A-Za-z0-9_]{8,}\b")
_ASSIGNMENT_KEY_LOOKBACK = 256
_UNQUOTED_VALUE_DELIMITERS = frozenset(",;&}")

_SENSITIVE_SEGMENTS = frozenset(
    {"apikey", "authorization", "password", "secret", "token"}
)
_SENSITIVE_SEQUENCES = (("api", "key"), ("access", "token"), ("client", "secret"))


def redact_text(text: str) -> str:
    redacted = _redact_authorization(text)
    redacted = _TOKEN_PATTERN.sub("[REDACTED]", redacted)
    return _redact_assignments(redacted)


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


def _redact_assignments(text: str) -> str:
    chunks: list[str] = []
    copy_from = 0
    index = 0
    while index < len(text):
        if text[index] not in {"=", ":"} or not _has_sensitive_key(
            text, index
        ):
            index += 1
            continue

        value_start = index + 1
        while value_start < len(text) and text[value_start] in {" ", "\t"}:
            value_start += 1
        if value_start >= len(text) or text[value_start] in {"\r", "\n"}:
            index += 1
            continue

        quote = text[value_start] if text[value_start] in {'"', "'"} else ""
        if quote:
            value_end, closed = _quoted_value_end(text, value_start + 1, quote)
            chunks.extend((text[copy_from : value_start + 1], "[REDACTED]"))
            if closed:
                chunks.append(quote)
                value_end += 1
        else:
            value_end = value_start
            while value_end < len(text):
                character = text[value_end]
                if character.isspace() or character in _UNQUOTED_VALUE_DELIMITERS:
                    break
                value_end += 1
            if value_end == value_start:
                index += 1
                continue
            chunks.extend((text[copy_from:value_start], "[REDACTED]"))

        copy_from = value_end
        index = value_end

    if not chunks:
        return text
    chunks.append(text[copy_from:])
    return "".join(chunks)


def _has_sensitive_key(text: str, separator: int) -> bool:
    key_end = separator
    while key_end > 0 and text[key_end - 1] in {" ", "\t"}:
        key_end -= 1
    if key_end == 0:
        return False

    lower_bound = max(0, key_end - _ASSIGNMENT_KEY_LOOKBACK)
    if text[key_end - 1] in {'"', "'"}:
        quote = text[key_end - 1]
        key_start = text.rfind(quote, lower_bound, key_end - 1)
        if key_start < 0:
            return False
        key = text[key_start + 1 : key_end - 1]
    else:
        key_start = key_end
        while key_start > lower_bound and _is_assignment_key_character(
            text[key_start - 1]
        ):
            key_start -= 1
        key = text[key_start:key_end].strip()
    segments = key_segments(key)
    return (
        bool(key)
        and (not segments or segments[-1] != "authorization")
        and is_sensitive_key(key)
    )


def _quoted_value_end(text: str, start: int, quote: str) -> tuple[int, bool]:
    index = start
    while index < len(text):
        character = text[index]
        if character in {"\r", "\n"}:
            return index, False
        if character == "\\":
            index += 2
            continue
        if character == quote:
            return index, True
        index += 1
    return len(text), False


def _is_assignment_key_character(character: str) -> bool:
    return character.isalnum() or character in {"_", "-", " ", "\t"}
