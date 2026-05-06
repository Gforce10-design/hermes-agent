"""Alpha Workflow approval packet generation primitives."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from agent.alpha_workflow_router import AlphaWorkflowClassification

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
DEFAULT_APPROVAL_OPTIONS = [
    "1. 승인하고 실행",
    "2. 보류하고 계획만 저장",
    "3. 수정 요청",
]


class AlphaApprovalPacketError(ValueError):
    """Raised when an approval packet would be unsafe or incomplete."""


def build_approval_packet(
    *,
    classification: AlphaWorkflowClassification,
    action: str,
    target: Mapping[str, Any],
    reason: str,
    proposed_change: Mapping[str, Any],
    rollback: Mapping[str, Any],
    verification: Mapping[str, Any],
    packet_id: str | None = None,
) -> dict[str, Any]:
    """Build a sanitized approval packet for an approval-gated action."""

    if not classification.approval_required:
        raise AlphaApprovalPacketError("classification.approval_required must be true")
    if classification.blocked:
        raise AlphaApprovalPacketError("blocked classification cannot produce an approval packet")
    if classification.allowed_next_step != "approval_packet":
        raise AlphaApprovalPacketError("classification.allowed_next_step must be approval_packet")
    if not action:
        raise AlphaApprovalPacketError("action is required")
    if not reason:
        raise AlphaApprovalPacketError("reason is required")
    _require_mapping(target, "target")
    _require_mapping(proposed_change, "proposed_change")
    _require_mapping(rollback, "rollback")
    _require_mapping(verification, "verification")
    if not rollback.get("steps"):
        raise AlphaApprovalPacketError("rollback steps are required")
    if not verification.get("precheck") or not verification.get("postcheck"):
        raise AlphaApprovalPacketError("verification precheck and postcheck are required")

    payload: dict[str, Any] = {
        "packet_id": packet_id or _default_packet_id(action),
        "requested_by": "Hermes Control Tower",
        "action": action,
        "target": dict(target),
        "reason": reason,
        "classification": {
            "domain": classification.domain,
            "risk": classification.risk,
            "worker_candidates": list(classification.worker_candidates),
            "blocked": classification.blocked,
            "blocked_reason": classification.blocked_reason,
        },
        "proposed_change": dict(proposed_change),
        "risk": {
            "level": classification.risk,
            "approval_required": True,
        },
        "rollback": dict(rollback),
        "verification": dict(verification),
        "approval": {
            "required": True,
            "approver": "CEO",
            "options": list(DEFAULT_APPROVAL_OPTIONS),
        },
    }
    _reject_secret_like_content(payload)
    return payload


def _default_packet_id(action: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_action = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in action.lower()).strip("-")
    return f"alpha-{stamp}-{safe_action or 'approval'}"


def _require_mapping(value: Mapping[str, Any], field_name: str) -> None:
    if not isinstance(value, Mapping) or not value:
        raise AlphaApprovalPacketError(f"{field_name} must be a non-empty mapping")


def _reject_secret_like_content(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            if any(fragment in key_text for fragment in SECRET_KEY_FRAGMENTS):
                raise AlphaApprovalPacketError(f"secret-like key is not allowed in approval packet: {'.'.join(path + (str(key),))}")
            _reject_secret_like_content(child, path + (str(key),))
    elif isinstance(value, str):
        lower_value = value.strip().lower()
        if any(lower_value.startswith(prefix) for prefix in SECRET_VALUE_PREFIXES):
            raise AlphaApprovalPacketError(
                f"secret-like value is not allowed in approval packet: {'.'.join(path)}"
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_like_content(child, path + (str(index),))
