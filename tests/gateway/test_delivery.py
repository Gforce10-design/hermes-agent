"""Tests for the delivery routing module."""

import pytest

from gateway.config import Platform
from gateway.delivery import DeliveryRouter, DeliveryTarget
from gateway.session import SessionSource


class FakeAdapter:
    def __init__(self):
        self.calls = []

    async def send(self, chat_id, content, metadata=None):
        self.calls.append({"chat_id": chat_id, "content": content, "metadata": metadata})
        return {"messageId": "m1"}


class TestParseTargetPlatformChat:
    def test_explicit_telegram_chat(self):
        target = DeliveryTarget.parse("telegram:12345")
        assert target.platform == Platform.TELEGRAM
        assert target.chat_id == "12345"
        assert target.is_explicit is True

    def test_platform_only_no_chat_id(self):
        target = DeliveryTarget.parse("discord")
        assert target.platform == Platform.DISCORD
        assert target.chat_id is None
        assert target.is_explicit is False

    def test_local_target(self):
        target = DeliveryTarget.parse("local")
        assert target.platform == Platform.LOCAL
        assert target.chat_id is None

    def test_origin_with_source(self):
        origin = SessionSource(platform=Platform.TELEGRAM, chat_id="789", thread_id="42")
        target = DeliveryTarget.parse("origin", origin=origin)
        assert target.platform == Platform.TELEGRAM
        assert target.chat_id == "789"
        assert target.thread_id == "42"
        assert target.is_origin is True

    def test_origin_without_source(self):
        target = DeliveryTarget.parse("origin")
        assert target.platform == Platform.LOCAL
        assert target.is_origin is True

    def test_unknown_platform(self):
        target = DeliveryTarget.parse("unknown_platform")
        assert target.platform == Platform.LOCAL


class TestTargetToStringRoundtrip:
    def test_origin_roundtrip(self):
        origin = SessionSource(platform=Platform.TELEGRAM, chat_id="111", thread_id="42")
        target = DeliveryTarget.parse("origin", origin=origin)
        assert target.to_string() == "origin"

    def test_local_roundtrip(self):
        target = DeliveryTarget.parse("local")
        assert target.to_string() == "local"

    def test_platform_only_roundtrip(self):
        target = DeliveryTarget.parse("discord")
        assert target.to_string() == "discord"

    def test_explicit_chat_roundtrip(self):
        target = DeliveryTarget.parse("telegram:999")
        s = target.to_string()
        assert s == "telegram:999"

        reparsed = DeliveryTarget.parse(s)
        assert reparsed.platform == Platform.TELEGRAM
        assert reparsed.chat_id == "999"


class TestDeliveryArbiterHook:
    @pytest.mark.asyncio
    async def test_without_arbiter_metadata_bypasses_hook(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        adapter = FakeAdapter()
        router = DeliveryRouter(config=object(), adapters={Platform.TELEGRAM: adapter})

        result = await router._deliver_to_platform(
            DeliveryTarget.parse("telegram:123"),
            "hello",
            {"job_id": "job-1"},
        )

        assert result == {"messageId": "m1"}
        assert adapter.calls[0]["metadata"]["job_id"] == "job-1"

    @pytest.mark.asyncio
    async def test_governed_metadata_without_routing_file_is_denied(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        adapter = FakeAdapter()
        router = DeliveryRouter(config=object(), adapters={Platform.TELEGRAM: adapter})

        result = await router._deliver_to_platform(
            DeliveryTarget.parse("telegram:123"),
            "hello",
            {"arbiter_topic": "ops", "arbiter_bot_name": "alpha"},
        )

        assert result["skipped"] is True
        assert "not found" in result["reason"]
        assert adapter.calls == []

    @pytest.mark.asyncio
    async def test_governed_metadata_allow_reaches_adapter(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        routing_dir = tmp_path / "config"
        routing_dir.mkdir()
        (routing_dir / "bot-routing.yml").write_text(
            "allow:\n"
            "  - topic: ops\n"
            "    bot: alpha\n",
            encoding="utf-8",
        )
        adapter = FakeAdapter()
        router = DeliveryRouter(config=object(), adapters={Platform.TELEGRAM: adapter})

        result = await router._deliver_to_platform(
            DeliveryTarget.parse("telegram:123"),
            "hello",
            {"arbiter_topic": "ops", "arbiter_bot_name": "alpha"},
        )

        assert result == {"messageId": "m1"}
        assert adapter.calls[0]["metadata"]["arbiter_allowed"] is True


