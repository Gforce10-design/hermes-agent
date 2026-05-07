"""Read-only capability routing tool.

This tool turns a user request into an advisory packet describing which Hermes
skills, tools, source mirrors, and creation surfaces are relevant. It never
executes the recommended action, mutates config, reads credential stores, or
starts services.
"""

from __future__ import annotations

import json
import re
from typing import Iterable

from hermes_constants import get_hermes_home
from tools.registry import registry

_GITHUB_TOKEN_PREFIX = "gh" + "p_"
_GITHUB_PAT_PREFIX = "github" + "_pat_"
_SLACK_TOKEN_PREFIX = "xox" + "[baprs]-"
_SECRET_RE = re.compile(
    r"secret|token|cookie|credential|password|auth|oauth|api[_ -]?key|\bkey\b|"
    r"sk-[A-Za-z0-9._-]+|"
    + _GITHUB_TOKEN_PREFIX
    + r"[A-Za-z0-9_]+|"
    + _GITHUB_PAT_PREFIX
    + r"[A-Za-z0-9_]+|"
    + r"\bbearer\s+[A-Za-z0-9._-]+|"
    + _SLACK_TOKEN_PREFIX
    + r"[A-Za-z0-9-]+",
    re.I,
)


SOURCE_HINTS = {
    "alpha_workflow": "tri-tool-ddd-ai-workflow/SKILL.md",
    "claude_work": "tri-tool-ddd-ai-workflow/references/source-skills-raw-2026-05-07/claude-codex/claude/claude-windows-root/commands/work.md",
    "codex_gh_fix_ci": "tri-tool-ddd-ai-workflow/references/source-skills-raw-2026-05-07/claude-codex/codex/.../skills/gh-fix-ci/SKILL.md",
    "gstack_office_hours": "tri-tool-ddd-ai-workflow/references/source-skills-raw-2026-05-07/gstack/office-hours/SKILL.md",
    "superpowers_tdd": "tri-tool-ddd-ai-workflow/references/source-skills-raw-2026-05-07/superpowers/test-driven-development/SKILL.md",
    "native_mcp": "mcp/native-mcp/SKILL.md",
    "skill_authoring": "software-development/hermes-agent-skill-authoring/SKILL.md",
}


def _contains_any(text: str, words: Iterable[str]) -> bool:
    low = text.lower()
    return any(word.lower() in low for word in words)


def _skill(name: str, reason: str, source: str = "hermes") -> dict:
    return {"name": name, "source": source, "reason": reason, "load_method": f"skill_view(name='{name}')"}


def _toolset(name: str, reason: str) -> dict:
    return {"toolset": name, "reason": reason}


def _evidence(label: str, source: str) -> dict:
    return {"label": label, "source": source}


def _summarize_request(text: str) -> str:
    if _SECRET_RE.search(text):
        return "[REDACTED_REQUEST_CONTAINS_SECRET_LIKE_TERMS]"
    categories = []
    low = text.lower()
    for label, words in (
        ("design", ["설계", "아이디어", "기능", "구현", "alphacommand", "control tower"]),
        ("debug", ["ci", "github", "checks", "action", "pull request", " pr "]),
        ("tooling", ["mcp", "plugin", "플러그인", "gateway", "게이트웨이", "재시작", "restart"]),
        ("skill", ["skill", "스킬"]),
    ):
        if any(word in low for word in words):
            categories.append(label)
    category_text = ",".join(dict.fromkeys(categories)) or "general"
    return f"[REQUEST_SUMMARY category={category_text} chars={len(text)}]"


def _creation(kind: str, reason: str, approval_gate: str, allowed: bool = False) -> dict:
    return {"type": kind, "reason": reason, "allowed_now": allowed, "approval_gate": approval_gate}


def _classify(request: str) -> dict:
    text = request.lower()
    has_secret = bool(_SECRET_RE.search(request))
    if _contains_any(text, ["ci", "github", "checks", "action", "pull request"]) or " pr " in f" {text} ":
        task_type = "debug"
        risk = "L4"
        difficulty = "normal"
    elif _contains_any(text, ["mcp", "plugin", "플러그인", "gateway", "게이트웨이", "재시작", "restart"]):
        task_type = "tooling"
        risk = "L5" if _contains_any(text, ["재시작", "restart", "auth", "token", "cookie"]) else "L4"
        difficulty = "complex"
    elif _contains_any(text, ["설계", "아이디어", "기능", "구현", "alphacommand", "control tower"]):
        task_type = "design"
        risk = "L6" if _contains_any(text, ["새", "new", "아이디어", "처음"]) else "L4"
        difficulty = "complex"
    else:
        task_type = "question"
        risk = "L5" if has_secret else "L1"
        difficulty = "simple"
    if has_secret:
        risk = "L5"
    return {
        "task_type": task_type,
        "risk_level": risk,
        "difficulty": difficulty,
        "operating_impact": "none in router v1; recommended actions may require approval",
    }


def _build_packet(request: str, mode: str, candidate_creation: list[str] | None, include_sources: bool) -> dict:
    candidate_creation = candidate_creation or []
    classification = _classify(request)
    skills: list[dict] = []
    tools: list[dict] = []
    creations: list[dict] = []
    gates: list[str] = []
    verification: list[str] = []
    evidence: list[dict] = []
    text = request.lower()

    skills.extend([
        _skill("tri-tool-ddd-ai-workflow", "Apply A0-A8 from idea/problem stage through save/release when non-trivial."),
        _skill("sudol-tool-use-discipline", "Compose only the necessary skills/tools and keep approval gates visible."),
    ])
    tools.append(_toolset("skills", "Load relevant skill procedures before acting."))
    gates.append("A0 아이디어/문제정의부터 시작하고, 구현 전 승인 경계를 확인합니다.")
    verification.append("Confirm this route is advisory only; no execution has been performed.")
    if include_sources:
        evidence.append(_evidence("Alpha Workflow", SOURCE_HINTS["alpha_workflow"]))

    if classification["task_type"] == "design":
        skills.extend([
            _skill("writing-plans", "Convert the Light Spec into bite-sized implementation tasks."),
            _skill("test-driven-development", "Require RED/GREEN for new behavior."),
            _skill("subagent-driven-development", "Use grey-box worker contracts after approval when useful."),
        ])
        gates.extend(["A1 도메인/DDD", "A2 Grill Me + Office Hours", "A3 Light Spec", "A4 CEO/Eng plan review"])
        verification.extend(["A0-A4 gate evidence exists before implementation.", "Targeted tests after approval."])
        if include_sources:
            evidence.extend([
                _evidence("gstack Office Hours", SOURCE_HINTS["gstack_office_hours"]),
                _evidence("Superpowers TDD", SOURCE_HINTS["superpowers_tdd"]),
            ])

    if classification["task_type"] == "debug" or _contains_any(text, ["ci", "github", "pr"]):
        skills.extend([
            _skill("github-pr-workflow", "Inspect PR metadata and lifecycle safely."),
            _skill("github-code-review", "Review diffs and findings before fixes."),
            _skill("codex-gh-fix-ci", "Use mirrored Codex gh-fix-ci workflow for GitHub Actions failures.", source="codex-source-mirror"),
        ])
        tools.append(_toolset("terminal", "Run gh auth/status/check/log commands when approved and available."))
        gates.append("Summarize CI root cause and get approval before applying fixes.")
        verification.extend(["gh auth status", "gh pr checks <pr>", "gh run view <run_id> --log"])
        if include_sources:
            evidence.append(_evidence("Codex gh-fix-ci", SOURCE_HINTS["codex_gh_fix_ci"]))

    if _contains_any(text, ["mcp"] ) or "mcp" in candidate_creation:
        skills.append(_skill("native-mcp", "Design or configure MCP servers with explicit config/restart gates."))
        creations.append(_creation("mcp", "A new MCP server can expose a reusable capability surface.", "MCP config write and agent/gateway reload or restart require separate approval."))
        gates.append("MCP activation/config changes and restart/reload are blocked until separately approved.")
        if include_sources:
            evidence.append(_evidence("Native MCP", SOURCE_HINTS["native_mcp"]))

    if _contains_any(text, ["skill", "스킬"]) or "skill" in candidate_creation:
        skills.append(_skill("hermes-agent-skill-authoring", "Author and validate reusable Hermes skills."))
        creations.append(_creation("skill", "A new Hermes skill can preserve a reusable workflow.", "Skill creation/edit requires plan approval and validation."))
        verification.extend(["Validate SKILL.md frontmatter.", "Check skill size and linked files."])
        if include_sources:
            evidence.append(_evidence("Skill authoring", SOURCE_HINTS["skill_authoring"]))

    if _contains_any(text, ["plugin", "플러그인"]) or "plugin" in candidate_creation:
        skills.append(_skill("hermes-agent", "Create or enable Hermes plugins only through config/restart approval gates."))
        creations.append(_creation("plugin", "A plugin can provide new toolsets or hooks.", "Plugin code/config changes and enablement require separate approval."))
        gates.append("Plugin enable/disable and gateway restart are blocked until separately approved.")

    if _contains_any(text, ["cli", "slash", "command", "명령"] ) or "cli" in candidate_creation or "slash_command" in candidate_creation:
        creations.append(_creation("cli", "A CLI or slash command can wrap a repeated workflow.", "Command registry/code changes require approval and tests."))

    if _SECRET_RE.search(request):
        gates.append("비밀값/인증/cookie/token 원문 읽기 또는 저장은 금지되며 별도 보안 승인 없이는 진행하지 않습니다.")
        verification.append("Static secret-safety review before any related code/config change.")

    # De-duplicate while preserving order.
    def dedupe_dicts(items: list[dict], key: str) -> list[dict]:
        seen = set()
        result = []
        for item in items:
            value = item.get(key)
            if value in seen:
                continue
            seen.add(value)
            result.append(item)
        return result

    return {
        "request_summary": _summarize_request(request),
        "mode": mode,
        "mode_behavior": {
            "recommend": "skills/tools/gates 중심 추천",
            "build_options": "candidate_creation 항목 중심 설계 옵션",
            "inspect": "분류와 source evidence 중심 점검",
            "full": "전체 advisory packet",
        }[mode],
        "classification": classification,
        "recommended_skills": dedupe_dicts(skills, "name"),
        "recommended_tools": dedupe_dicts(tools, "toolset"),
        "creation_options": [] if mode == "recommend" else dedupe_dicts(creations, "type"),
        "approval_gates": list(dict.fromkeys(gates)),
        "verification_plan": list(dict.fromkeys(verification)),
        "source_evidence": dedupe_dicts(evidence, "source") if include_sources and mode != "recommend" else [],
        "limitations": [
            "Advisory/추천 only; this tool did not execute, edit, configure, restart, deploy, or send anything.",
            "High-risk actions remain blocked behind explicit approval gates.",
        ],
        "executed": False,
    }


def capability_route(
    request: str,
    mode: str = "full",
    candidate_creation: list[str] | None = None,
    include_sources: bool = True,
    task_id: str | None = None,
) -> str:
    """Return a read-only capability routing packet for *request*."""
    if not request or not request.strip():
        return json.dumps({"error": "request is required", "executed": False}, ensure_ascii=False)
    if mode not in {"recommend", "build_options", "inspect", "full"}:
        return json.dumps({"error": f"unsupported mode: {mode}", "executed": False}, ensure_ascii=False)
    # Touch HERMES_HOME only to keep this profile-aware without reading secrets.
    _ = get_hermes_home()
    packet = _build_packet(request.strip(), mode, candidate_creation, include_sources)
    return json.dumps(packet, ensure_ascii=False)


CAPABILITY_ROUTE_SCHEMA = {
    "name": "capability_route",
    "description": "Read-only router that recommends skills, tools, creation surfaces, approval gates, and verification steps for a user request.",
    "parameters": {
        "type": "object",
        "properties": {
            "request": {"type": "string", "description": "User request to classify and route."},
            "mode": {"type": "string", "enum": ["recommend", "build_options", "inspect", "full"], "default": "full"},
            "candidate_creation": {"type": "array", "description": "Creation surfaces to consider; this never authorizes execution.", "items": {"type": "string", "enum": ["skill", "mcp", "plugin", "cli", "slash_command"]}},
            "include_sources": {"type": "boolean", "default": True},
        },
        "required": ["request"],
    },
}


registry.register(
    name="capability_route",
    toolset="skills",
    schema=CAPABILITY_ROUTE_SCHEMA,
    handler=lambda args, **kwargs: capability_route(
        request=args.get("request", ""),
        mode=args.get("mode", "full"),
        candidate_creation=args.get("candidate_creation", args.get("allowed_creation")),
        include_sources=args.get("include_sources", True),
        task_id=kwargs.get("task_id"),
    ),
    description=CAPABILITY_ROUTE_SCHEMA["description"],
    emoji="🧭",
)
