"""Read-only Alpha Workflow worker registry loader.

This module is intentionally side-effect free. It validates a YAML contract and
returns typed records that future router/approval code can use without treating
cached files or broad runtime claims as executable authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

VALID_STATUS = frozenset({"active", "installed", "cached", "unused", "needs-auth", "blocked"})
REQUIRED_GLOBAL_BLOCKS = frozenset(
    {
        "unapproved_g3_service_restart",
        "arbitrary_openclaw_command",
    }
)
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


class AlphaWorkflowRegistryError(ValueError):
    """Raised when the Alpha Workflow worker registry contract is invalid."""


@dataclass(frozen=True)
class AlphaWorker:
    worker_id: str
    display_name: str
    runtime: str
    machine: str
    status: str
    allowed_actions: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    approval_required_for: tuple[str, ...]


@dataclass(frozen=True)
class AlphaWorkflowRegistry:
    schema_version: str
    artifact: str
    status: str
    workers: dict[str, AlphaWorker]
    global_blocks: tuple[str, ...]


def load_alpha_workflow_registry(path: str | Path) -> AlphaWorkflowRegistry:
    """Load and validate an Alpha Workflow worker registry YAML file."""

    registry_path = Path(path)
    try:
        raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AlphaWorkflowRegistryError(f"invalid YAML: {exc}") from exc
    except OSError as exc:
        raise AlphaWorkflowRegistryError(f"cannot read registry: {exc}") from exc

    if not isinstance(raw, Mapping):
        raise AlphaWorkflowRegistryError("registry root must be a mapping")

    _reject_secret_like_keys(raw)
    _validate_status_values(raw)
    global_blocks = _validate_global_blocks(raw)
    workers = _validate_workers(raw)

    return AlphaWorkflowRegistry(
        schema_version=_required_str(raw, "schema_version"),
        artifact=_required_str(raw, "artifact"),
        status=_required_str(raw, "status"),
        workers=workers,
        global_blocks=tuple(global_blocks),
    )


def _validate_status_values(raw: Mapping[str, Any]) -> None:
    values = raw.get("status_values")
    if not isinstance(values, list):
        raise AlphaWorkflowRegistryError("status_values must be a list")
    missing = VALID_STATUS.difference(str(value) for value in values)
    if missing:
        raise AlphaWorkflowRegistryError(f"status_values missing canonical statuses: {sorted(missing)}")


def _validate_global_blocks(raw: Mapping[str, Any]) -> list[str]:
    blocks = raw.get("global_blocks")
    if not isinstance(blocks, list) or not blocks:
        raise AlphaWorkflowRegistryError("global_blocks must be a non-empty list")
    block_values = [str(block) for block in blocks]
    missing = REQUIRED_GLOBAL_BLOCKS.difference(block_values)
    if missing:
        raise AlphaWorkflowRegistryError(f"global_blocks missing required entries: {sorted(missing)}")
    return block_values


def _validate_workers(raw: Mapping[str, Any]) -> dict[str, AlphaWorker]:
    workers_raw = raw.get("workers")
    if not isinstance(workers_raw, Mapping) or not workers_raw:
        raise AlphaWorkflowRegistryError("workers must be a non-empty mapping")

    workers: dict[str, AlphaWorker] = {}
    for worker_id, data in workers_raw.items():
        if not isinstance(worker_id, str) or not worker_id:
            raise AlphaWorkflowRegistryError("worker id must be a non-empty string")
        if not isinstance(data, Mapping):
            raise AlphaWorkflowRegistryError(f"worker {worker_id} must be a mapping")

        status = _required_str(data, "status", worker_id=worker_id)
        if status not in VALID_STATUS:
            raise AlphaWorkflowRegistryError(f"worker {worker_id} has invalid status: {status}")

        workers[worker_id] = AlphaWorker(
            worker_id=worker_id,
            display_name=_required_str(data, "display_name", worker_id=worker_id),
            runtime=_required_str(data, "runtime", worker_id=worker_id),
            machine=_required_str(data, "machine", worker_id=worker_id),
            status=status,
            allowed_actions=_required_str_tuple(data, "allowed_actions", worker_id),
            blocked_actions=_required_str_tuple(data, "blocked_actions", worker_id),
            approval_required_for=_required_str_tuple(data, "approval_required_for", worker_id),
        )

    openclaw = workers.get("openclaw_bridge_worker")
    if openclaw and "arbitrary command" not in openclaw.blocked_actions:
        raise AlphaWorkflowRegistryError("openclaw_bridge_worker must block arbitrary command")
    return workers


def _required_str(data: Mapping[str, Any], key: str, *, worker_id: str | None = None) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        subject = f"worker {worker_id}" if worker_id else "registry"
        raise AlphaWorkflowRegistryError(f"{subject} missing required string field: {key}")
    return value


def _required_str_tuple(data: Mapping[str, Any], key: str, worker_id: str) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise AlphaWorkflowRegistryError(f"worker {worker_id} missing required string list field: {key}")
    return tuple(value)


def _reject_secret_like_keys(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            if any(fragment in key_text for fragment in SECRET_KEY_FRAGMENTS):
                raise AlphaWorkflowRegistryError(f"secret-like key is not allowed in registry: {'.'.join(path + (str(key),))}")
            _reject_secret_like_keys(child, path + (str(key),))
    elif isinstance(value, str):
        lower_value = value.strip().lower()
        if any(lower_value.startswith(prefix) for prefix in SECRET_VALUE_PREFIXES):
            raise AlphaWorkflowRegistryError(f"secret-like value is not allowed in registry: {'.'.join(path)}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_like_keys(child, path + (str(index),))
