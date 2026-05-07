"""Tests for the read-only capability routing tool."""

import json

from tools.capability_router_tool import capability_route
from tools.registry import registry


def _route(request: str, **kwargs):
    return json.loads(capability_route(request, **kwargs))


def _skill_names(payload):
    return {item["name"] for item in payload["recommended_skills"]}


def _toolsets(payload):
    return {item["toolset"] for item in payload["recommended_tools"]}


def test_capability_route_recommends_alpha_workflow_for_design_request():
    payload = _route("새 AlphaCommand 기능을 아이디어 단계부터 설계하고 구현하고 싶습니다")

    assert payload["classification"]["task_type"] in {"design", "code"}
    assert payload["classification"]["risk_level"] in {"L4", "L5", "L6"}
    names = _skill_names(payload)
    assert "tri-tool-ddd-ai-workflow" in names
    assert "writing-plans" in names
    assert "test-driven-development" in names
    assert any("A0" in gate or "아이디어" in gate for gate in payload["approval_gates"] + payload["verification_plan"])
    assert payload["limitations"]
    assert payload["executed"] is False


def test_capability_route_recommends_gh_fix_ci_for_pr_ci_failure():
    payload = _route("GitHub PR CI 실패 원인을 찾아서 고쳐줘")

    names = _skill_names(payload)
    toolsets = _toolsets(payload)
    assert "github-pr-workflow" in names or "github-code-review" in names
    assert "codex-gh-fix-ci" in names
    assert "terminal" in toolsets
    assert any("gh pr checks" in step for step in payload["verification_plan"])
    assert any("approval" in gate.lower() or "승인" in gate for gate in payload["approval_gates"])


def test_capability_route_identifies_mcp_creation_approval_gates():
    payload = _route("새 MCP 서버를 만들어서 Hermes에 연결해줘", candidate_creation=["mcp"])

    assert any(option["type"] == "mcp" for option in payload["creation_options"])
    mcp_option = next(option for option in payload["creation_options"] if option["type"] == "mcp")
    assert mcp_option["allowed_now"] is False
    assert "native-mcp" in _skill_names(payload)
    assert any("restart" in gate.lower() or "재시작" in gate for gate in payload["approval_gates"])
    assert payload["executed"] is False


def test_capability_route_identifies_skill_authoring_path():
    payload = _route("이 반복 작업을 새 Hermes skill로 만들어줘", candidate_creation=["skill"])

    assert "hermes-agent-skill-authoring" in _skill_names(payload)
    assert any(option["type"] == "skill" for option in payload["creation_options"])
    assert any("frontmatter" in step.lower() or "skill" in step.lower() for step in payload["verification_plan"])
    assert payload["executed"] is False


def test_capability_route_is_advisory_and_does_not_claim_execution():
    payload = _route("플러그인을 활성화하고 게이트웨이를 재시작해줘", candidate_creation=["plugin"])

    assert payload["executed"] is False
    assert any("advisory" in item.lower() or "추천" in item for item in payload["limitations"])
    assert any("재시작" in gate or "restart" in gate.lower() for gate in payload["approval_gates"])
    assert any(option["type"] == "plugin" for option in payload["creation_options"])


def test_capability_route_marks_secret_requests_high_risk():
    payload = _route("auth token과 cookie를 읽어서 설정해줘")

    assert payload["classification"]["risk_level"] in {"L5", "L6"}
    assert any("secret" in gate.lower() or "비밀" in gate or "인증" in gate for gate in payload["approval_gates"])
    assert payload["executed"] is False


def test_capability_route_summarizes_plain_request_without_echoing_raw_text():
    request = "새 AlphaCommand 기능을 아이디어 단계부터 설계하고 싶습니다"
    payload = _route(request)

    rendered = json.dumps(payload, ensure_ascii=False)
    assert request not in rendered
    assert payload["request_summary"].startswith("[REQUEST_SUMMARY")
    assert "request" not in payload


def test_capability_route_redacts_secret_like_request_values():
    payload = _route("auth token MY_TOKEN_VALUE_12345 and cookie sessionid=COOKIE_VALUE_67890 설정")

    rendered = json.dumps(payload, ensure_ascii=False)
    assert "MY_TOKEN_VALUE_12345" not in rendered
    assert "COOKIE_VALUE_67890" not in rendered
    assert "[REDACTED_REQUEST_CONTAINS_SECRET_LIKE_TERMS]" in rendered
    assert payload["executed"] is False


def test_capability_route_redacts_api_key_style_request_values():
    payload = _route("use API key sk-ABC...erty to configure provider")

    rendered = json.dumps(payload, ensure_ascii=False)
    assert "sk-ABC...erty" not in rendered
    assert "[REDACTED_REQUEST_CONTAINS_SECRET_LIKE_TERMS]" in rendered
    assert payload["classification"]["risk_level"] in {"L5", "L6"}


def test_capability_route_redacts_common_token_patterns():
    github_like = "gh" + "p_" + "ab" + "..." + "3456"
    bearer_value = "abcdefghijklmnopqrstuvwxyz" + "1234567890"
    slack_like = "xox" + "b-1234567890-abcdefghijklmnopqrstuv"
    sensitive_requests = [
        f"use {github_like} for GitHub",
        "Authorization " + "Bearer " + bearer_value,
        f"slack bot {slack_like} 설정",
    ]

    for request in sensitive_requests:
        payload = _route(request)
        rendered = json.dumps(payload, ensure_ascii=False)
        assert github_like not in rendered
        assert bearer_value not in rendered
        assert slack_like not in rendered
        assert "[REDACTED_REQUEST_CONTAINS_SECRET_LIKE_TERMS]" in rendered
        assert payload["classification"]["risk_level"] in {"L5", "L6"}


def test_capability_route_includes_source_evidence():
    payload = _route("새 MCP 서버를 만들 계획을 세워줘", candidate_creation=["mcp"])

    assert payload["source_evidence"]
    assert any("native-mcp" in item["source"] or "tri-tool" in item["source"] for item in payload["source_evidence"])


def test_capability_route_registers_under_skills_toolset():
    entry = registry.get_entry("capability_route")

    assert entry is not None
    assert entry.toolset == "skills"


def test_capability_route_build_options_mode_keeps_creation_options_but_recommend_hides_them():
    build_payload = _route("새 MCP 서버", mode="build_options", candidate_creation=["mcp"])
    recommend_payload = _route("새 MCP 서버", mode="recommend", candidate_creation=["mcp"])

    assert build_payload["creation_options"]
    assert recommend_payload["creation_options"] == []
    assert recommend_payload["source_evidence"] == []
