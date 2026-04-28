"""Tests for Hermes dashboard mobile API endpoints."""

import time
from urllib.parse import urlencode

import pytest


class TestMobileWebSocket:
    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch, _isolate_hermes_home):
        try:
            from starlette.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi/starlette not installed")

        import hermes_cli.web_server as web_server

        self.web_server = web_server
        self.token = web_server._SESSION_TOKEN
        self.client = TestClient(web_server.app)

    def _url(self, token: str | None = None) -> str:
        tok = token if token is not None else self.token
        return f"/api/mobile/ws?{urlencode({'token': tok})}"

    def test_mobile_bootstrap_rejects_anonymous_requests(self):
        resp = self.client.get("/api/mobile/bootstrap")

        assert resp.status_code == 401

    def test_mobile_bootstrap_rejects_spoofable_cloudflare_identity_header(self):
        resp = self.client.get(
            "/api/mobile/bootstrap",
            headers={"CF-Access-Authenticated-User-Email": "user@example.com"},
        )

        assert resp.status_code == 401

    def test_mobile_bootstrap_returns_ws_url_with_valid_access_headers(self, monkeypatch):
        monkeypatch.setenv("HERMES_CLOUDFLARE_ACCESS_CLIENT_ID", "client-id")
        monkeypatch.setenv("HERMES_CLOUDFLARE_ACCESS_CLIENT_SECRET", "client-secret")
        resp = self.client.get(
            "/api/mobile/bootstrap",
            headers={
                "CF-Access-Client-Id": "client-id",
                "CF-Access-Client-Secret": "client-secret",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["mobile_ws_url"].startswith("/api/mobile/ws?token=")

        async def fake_run(prompt: str, session_id: str | None = None) -> dict:
            return {"session_id": "mobile-bootstrap-session", "text": f"응답: {prompt}", "model": "test-model"}

        monkeypatch.setattr(self.web_server, "_run_mobile_prompt", fake_run)

        with self.client.websocket_connect(data["mobile_ws_url"]) as conn:
            conn.send_json({"type": "prompt.submit", "text": "부트스트랩", "client": "flutter"})
            assert conn.receive_json()["type"] == "message.start"
            assert conn.receive_json()["type"] == "message.delta"
            assert conn.receive_json()["type"] == "message.complete"

    def test_mobile_app_update_returns_latest_apk_metadata(self):
        resp = self.client.get("/api/mobile/app-update")

        assert resp.status_code == 200
        data = resp.json()
        assert data["version"]
        assert isinstance(data["build"], int)
        assert data["apk_url"].endswith("/api/mobile/app-release/apk")
        assert "삭제하지 말고" in data["notes"]

    def test_rejects_missing_token(self):
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect) as exc:
            with self.client.websocket_connect("/api/mobile/ws"):
                pass

        assert exc.value.code == 4401

    @pytest.mark.asyncio
    async def test_safe_mobile_send_treats_client_disconnect_as_normal_close(self):
        from starlette.websockets import WebSocketDisconnect

        class DisconnectedWebSocket:
            async def send_json(self, payload):
                raise WebSocketDisconnect(code=1006)

        sent = await self.web_server._safe_send_mobile_json(
            DisconnectedWebSocket(), {"type": "message.delta", "text": "늦은 응답"}
        )

        assert sent is False

    def test_prompt_submit_returns_mobile_event_contract(self, monkeypatch):
        async def fake_run(prompt: str, session_id: str | None = None) -> dict:
            return {
                "session_id": session_id or "mobile-session-1",
                "text": f"응답: {prompt}",
                "model": "test-model",
            }

        monkeypatch.setattr(self.web_server, "_run_mobile_prompt", fake_run)

        with self.client.websocket_connect(self._url()) as conn:
            conn.send_json({"type": "prompt.submit", "text": "안녕", "client": "flutter"})

            started = conn.receive_json()
            delta = conn.receive_json()
            complete = conn.receive_json()

        assert started == {"type": "message.start", "session_id": None}
        assert delta == {"type": "message.delta", "text": "응답: 안녕"}
        assert complete == {
            "type": "message.complete",
            "session_id": "mobile-session-1",
            "text": "응답: 안녕",
            "model": "test-model",
        }

    @pytest.mark.asyncio
    async def test_run_mobile_prompt_uses_codex_primary_and_opus_fallback_config(self, monkeypatch):
        captured = {}

        class FakeAgent:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                self.session_id = kwargs.get("session_id") or "mobile-session"
                self.model = kwargs.get("model") or "test-model"

            def run_conversation(self, prompt):
                return {"final_response": f"응답: {prompt}"}

        import run_agent

        monkeypatch.setattr(run_agent, "AIAgent", FakeAgent)
        monkeypatch.setattr(
            self.web_server,
            "load_config",
            lambda: {
                "model": {"provider": "openai-codex", "default": "gpt-5.5"},
                "fallback_providers": [{"provider": "claude-code", "model": "opus4.7"}],
            },
            raising=False,
        )

        result = await self.web_server._run_mobile_prompt("안녕", session_id="s1")

        assert result["text"] == "응답: 안녕"
        assert captured["provider"] == "openai-codex"
        assert captured["model"] == "gpt-5.5"
        assert captured["fallback_model"] == [{"provider": "claude-code", "model": "opus"}]

    @pytest.mark.asyncio
    async def test_run_mobile_prompt_falls_back_to_opus_when_codex_returns_empty(self, monkeypatch):
        calls = []

        class FakeAgent:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.session_id = kwargs.get("session_id") or "mobile-session"
                self.model = kwargs.get("model") or "test-model"

            def run_conversation(self, prompt):
                calls.append(self.kwargs)
                if self.kwargs.get("provider") == "openai-codex":
                    return {"final_response": ""}
                return {"final_response": "오푸스 응답"}

        import run_agent

        monkeypatch.setattr(run_agent, "AIAgent", FakeAgent)
        monkeypatch.setattr(
            self.web_server,
            "load_config",
            lambda: {
                "model": {"provider": "openai-codex", "default": "gpt-5.5"},
                "fallback_providers": [{"provider": "claude-code", "model": "opus4.7"}],
            },
            raising=False,
        )

        result = await self.web_server._run_mobile_prompt("안녕", session_id="s1")

        assert result["text"] == "오푸스 응답"
        assert [call["provider"] for call in calls] == ["openai-codex", "claude-code"]
        assert calls[1]["model"] == "opus"

    @pytest.mark.asyncio
    async def test_run_mobile_prompt_does_not_start_fallback_while_timed_out_primary_is_running(self, monkeypatch):
        calls = []

        class FakeAgent:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.session_id = kwargs.get("session_id") or "mobile-session"
                self.model = kwargs.get("model") or "test-model"

            def run_conversation(self, prompt):
                calls.append(self.kwargs)
                if self.kwargs.get("provider") == "openai-codex":
                    time.sleep(0.05)
                    return {"final_response": "늦은 응답"}
                return {"final_response": "오푸스 빠른 응답"}

        import run_agent

        monkeypatch.setattr(run_agent, "AIAgent", FakeAgent)
        monkeypatch.setenv("HERMES_MOBILE_PRIMARY_TIMEOUT_SECONDS", "0.01")
        monkeypatch.setattr(
            self.web_server,
            "load_config",
            lambda: {
                "model": {"provider": "openai-codex", "default": "gpt-5.5"},
                "fallback_providers": [{"provider": "claude-code", "model": "opus4.7"}],
            },
            raising=False,
        )

        result = await self.web_server._run_mobile_prompt("안녕", session_id="s1")

        assert result["text"] == "늦은 응답"
        assert [call["provider"] for call in calls] == ["openai-codex"]

    def test_rejects_unknown_message_type_with_error_event(self):
        with self.client.websocket_connect(self._url()) as conn:
            conn.send_json({"type": "unknown"})
            msg = conn.receive_json()

        assert msg["type"] == "error"
        assert "Unsupported mobile message type" in msg["message"]

    def test_prompt_submit_keeps_socket_open_for_followup_prompt(self, monkeypatch):
        calls: list[tuple[str, str | None]] = []

        async def fake_run(prompt: str, session_id: str | None = None) -> dict:
            calls.append((prompt, session_id))
            return {
                "session_id": session_id or "mobile-session-1",
                "text": f"응답: {prompt}",
                "model": "test-model",
            }

        monkeypatch.setattr(self.web_server, "_run_mobile_prompt", fake_run)

        with self.client.websocket_connect(self._url()) as conn:
            conn.send_json({"type": "prompt.submit", "text": "첫 질문", "client": "flutter"})
            assert conn.receive_json()["type"] == "message.start"
            assert conn.receive_json()["type"] == "message.delta"
            first_complete = conn.receive_json()

            conn.send_json({
                "type": "prompt.submit",
                "text": "후속 질문",
                "session_id": first_complete["session_id"],
                "client": "flutter",
            })
            assert conn.receive_json()["type"] == "message.start"
            assert conn.receive_json()["type"] == "message.delta"
            second_complete = conn.receive_json()

        assert calls == [("첫 질문", None), ("후속 질문", "mobile-session-1")]
        assert second_complete["session_id"] == "mobile-session-1"

    def test_prompt_failure_returns_sanitized_error(self, monkeypatch):
        async def fake_run(prompt: str, session_id: str | None = None) -> dict:
            raise RuntimeError("secret provider path /tmp/token.txt")

        monkeypatch.setattr(self.web_server, "_run_mobile_prompt", fake_run)

        with self.client.websocket_connect(self._url()) as conn:
            conn.send_json({"type": "prompt.submit", "text": "실패", "client": "flutter"})
            assert conn.receive_json()["type"] == "message.start"
            msg = conn.receive_json()

        assert msg == {"type": "error", "message": "Mobile prompt failed"}

    def test_prompt_submit_requires_text(self):
        with self.client.websocket_connect(self._url()) as conn:
            conn.send_json({"type": "prompt.submit", "text": ""})
            msg = conn.receive_json()

        assert msg == {"type": "error", "message": "prompt.submit requires non-empty text"}
