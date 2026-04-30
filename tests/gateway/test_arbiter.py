from gateway.arbiter import RoutingCache, arbitrate_send, is_governed_metadata


def test_metadata_without_topic_or_bot_is_not_governed():
    assert not is_governed_metadata({})
    assert not is_governed_metadata({"arbiter_topic": "ops"})
    assert is_governed_metadata({"arbiter_topic": "ops", "arbiter_bot_name": "alpha"})


def test_missing_routing_file_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    decision = arbitrate_send(
        metadata={"arbiter_topic": "ops", "arbiter_bot_name": "alpha"},
        target="telegram:1",
        content="hello",
        cache=RoutingCache(tmp_path / "missing.yml"),
    )

    assert decision.governed
    assert not decision.allowed
    assert decision.status == "denied"
    assert "not found" in decision.reason


def test_explicit_deny_blocks_send(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    routing = tmp_path / "bot-routing.yml"
    routing.write_text(
        "deny:\n"
        "  - name: block-alpha-ops\n"
        "    topic: ops\n"
        "    bot: alpha\n"
        "    reason: blocked for test\n",
        encoding="utf-8",
    )

    decision = arbitrate_send(
        metadata={"arbiter_topic": "ops", "arbiter_bot_name": "alpha"},
        target="telegram:1",
        content="hello",
        cache=RoutingCache(routing),
    )

    assert not decision.allowed
    assert decision.reason == "blocked for test"
    assert decision.matched_rule == "block-alpha-ops"


def test_global_deny_patterns_block_matching_content(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    routing = tmp_path / "bot-routing.yml"
    routing.write_text(
        "global_deny:\n"
        "  - name: destructive-shell\n"
        "    topic: \"*\"\n"
        "    patterns:\n"
        "      - git reset --hard\n"
        "      - ssh.*g3\n"
        "    reason: destructive command\n"
        "allow:\n"
        "  - name: allow-alpha-ops\n"
        "    topic: ops\n"
        "    bot: alpha\n",
        encoding="utf-8",
    )

    decision = arbitrate_send(
        metadata={"arbiter_topic": "ops", "arbiter_bot_name": "alpha"},
        target="telegram:1",
        content="please run ssh prod-g3 and git reset --hard now",
        cache=RoutingCache(routing),
    )

    assert not decision.allowed
    assert decision.reason == "destructive command"
    assert decision.matched_rule == "destructive-shell"


def test_policy_action_does_not_prevent_global_deny_pattern(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    routing = tmp_path / "bot-routing.yml"
    routing.write_text(
        "global_deny:\n"
        "  - name: destructive-shell\n"
        "    topic: \"*\"\n"
        "    patterns:\n"
        "      - git reset --hard\n"
        "    action: deny_and_alert\n"
        "    reason: destructive command\n"
        "allow:\n"
        "  - name: allow-alpha-ops\n"
        "    topic: ops\n"
        "    bot: alpha\n"
        "    action: send\n",
        encoding="utf-8",
    )

    decision = arbitrate_send(
        metadata={"arbiter_topic": "ops", "arbiter_bot_name": "alpha"},
        target="telegram:1",
        content="please run git reset --hard now",
        cache=RoutingCache(routing),
    )

    assert not decision.allowed
    assert decision.matched_rule == "destructive-shell"


def test_governed_send_without_allow_rules_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    routing = tmp_path / "bot-routing.yml"
    routing.write_text("topics:\n  ops: {}\n", encoding="utf-8")

    decision = arbitrate_send(
        metadata={"arbiter_topic": "ops", "arbiter_bot_name": "alpha"},
        target="telegram:1",
        content="hello",
        cache=RoutingCache(routing),
    )

    assert decision.governed
    assert not decision.allowed
    assert decision.status == "denied"
    assert decision.reason == "no allow rules configured"


def test_allow_rule_permits_send_and_records_idempotency(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    routing = tmp_path / "bot-routing.yml"
    routing.write_text(
        "allow:\n"
        "  - name: allow-alpha-ops\n"
        "    topic: ops\n"
        "    bot: alpha\n",
        encoding="utf-8",
    )
    metadata = {
        "arbiter_topic": "ops",
        "arbiter_bot_name": "alpha",
        "arbiter_trace_id": "trace-1",
        "arbiter_idempotency_key": "idem-1",
    }

    first = arbitrate_send(
        metadata=metadata,
        target="telegram:1",
        content="hello",
        cache=RoutingCache(routing),
    )
    second = arbitrate_send(
        metadata=metadata,
        target="telegram:1",
        content="hello again",
        cache=RoutingCache(routing),
    )

    assert first.allowed
    assert first.to_metadata()["arbiter_allowed"] is True
    assert not second.allowed
    assert second.reason == "duplicate idempotency key"
