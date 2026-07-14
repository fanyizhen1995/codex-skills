"""Shared deterministic project-global safety signal classification."""

from __future__ import annotations

from collections.abc import Mapping


SECRET_SIGNAL_KEYS = (
    "unsafe_secret",
    "unsafe_secret_detected",
    "secret_detected",
    "secret_exposure_confirmed",
)
GLOBAL_SAFETY_SIGNAL_SUMMARIES = {
    "secret_exposure": "Confirmed secret or credential exposure.",
    "repo_corruption": "repository corruption prevents trustworthy ownership checks",
    "permission_expansion_required": "required permission expansion affects the project",
    "irreversible_operation_required": "irreversible operation requires approval",
    "explicit_global_stop": "explicit global stop requested",
}


def detected_global_safety_signals(run: Mapping[str, object]) -> tuple[str, ...]:
    """Return canonical global stop signals from one trusted run payload."""
    signals = run.get("supervisor_signals")
    nested = signals if isinstance(signals, Mapping) else {}
    detected: list[str] = []
    if any(run.get(key) is True for key in SECRET_SIGNAL_KEYS) or nested.get(
        "unsafe_secret"
    ) is True:
        detected.append("secret_exposure")
    for key in GLOBAL_SAFETY_SIGNAL_SUMMARIES:
        if key == "secret_exposure":
            continue
        if run.get(key) is True or nested.get(key) is True:
            detected.append(key)
    return tuple(detected)
