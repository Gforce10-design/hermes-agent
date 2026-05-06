"""Deterministic Alpha Workflow task classification primitives."""

from __future__ import annotations

from dataclasses import dataclass

from agent.alpha_workflow_registry import AlphaWorkflowRegistry


@dataclass(frozen=True)
class AlphaWorkflowClassification:
    domain: str
    risk: str
    worker_candidates: tuple[str, ...]
    approval_required: bool
    blocked: bool
    blocked_reason: str
    allowed_next_step: str
    save_surface_required: tuple[str, ...] = ()


def classify_alpha_workflow_task(
    message_text: str,
    registry: AlphaWorkflowRegistry,
) -> AlphaWorkflowClassification:
    """Classify a user request before any Alpha Workflow execution.

    This is intentionally conservative and deterministic. It is not an LLM
    router. Live runtime wiring can layer LLM interpretation on top later, but
    these guardrail cases must stay fail-closed.
    """

    text = message_text.casefold()

    if _mentions_ambiguous_reboot(text):
        return AlphaWorkflowClassification(
            domain="runtime",
            risk="critical",
            worker_candidates=_existing_workers(registry, "hermes_control_tower"),
            approval_required=True,
            blocked=False,
            blocked_reason="Clarify whether this means service restart or system reboot",
            allowed_next_step="ask_clarification",
            save_surface_required=("approval packet",),
        )

    if _mentions_g3_operational_change(text):
        return AlphaWorkflowClassification(
            domain="alphamate",
            risk="critical",
            worker_candidates=_existing_workers(registry, "alphamate_ops_worker"),
            approval_required=True,
            blocked=False,
            blocked_reason="G3 operational action requires approval packet",
            allowed_next_step="approval_packet",
            save_surface_required=("approval packet", "WORKLOG/HANDOFF"),
        )

    if _mentions_wiki_apply(text):
        return AlphaWorkflowClassification(
            domain="alphavaults",
            risk="critical",
            worker_candidates=_existing_workers(registry, "alphavaults_review_worker"),
            approval_required=True,
            blocked=False,
            blocked_reason="wiki apply requires approval packet",
            allowed_next_step="approval_packet",
            save_surface_required=("approval packet", "Obsidian raw/dev"),
        )

    if _mentions_sensitive_admin_change(text):
        return AlphaWorkflowClassification(
            domain="runtime",
            risk="critical",
            worker_candidates=_existing_workers(registry, "hermes_control_tower"),
            approval_required=True,
            blocked=False,
            blocked_reason="DB/secrets/auth change requires approval packet",
            allowed_next_step="approval_packet",
            save_surface_required=("approval packet", "WORKLOG/HANDOFF"),
        )

    if _mentions_openclaw_arbitrary_command(text):
        return AlphaWorkflowClassification(
            domain="runtime",
            risk="medium",
            worker_candidates=_existing_workers(registry, "openclaw_bridge_worker"),
            approval_required=False,
            blocked=False,
            blocked_reason="Hermes-controlled OpenClaw execution is allowed without per-command user approval",
            allowed_next_step="execute",
            save_surface_required=("WORKLOG/HANDOFF", "Obsidian raw/dev"),
        )

    if _mentions_save(text):
        return AlphaWorkflowClassification(
            domain="save_sync",
            risk="medium",
            worker_candidates=_existing_workers(registry, "recorder_save_sync_worker"),
            approval_required=False,
            blocked=False,
            blocked_reason="",
            allowed_next_step="execute",
            save_surface_required=("HANDOFF.md", "WORKLOG.md", "Obsidian raw/dev"),
        )

    if _mentions_alphamate_status(text):
        return AlphaWorkflowClassification(
            domain="alphamate",
            risk="low",
            worker_candidates=_existing_workers(registry, "alphamate_ops_worker"),
            approval_required=False,
            blocked=False,
            blocked_reason="",
            allowed_next_step="execute",
            save_surface_required=("Obsidian raw/dev",),
        )

    return AlphaWorkflowClassification(
        domain="control_tower",
        risk="low",
        worker_candidates=_existing_workers(registry, "hermes_control_tower"),
        approval_required=False,
        blocked=False,
        blocked_reason="",
        allowed_next_step="plan" if _mentions_plan_or_docs(text) else "execute",
        save_surface_required=("Obsidian raw/dev",),
    )


def _existing_workers(registry: AlphaWorkflowRegistry, *worker_ids: str) -> tuple[str, ...]:
    return tuple(worker_id for worker_id in worker_ids if worker_id in registry.workers)


def _mentions_openclaw_arbitrary_command(text: str) -> bool:
    has_openclaw = "openclaw" in text
    has_unrestricted = any(term in text for term in ("아무 명령", "임의 명령", "arbitrary", "unrestricted", "dispatch"))
    has_command = any(term in text for term in ("명령 실행", "command", "execute"))
    return has_openclaw and (has_unrestricted or has_command)


def _mentions_ambiguous_reboot(text: str) -> bool:
    has_target = any(term in text for term in ("서버", "g3", "지삼", "system", "시스템"))
    has_reboot = any(term in text for term in ("다시 켜", "재부팅", "reboot"))
    return has_target and has_reboot


def _mentions_g3_operational_change(text: str) -> bool:
    has_g3_or_alphamate = any(term in text for term in ("g3", "지삼", "alphamate", "dashboard", "doctor"))
    has_operation = any(term in text for term in ("재시작", "restart", "배포", "deploy", "sync", "동기화", "db", "secrets", "secret"))
    return has_g3_or_alphamate and has_operation


def _mentions_wiki_apply(text: str) -> bool:
    has_wiki = "wiki" in text or "위키" in text
    has_apply = any(term in text for term in ("반영", "apply", "바로", "직접"))
    return has_wiki and has_apply


def _mentions_sensitive_admin_change(text: str) -> bool:
    return any(
        term in text
        for term in (
            "db",
            "database",
            "데이터베이스",
            "디비",
            "migration",
            "마이그레이션",
            "secrets",
            "secret",
            "시크릿",
            "키 회전",
            "토큰",
            "auth",
            "인증",
            "권한",
            "credential",
            "authorization",
        )
    )


def _mentions_save(text: str) -> bool:
    return any(term in text for term in ("세이브", "save", "저장"))


def _mentions_alphamate_status(text: str) -> bool:
    return "alphamate" in text and any(term in text for term in ("상태", "status", "확인", "health"))


def _mentions_plan_or_docs(text: str) -> bool:
    return any(term in text for term in ("문서", "계획", "plan", "docs"))
