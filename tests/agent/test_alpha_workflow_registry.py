"""Alpha workflow worker registry loader tests."""

from pathlib import Path

import pytest

from agent.alpha_workflow_registry import (
    AlphaWorkflowRegistryError,
    load_alpha_workflow_registry,
)


VALID_REGISTRY = """
schema_version: "0.1"
artifact: alpha-workflow-worker-registry
status: draft_no_runtime_mutation
status_values: [active, installed, cached, unused, needs-auth, blocked]
global_blocks:
  - unapproved_g3_service_restart
  - arbitrary_openclaw_command
workers:
  hermes_control_tower:
    display_name: "Dr.에르메스 / Control Tower"
    runtime: hermes
    machine: a8
    status: active
    allowed_actions: ["read-only investigation"]
    blocked_actions: ["unapproved production restart/deploy/sync"]
    approval_required_for: ["G3 service restart"]
  openclaw_bridge_worker:
    display_name: "OpenClaw Bridge Worker"
    runtime: openclaw
    machine: a8
    status: active
    allowed_actions: ["read_only_status"]
    blocked_actions: ["arbitrary command", "unrestricted live dispatch"]
    approval_required_for: ["worker trigger execution when contract requires token"]
  alphamate_ops_worker:
    display_name: "AlphaMate Ops / Doctor Worker"
    runtime: alphamate
    machine: g3_or_a8
    status: active
    allowed_actions: ["read-only healthcheck"]
    blocked_actions: ["unapproved service restart"]
    approval_required_for: ["G3 restart"]
  alphavaults_review_worker:
    display_name: "AlphaVaults Review Worker"
    runtime: alphavaults
    machine: mixed
    status: active
    allowed_actions: ["review output write"]
    blocked_actions: ["wiki direct write without approval"]
    approval_required_for: ["wiki apply"]
  recorder_save_sync_worker:
    display_name: "Recorder / Save Sync Worker"
    runtime: hermes_or_claude_or_codex
    machine: mixed
    status: active
    allowed_actions: ["docs-only save"]
    blocked_actions: ["saving secrets"]
    approval_required_for: ["production deploy/restart/sync"]
"""


def write_registry(tmp_path: Path, content: str = VALID_REGISTRY) -> Path:
    path = tmp_path / "alpha-workflow-worker-registry.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_alpha_workflow_registry_returns_typed_workers(tmp_path):
    registry = load_alpha_workflow_registry(write_registry(tmp_path))

    assert registry.schema_version == "0.1"
    assert registry.artifact == "alpha-workflow-worker-registry"
    assert "unapproved_g3_service_restart" in registry.global_blocks
    assert set(registry.workers) == {
        "hermes_control_tower",
        "openclaw_bridge_worker",
        "alphamate_ops_worker",
        "alphavaults_review_worker",
        "recorder_save_sync_worker",
    }
    assert registry.workers["hermes_control_tower"].runtime == "hermes"
    assert registry.workers["openclaw_bridge_worker"].blocked_actions == (
        "arbitrary command",
        "unrestricted live dispatch",
    )


def test_load_alpha_workflow_registry_rejects_invalid_status(tmp_path):
    path = write_registry(tmp_path, VALID_REGISTRY.replace("status: active", "status: live", 1))

    with pytest.raises(AlphaWorkflowRegistryError, match="invalid status"):
        load_alpha_workflow_registry(path)


def test_load_alpha_workflow_registry_rejects_missing_workers(tmp_path):
    path = write_registry(tmp_path, VALID_REGISTRY.replace("workers:", "not_workers:"))

    with pytest.raises(AlphaWorkflowRegistryError, match="workers"):
        load_alpha_workflow_registry(path)


def test_load_alpha_workflow_registry_requires_g3_and_openclaw_global_blocks(tmp_path):
    content = VALID_REGISTRY.replace("  - unapproved_g3_service_restart\n", "")
    path = write_registry(tmp_path, content)

    with pytest.raises(AlphaWorkflowRegistryError, match="global_blocks"):
        load_alpha_workflow_registry(path)


def test_load_alpha_workflow_registry_rejects_secret_like_values(tmp_path):
    content = VALID_REGISTRY + '\nnotes:\n  token: "secret-token-value"\n'
    path = write_registry(tmp_path, content)

    with pytest.raises(AlphaWorkflowRegistryError, match="secret"):
        load_alpha_workflow_registry(path)
