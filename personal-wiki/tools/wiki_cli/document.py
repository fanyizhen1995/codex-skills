from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MarkdownDocument:
    frontmatter: dict[str, Any]
    body: str


def parse_markdown(text: str) -> MarkdownDocument:
    if not text.startswith("---\n"):
        return MarkdownDocument(frontmatter={}, body=text)

    closing = text.find("\n---", 4)
    if closing == -1:
        return MarkdownDocument(frontmatter={}, body=text)

    delimiter_end = closing + len("\n---")
    if len(text) > delimiter_end and text[delimiter_end] not in "\r\n":
        return MarkdownDocument(frontmatter={}, body=text)

    frontmatter_text = text[4:closing]
    body_start = delimiter_end
    if text.startswith("\r\n", body_start):
        body_start += 2
    elif text.startswith("\n", body_start):
        body_start += 1
    return MarkdownDocument(frontmatter=_parse_frontmatter(frontmatter_text), body=text[body_start:])


def serialize_markdown(doc: MarkdownDocument) -> str:
    if not doc.frontmatter:
        return doc.body

    lines = ["---"]
    for key, value in doc.frontmatter.items():
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                lines.extend(f"  - {item}" for item in value)
            else:
                lines.append(f"{key}: []")
        elif value is None:
            lines.append(f"{key}:")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n" + doc.body


def load_document(path: Path) -> MarkdownDocument:
    return parse_markdown(path.read_text(encoding="utf-8"))


def write_document(path: Path, doc: MarkdownDocument) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_markdown(doc), encoding="utf-8")


def _parse_frontmatter(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list_key: str | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue

        stripped = raw_line.strip()
        if raw_line.startswith((" ", "\t")):
            if current_list_key is not None and stripped.startswith("- "):
                if not isinstance(data[current_list_key], list):
                    data[current_list_key] = []
                data[current_list_key].append(stripped[2:].strip())
            continue

        current_list_key = None
        if ":" not in raw_line:
            continue

        key, raw_value = raw_line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value == "":
            data[key] = ""
            current_list_key = key
        elif value == "[]":
            data[key] = []
        elif value.startswith("[") and value.endswith("]"):
            data[key] = _parse_inline_list(value)
        else:
            data[key] = value

    return data


def _parse_inline_list(value: str) -> list[str]:
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [item.strip() for item in inner.split(",")]
