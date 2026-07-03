from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AgentSummary:
    name: str
    status: str
    attempt: int
    current_action: str
    last_result: str
    artifact_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FlowNode:
    id: str
    label: str
    status: str
    current_action: str = ""
    recent_result: str = ""
    artifact_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LogEntry:
    source: str
    stream: str
    content: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Event:
    kind: str
    source: str
    message: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
