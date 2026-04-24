import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from gateway.arbiter import Decision, RoutingCache, arbitrate_receive, arbitrate_send
from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.delivery import DeliveryRouter, DeliveryTarget


SAMPLE_ROUTING_YAML = """
version: 1
topics:
  dev-command:
    primary: HermesA8_bot
    failover: [AHC_A8_bot]
    notify_only: []
    enabled: true
  invest-command:
    primary: AlphaMate_Alpha_No_1
    failover: [AlphaMate_Alpha_No_2]
    notify_only: []
    enabled: true
  content-publish:
    primary: AHC_A8_bot
    failover: []
    notify_only: []
    enabled: false
inbound_classification:
  by_command_prefix:
    "/work": dev-command
    "/alpha": invest-command
  by_bot_token_hint:
    HermesA8_bot: dev-command
    AHC_A8_bot: dev-command
  default_fallback: dev-command
global_deny:
  - name: destructive_shell
    topic: "*"
    patterns: ["rm -rf /", "DROP TABLE"]
    action: deny_and_alert
    reason: "shell destructive"
  - name: trading_live
    topic: invest-command
    patterns: ["주문실행", "execute_order"]
    action: require_human_confirmation
    reason: "live trade"
idempotency:
  action_hash_ttl_seconds: 3600
"""


@pytest.fixture
def routing_file(tmp_path):
    p = tmp_path / "bot-routing.yml"
    p.write_text(SAMPLE_ROUTING_YAML, encoding="utf-8")
    return p


@pytest.fixture
def db_file(tmp_path):
    return tmp_path / "idempotency.db"


@pytest.fixture
def heartbeat_dir(tmp_path):
    d = tmp_path / "heartbeat"
    d.mkdir()
    return d


@pytest.fixture
def cache(routing_file):
    return RoutingCache(routing_file)


def test_primary_allowed_dev_command(cache, db_file, heartbeat_dir):
    d = arbitrate_send(
        "HermesA8_bot",
        "dev-command",
        {"type": "shell", "payload": "ls"},
        routing_cache=cache,
        idempotency_db=db_file,
        heartbeat_dir=heartbeat_dir,
        trace_id="t1",
    )
    assert d.allow is True
    assert d.reason == "ok"


def test_unauthorized_bot_denied(cache, db_file, heartbeat_dir):
    d = arbitrate_send(
        "AlphaMate_Alpha_No_1",
        "dev-command",
        {"type": "shell", "payload": "ls"},
        routing_cache=cache,
        idempotency_db=db_file,
        heartbeat_dir=heartbeat_dir,
        trace_id="t2",
    )
    assert d.allow is False
    assert d.reason == "bot_not_authorized_for_topic"
    assert d.alert_slack is True


def test_trading_requires_human(cache, db_file, heartbeat_dir):
    d = arbitrate_send(
        "AlphaMate_Alpha_No_1",
        "invest-command",
        {"type": "command", "payload": "주문실행 005930 10주"},
        routing_cache=cache,
        idempotency_db=db_file,
        heartbeat_dir=heartbeat_dir,
        trace_id="t3",
    )
    assert d.allow is False
    assert d.reason == "global_deny:trading_live"
    assert d.require_human_confirmation is True


def test_destructive_shell_blocked(cache, db_file, heartbeat_dir):
    d = arbitrate_send(
        "HermesA8_bot",
        "dev-command",
        {"type": "shell", "payload": "rm -rf /tmp && rm -rf /"},
        routing_cache=cache,
        idempotency_db=db_file,
        heartbeat_dir=heartbeat_dir,
        trace_id="t4",
    )
    assert d.allow is False
    assert d.reason == "global_deny:destructive_shell"
    assert d.alert_slack is True
    assert d.alert_telegram is True


def test_idempotency_duplicate(cache, db_file, heartbeat_dir):
    action = {"type": "shell", "payload": "uptime"}
    d1 = arbitrate_send(
        "HermesA8_bot", "dev-command", action,
        routing_cache=cache, idempotency_db=db_file, heartbeat_dir=heartbeat_dir, trace_id="t5a"
    )
    d2 = arbitrate_send(
        "HermesA8_bot", "dev-command", action,
        routing_cache=cache, idempotency_db=db_file, heartbeat_dir=heartbeat_dir, trace_id="t5b"
    )
    assert d1.allow is True
    assert d2.allow is False
    assert d2.reason == "duplicate_action_denied_by_idempotency"


def test_ttl_expiry_allows(cache, db_file, heartbeat_dir):
    action = {"type": "shell", "payload": "date"}
    d1 = arbitrate_send(
        "HermesA8_bot", "dev-command", action,
        routing_cache=cache, idempotency_db=db_file, heartbeat_dir=heartbeat_dir, trace_id="t6a"
    )
    with sqlite3.connect(db_file) as db:
        db.execute("UPDATE seen SET first_seen = first_seen - 7200")
        db.commit()
    d2 = arbitrate_send(
        "HermesA8_bot", "dev-command", action,
        routing_cache=cache, idempotency_db=db_file, heartbeat_dir=heartbeat_dir, trace_id="t6b"
    )
    assert d1.allow is True
    assert d2.allow is True


def test_unknown_topic(cache, db_file, heartbeat_dir):
    d = arbitrate_send(
        "HermesA8_bot", "nonexistent-topic", {"type": "msg", "payload": "hi"},
        routing_cache=cache, idempotency_db=db_file, heartbeat_dir=heartbeat_dir, trace_id="t7"
    )
    assert d.allow is False
    assert d.reason == "unknown_topic"
    assert d.alert_slack is True


def test_primary_alive_failover_denied(cache, db_file, heartbeat_dir):
    (heartbeat_dir / "HermesA8_bot.ts").write_text("alive", encoding="utf-8")
    d = arbitrate_send(
        "AHC_A8_bot", "dev-command", {"type": "msg", "payload": "take over"},
        routing_cache=cache, idempotency_db=db_file, heartbeat_dir=heartbeat_dir, trace_id="t8"
    )
    assert d.allow is False
    assert d.reason == "primary_alive_failover_denied"
    assert d.fallback_bot == "HermesA8_bot"


def test_yaml_parse_failure_minimal_mode(tmp_path, db_file, heartbeat_dir):
    bad = tmp_path / "bot-routing.yml"
    bad.write_text("version: 1\ntopics: {broken: [", encoding="utf-8")
    cache = RoutingCache(bad)
    d = arbitrate_send(
        "HermesA8_bot", "dev-command", {"type": "msg", "payload": "x"},
        routing_cache=cache, idempotency_db=db_file, heartbeat_dir=heartbeat_dir, trace_id="t9"
    )
    assert d.allow is False
    assert d.reason == "arbiter_yaml_unavailable"
    assert d.alert_telegram is True


def test_topic_disabled_denied(cache, db_file, heartbeat_dir):
    d = arbitrate_send(
        "AHC_A8_bot", "content-publish", {"type": "msg", "payload": "draft ready"},
        routing_cache=cache, idempotency_db=db_file, heartbeat_dir=heartbeat_dir, trace_id="t10"
    )
    assert d.allow is False
    assert d.reason == "topic_disabled"


def test_inbound_command_prefix(cache):
    t = arbitrate_receive("AlphaMate_Alpha_No_1", {"text": "/alpha 현재가 삼성전자"}, routing_cache=cache)
    assert t == "invest-command"


def test_inbound_default_fallback(cache):
    t = arbitrate_receive("HermesA8_bot", {"text": "오늘 어때"}, routing_cache=cache)
    assert t == "dev-command"


@pytest.mark.asyncio
async def test_delivery_router_bypasses_without_arbiter_metadata(tmp_path):
    cfg = GatewayConfig(platforms={})
    adapter = AsyncMock()
    adapter.send = AsyncMock(return_value={"ok": True})
    router = DeliveryRouter(cfg, adapters={Platform.TELEGRAM: adapter})
    target = DeliveryTarget(platform=Platform.TELEGRAM, chat_id="123")

    await router._deliver_to_platform(target, "hello", metadata={"thread_id": "42"})

    adapter.send.assert_awaited_once()
    assert adapter.send.await_args.kwargs["metadata"] == {"thread_id": "42"}


@pytest.mark.asyncio
async def test_delivery_router_denies_when_arbiter_blocks(routing_file, db_file, heartbeat_dir):
    cfg = GatewayConfig(platforms={})
    adapter = AsyncMock()
    adapter.send = AsyncMock(return_value={"ok": True})
    router = DeliveryRouter(cfg, adapters={Platform.TELEGRAM: adapter})
    target = DeliveryTarget(platform=Platform.TELEGRAM, chat_id="123")

    metadata = {
        "arbiter_topic": "dev-command",
        "arbiter_bot_name": "HermesA8_bot",
        "arbiter_action": {"type": "shell", "payload": "rm -rf /"},
        "arbiter_routing_yml": str(routing_file),
        "arbiter_idempotency_db": str(db_file),
        "arbiter_heartbeat_dir": str(heartbeat_dir),
    }

    result = await router._deliver_to_platform(target, "blocked", metadata=metadata)

    adapter.send.assert_not_awaited()
    assert result["arbiter"] is True
    assert result["decision"]["allow"] is False
    assert result["decision"]["reason"] == "global_deny:destructive_shell"


@pytest.mark.asyncio
async def test_delivery_router_allows_opt_in_metadata(routing_file, db_file, heartbeat_dir):
    cfg = GatewayConfig(platforms={})
    adapter = AsyncMock()
    adapter.send = AsyncMock(return_value={"ok": True})
    router = DeliveryRouter(cfg, adapters={Platform.TELEGRAM: adapter})
    target = DeliveryTarget(platform=Platform.TELEGRAM, chat_id="123")

    metadata = {
        "arbiter_topic": "dev-command",
        "arbiter_bot_name": "HermesA8_bot",
        "arbiter_action": {"type": "message", "payload": "hello"},
        "arbiter_routing_yml": str(routing_file),
        "arbiter_idempotency_db": str(db_file),
        "arbiter_heartbeat_dir": str(heartbeat_dir),
    }

    await router._deliver_to_platform(target, "hello", metadata=metadata)

    adapter.send.assert_awaited_once()
    sent_meta = adapter.send.await_args.kwargs["metadata"]
    assert sent_meta["arbiter_trace_id"]
    assert sent_meta["arbiter_decision_reason"] == "ok"



# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# TelegramAdapter gate (adapter-level wiring) --------------------------------
# ---------------------------------------------------------------------------

from gateway.config import Platform as _Platform
from gateway.platforms.base import SendResult
from gateway.platforms.telegram import TelegramAdapter


def _make_unbound_adapter():
    adapter = TelegramAdapter.__new__(TelegramAdapter)
    adapter.platform = _Platform.TELEGRAM  # name property reads self.platform.value.title()
    return adapter


def test_adapter_gate_noop_without_arbiter_metadata():
    adapter = _make_unbound_adapter()

    meta, gate = adapter._apply_arbiter_gate(
        surface="send_image_file", content="hi", metadata=None
    )
    assert meta is None and gate is None

    meta, gate = adapter._apply_arbiter_gate(
        surface="send_image_file", content="hi", metadata={"thread_id": "42"}
    )
    assert meta == {"thread_id": "42"}
    assert gate is None


def test_adapter_gate_allows_and_stamps_trace(
    routing_file, db_file, heartbeat_dir
):
    adapter = _make_unbound_adapter()

    meta, gate = adapter._apply_arbiter_gate(
        surface="send_image_file",
        content="image:/tmp/foo.png",
        metadata={
            "arbiter_topic": "dev-command",
            "arbiter_bot_name": "HermesA8_bot",
            "arbiter_action": {"type": "message", "payload": "image:/tmp/foo.png"},
            "arbiter_routing_yml": str(routing_file),
            "arbiter_idempotency_db": str(db_file),
            "arbiter_heartbeat_dir": str(heartbeat_dir),
        },
    )

    assert gate is None
    assert meta is not None
    assert meta["arbiter_decision_reason"] == "ok"
    assert meta["arbiter_trace_id"]


def test_adapter_gate_denies_on_global_deny(
    routing_file, db_file, heartbeat_dir
):
    adapter = _make_unbound_adapter()

    meta, gate = adapter._apply_arbiter_gate(
        surface="send_exec_approval",
        content="exec_approval:rm -rf /",
        metadata={
            "arbiter_topic": "dev-command",
            "arbiter_bot_name": "HermesA8_bot",
            "arbiter_action": {"type": "shell", "payload": "rm -rf /"},
            "arbiter_routing_yml": str(routing_file),
            "arbiter_idempotency_db": str(db_file),
            "arbiter_heartbeat_dir": str(heartbeat_dir),
        },
    )

    assert isinstance(gate, SendResult)
    assert gate.success is False
    assert gate.error.startswith("arbiter_denied:global_deny:")
    assert meta is not None
    assert meta["arbiter_decision_reason"].startswith("global_deny:")
