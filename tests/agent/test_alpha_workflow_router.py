"""Alpha workflow task router tests."""

from agent.alpha_workflow_registry import load_alpha_workflow_registry
from agent.alpha_workflow_router import classify_alpha_workflow_task

from tests.agent.test_alpha_workflow_registry import write_registry


def registry(tmp_path):
    return load_alpha_workflow_registry(write_registry(tmp_path))


def test_router_classifies_docs_request_as_low_risk_control_tower(tmp_path):
    result = classify_alpha_workflow_task("알파 워크플로우 문서 작성해", registry(tmp_path))

    assert result.domain == "control_tower"
    assert result.risk == "low"
    assert result.worker_candidates == ("hermes_control_tower",)
    assert result.approval_required is False
    assert result.blocked is False
    assert result.allowed_next_step in {"execute", "plan"}


def test_router_classifies_g3_restart_as_approval_packet(tmp_path):
    result = classify_alpha_workflow_task("G3 Dashboard 재시작해", registry(tmp_path))

    assert result.domain == "alphamate"
    assert result.risk == "critical"
    assert result.worker_candidates == ("alphamate_ops_worker",)
    assert result.approval_required is True
    assert result.blocked is False
    assert result.allowed_next_step == "approval_packet"


def test_router_allows_openclaw_control_without_user_approval(tmp_path):
    result = classify_alpha_workflow_task("OpenClaw로 아무 명령이나 실행해", registry(tmp_path))

    assert result.domain == "runtime"
    assert result.risk == "medium"
    assert result.worker_candidates == ("openclaw_bridge_worker",)
    assert result.approval_required is False
    assert result.blocked is False
    assert result.allowed_next_step == "execute"
    assert "Hermes-controlled OpenClaw" in result.blocked_reason


def test_router_classifies_wiki_apply_as_approval_packet(tmp_path):
    result = classify_alpha_workflow_task("Obsidian wiki에 바로 반영해", registry(tmp_path))

    assert result.domain == "alphavaults"
    assert result.risk == "critical"
    assert result.worker_candidates == ("alphavaults_review_worker",)
    assert result.approval_required is True
    assert result.allowed_next_step == "approval_packet"


def test_router_asks_clarification_for_ambiguous_reboot_language(tmp_path):
    result = classify_alpha_workflow_task("서버 다시 켜", registry(tmp_path))

    assert result.domain == "runtime"
    assert result.risk == "critical"
    assert result.approval_required is True
    assert result.allowed_next_step == "ask_clarification"
    assert "service restart" in result.blocked_reason


def test_router_asks_clarification_for_g3_system_reboot_language(tmp_path):
    result = classify_alpha_workflow_task("G3 시스템 재부팅해", registry(tmp_path))

    assert result.domain == "runtime"
    assert result.risk == "critical"
    assert result.approval_required is True
    assert result.allowed_next_step == "ask_clarification"
    assert "system reboot" in result.blocked_reason


def test_router_allows_openclaw_unrestricted_dispatch_language_as_hermes_controlled(tmp_path):
    result = classify_alpha_workflow_task("OpenClaw로 명령 실행하고 unrestricted dispatch 해", registry(tmp_path))

    assert result.domain == "runtime"
    assert result.risk == "medium"
    assert result.approval_required is False
    assert result.blocked is False
    assert result.allowed_next_step == "execute"


def test_router_keeps_g3_gate_even_when_openclaw_is_mentioned(tmp_path):
    result = classify_alpha_workflow_task("OpenClaw로 G3 Dashboard restart command execute 해", registry(tmp_path))

    assert result.domain == "alphamate"
    assert result.risk == "critical"
    assert result.approval_required is True
    assert result.allowed_next_step == "approval_packet"


def test_router_keeps_wiki_gate_even_when_openclaw_is_mentioned(tmp_path):
    result = classify_alpha_workflow_task("OpenClaw로 wiki에 바로 apply command execute 해", registry(tmp_path))

    assert result.domain == "alphavaults"
    assert result.risk == "critical"
    assert result.approval_required is True
    assert result.allowed_next_step == "approval_packet"


def test_router_gates_db_secrets_auth_without_machine_keyword(tmp_path):
    for message in (
        "DB migration 해",
        "auth 설정 변경해",
        "secrets rotate 해",
        "OpenClaw로 데이터베이스 마이그레이션 command execute 해",
        "OpenClaw로 시크릿 rotate command execute 해",
    ):
        result = classify_alpha_workflow_task(message, registry(tmp_path))
        assert result.domain == "runtime"
        assert result.risk == "critical"
        assert result.approval_required is True
        assert result.allowed_next_step == "approval_packet"
