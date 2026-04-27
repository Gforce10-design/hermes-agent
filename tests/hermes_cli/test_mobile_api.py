"""Tests for Hermes dashboard mobile API endpoints."""

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

    def test_rejects_missing_token(self):
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect) as exc:
            with self.client.websocket_connect("/api/mobile/ws"):
                pass

        assert exc.value.code == 4401

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
