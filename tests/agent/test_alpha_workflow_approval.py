"""Alpha workflow approval packet tests."""

import pytest

from agent.alpha_workflow_approval import (
    AlphaApprovalPacketError,
    build_approval_packet,
)
from agent.alpha_workflow_router import AlphaWorkflowClassification


def classification(**overrides):
    data = {
        "domain": "alphamate",
        "risk": "critical",
        "worker_candidates": ("alphamate_ops_worker",),
        "approval_required": True,
        "blocked": False,
        "blocked_reason": "G3 operational action requires approval packet",
        "allowed_next_step": "approval_packet",
        "save_surface_required": ("approval packet",),
    }
    data.update(overrides)
    return AlphaWorkflowClassification(**data)


def test_build_approval_packet_requires_approval_and_includes_rollback_and_verification():
    packet = build_approval_packet(
        classification=classification(),
        action="service_restart",
        target={"machine": "g3", "service": "AlphaMate-Dashboard"},
        reason="healthcheck failure after verified diagnosis",
        proposed_change={"summary": "restart service only"},
        rollback={"possible": True, "steps": ["collect logs", "restore previous service state"]},
        verification={"precheck": ["service status"], "postcheck": ["smoke check"]},
    )

    assert packet["approval"]["required"] is True
    assert packet["action"] == "service_restart"
    assert packet["target"]["machine"] == "g3"
    assert packet["rollback"]["steps"]
    assert packet["verification"]["postcheck"] == ["smoke check"]
    assert packet["approval"]["options"] == [
        "1. 승인하고 실행",
        "2. 보류하고 계획만 저장",
        "3. 수정 요청",
    ]


def test_build_approval_packet_rejects_secret_like_target_values():
    with pytest.raises(AlphaApprovalPacketError, match="secret"):
        build_approval_packet(
            classification=classification(),
            action="config_change",
            target={"machine": "a8", "token": "secret-token-value"},
            reason="test",
            proposed_change={"summary": "test"},
            rollback={"possible": True, "steps": ["undo"]},
            verification={"precheck": ["status"], "postcheck": ["status"]},
        )


def test_build_approval_packet_requires_rollback_and_verification():
    with pytest.raises(AlphaApprovalPacketError, match="rollback"):
        build_approval_packet(
            classification=classification(),
            action="deploy",
            target={"machine": "g3"},
            reason="test",
            proposed_change={"summary": "deploy"},
            rollback={},
            verification={"precheck": ["status"], "postcheck": ["status"]},
        )


def test_build_approval_packet_rejects_non_approval_classification():
    with pytest.raises(AlphaApprovalPacketError, match="approval_required"):
        build_approval_packet(
            classification=classification(approval_required=False, risk="low"),
            action="docs_update",
            target={"machine": "a8"},
            reason="test",
            proposed_change={"summary": "docs"},
            rollback={"possible": True, "steps": ["revert docs"]},
            verification={"precheck": ["read"], "postcheck": ["read"]},
        )


def test_build_approval_packet_rejects_blocked_router_classification():
    with pytest.raises(AlphaApprovalPacketError, match="blocked"):
        build_approval_packet(
            classification=classification(blocked=True, allowed_next_step="reject"),
            action="openclaw_command",
            target={"machine": "a8"},
            reason="test",
            proposed_change={"summary": "run unrestricted command"},
            rollback={"possible": True, "steps": ["do not run"]},
            verification={"precheck": ["status"], "postcheck": ["status"]},
        )


def test_build_approval_packet_rejects_secret_like_neutral_values():
    for secret_like_value in ("ghp_exampleplaceholder1234567890", " sk-exampleplaceholder", "Bearer placeholder"):
        with pytest.raises(AlphaApprovalPacketError, match="secret"):
            build_approval_packet(
                classification=classification(),
                action="config_change",
                target={"machine": "a8", "note": secret_like_value},
                reason="test",
                proposed_change={"summary": "test"},
                rollback={"possible": True, "steps": ["undo"]},
                verification={"precheck": ["status"], "postcheck": ["status"]},
            )


def test_build_approval_packet_rejects_expanded_secret_like_keys():
    with pytest.raises(AlphaApprovalPacketError, match="secret"):
        build_approval_packet(
            classification=classification(),
            action="config_change",
            target={"machine": "a8", "authorization_header": "placeholder"},
            reason="test",
            proposed_change={"summary": "test"},
            rollback={"possible": True, "steps": ["undo"]},
            verification={"precheck": ["status"], "postcheck": ["status"]},
        )
