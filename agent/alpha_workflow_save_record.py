"""Alpha Workflow save/sync record generation primitives."""

from __future__ import annotations

from typing import Any, Mapping

VALID_WORK_TYPES = frozenset({"code", "docs", "ops", "research", "design"})
VALID_REVIEW_GATES = frozenset({"xrev", "docs-light-review", "manual-strict-review"})
REQUIRED_MACHINES = frozenset({"a8", "desktop", "g3"})
SECRET_KEY_FRAGMENTS = (
    "token",
    "secret",
    "api_key",
    "password",
    "passwd",
    "private_key",
    "authorization",
    "credential",
    "credentials",
    "access_key",
    "secret_key",
    "refresh_token",
    "client_secret",
    "bearer",
)
SECRET_VALUE_PREFIXES = ("ghp_", "github_pat_", "sk-", "xoxb-", "xoxp-", "xapp-", "akia", "asia", "bearer ")


class AlphaSaveRecordError(ValueError):
    """Raised when a save/sync record is incomplete or unsafe."""


def build_save_record(
    *,
    task_id: str,
    work_type: str,
    review_gate: str,
    verification: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    branch_state: Mapping[str, Any],
    machine_state: Mapping[str, Any],
    residual_risk: list[str] | None = None,
) -> dict[str, Any]:
    """Build a normalized Alpha Workflow save/sync record."""

    if not task_id:
        raise AlphaSaveRecordError("task_id is required")
    if work_type not in VALID_WORK_TYPES:
        raise AlphaSaveRecordError(f"invalid work_type: {work_type}")
    if review_gate not in VALID_REVIEW_GATES:
        raise AlphaSaveRecordError(f"invalid review_gate: {review_gate}")
    if work_type == "code" and review_gate != "xrev":
        raise AlphaSaveRecordError("code work requires xrev review gate")

    _require_mapping(verification, "verification")
    _require_mapping(artifacts, "artifacts")
    _require_mapping(branch_state, "branch_state")
    _require_mapping(machine_state, "machine_state")

    missing_machines = REQUIRED_MACHINES.difference(machine_state.keys())
    if missing_machines:
        raise AlphaSaveRecordError(f"machine_state missing required machines: {sorted(missing_machines)}")

    if "result" not in verification or "evidence" not in verification:
        raise AlphaSaveRecordError("verification requires result and evidence")

    payload: dict[str, Any] = {
        "task_id": task_id,
        "work_type": work_type,
        "review_gate": review_gate,
        "verification": dict(verification),
        "artifacts": dict(artifacts),
        "branch_state": {
            **dict(branch_state),
            "note": "branch push is not mainline merge",
        },
        "machine_state": dict(machine_state),
        "residual_risk": list(residual_risk or []),
    }
    _reject_secret_like_content(payload)
    return payload


def _require_mapping(value: Mapping[str, Any], field_name: str) -> None:
    if not isinstance(value, Mapping) or not value:
        raise AlphaSaveRecordError(f"{field_name} must be a non-empty mapping")


def _reject_secret_like_content(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            if any(fragment in key_text for fragment in SECRET_KEY_FRAGMENTS):
                raise AlphaSaveRecordError(f"secret-like key is not allowed in save record: {'.'.join(path + (str(key),))}")
            _reject_secret_like_content(child, path + (str(key),))
    elif isinstance(value, str):
        lower_value = value.strip().lower()
        if any(lower_value.startswith(prefix) for prefix in SECRET_VALUE_PREFIXES):
            raise AlphaSaveRecordError(f"secret-like value is not allowed in save record: {'.'.join(path)}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_like_content(child, path + (str(index),))
