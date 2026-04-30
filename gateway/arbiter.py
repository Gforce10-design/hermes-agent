"""Delivery-time arbitration for opt-in OpenClaw bridge sends."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from hermes_cli.config import get_hermes_home

try:
    import yaml
except ImportError:  # pragma: no cover - optional in minimal installs
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

TOPIC_KEY = "arbiter_topic"
BOT_KEY = "arbiter_bot_name"
ACTION_KEY = "arbiter_action_type"
TRACE_KEY = "arbiter_trace_id"
IDEMPOTENCY_KEY = "arbiter_idempotency_key"

POLICY_ACTIONS = {
    "allow",
    "deny",
    "deny_and_alert",
    "require_human_confirmation",
    "review",
    "blocked",
}


@dataclass(frozen=True)
class Decision:
    """Result of an arbiter decision."""

    governed: bool
    allowed: bool
    reason: str
    status: str
    source: str = "bypass"
    trace_id: str | None = None
    idempotency_key: str | None = None
    matched_rule: str | None = None

    def to_metadata(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "arbiter_governed": self.governed,
            "arbiter_allowed": self.allowed,
            "arbiter_status": self.status,
            "arbiter_reason": self.reason,
            "arbiter_source": self.source,
        }
        if self.trace_id:
            data[TRACE_KEY] = self.trace_id
        if self.idempotency_key:
            data[IDEMPOTENCY_KEY] = self.idempotency_key
        if self.matched_rule:
            data["arbiter_matched_rule"] = self.matched_rule
        return data


class RoutingCache:
    """Small mtime-aware loader for bot-routing.yml."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_routing_path()
        self._mtime_ns: int | None = None
        self._data: dict[str, Any] | None = None
        self._error: str | None = None

    def load(self) -> tuple[dict[str, Any] | None, str | None]:
        if not self.path.exists():
            self._mtime_ns = None
            self._data = None
            self._error = f"routing file not found: {self.path}"
            return None, self._error

        stat = self.path.stat()
        if self._data is not None and self._mtime_ns == stat.st_mtime_ns:
            return self._data, self._error

        try:
            raw = self.path.read_text(encoding="utf-8")
            if yaml is None:
                data = json.loads(raw)
            else:
                data = yaml.safe_load(raw) or {}
            if not isinstance(data, dict):
                raise ValueError("routing file root must be a mapping")
        except Exception as exc:  # pragma: no cover - exact parser errors vary
            self._mtime_ns = stat.st_mtime_ns
            self._data = None
            self._error = f"could not parse routing file: {exc}"
            return None, self._error

        self._mtime_ns = stat.st_mtime_ns
        self._data = data
        self._error = None
        return data, None


_DEFAULT_CACHE: RoutingCache | None = None


def default_routing_path() -> Path:
    return get_hermes_home() / "config" / "bot-routing.yml"


def _cache() -> RoutingCache:
    global _DEFAULT_CACHE
    path = default_routing_path()
    if _DEFAULT_CACHE is None or _DEFAULT_CACHE.path != path:
        _DEFAULT_CACHE = RoutingCache(path)
    return _DEFAULT_CACHE


def is_governed_metadata(metadata: Mapping[str, Any] | None) -> bool:
    if not isinstance(metadata, Mapping):
        return False
    return bool(_text(metadata.get(TOPIC_KEY)) and _text(metadata.get(BOT_KEY)))


def arbitrate_send(
    *,
    metadata: Mapping[str, Any] | None,
    target: str,
    content: str,
    cache: RoutingCache | None = None,
) -> Decision:
    """Return a delivery decision for an outbound send.

    The arbiter is opt-in.  Missing topic/bot metadata bypasses all checks.
    Once opted in, missing or malformed routing config fails closed.
    """
    if not is_governed_metadata(metadata):
        return Decision(governed=False, allowed=True, reason="no arbiter metadata", status="bypass")

    meta = dict(metadata or {})
    topic = _text(meta.get(TOPIC_KEY))
    bot = _text(meta.get(BOT_KEY))
    action = _text(meta.get(ACTION_KEY)) or "send"
    trace_id = _text(meta.get(TRACE_KEY))
    idempotency_key = _text(meta.get(IDEMPOTENCY_KEY)) or _text(meta.get("idempotency_key"))

    data, error = (cache or _cache()).load()
    if error or data is None:
        return Decision(
            governed=True,
            allowed=False,
            reason=error or "routing file unavailable",
            status="denied",
            source="routing",
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )

    context = {
        "topic": topic,
        "bot": bot,
        "action": action,
        "target": target,
        "content": content,
    }

    deny_match = _first_matching_rule(_collect_rules(data, "deny", topic, bot), context)
    if deny_match:
        return Decision(
            governed=True,
            allowed=False,
            reason=deny_match.get("reason") or "denied by bot routing policy",
            status="denied",
            source="routing",
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            matched_rule=deny_match.get("name"),
        )

    allow_rules = list(_collect_rules(data, "allow", topic, bot))
    if not allow_rules:
        return Decision(
            governed=True,
            allowed=False,
            reason="no allow rules configured",
            status="denied",
            source="routing",
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )
    allow_match = _first_matching_rule(allow_rules, context)
    if not allow_match:
        return Decision(
            governed=True,
            allowed=False,
            reason="no allow rule matched",
            status="denied",
            source="routing",
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )

    if idempotency_key and _is_duplicate(idempotency_key, trace_id):
        return Decision(
            governed=True,
            allowed=False,
            reason="duplicate idempotency key",
            status="denied",
            source="idempotency",
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )

    return Decision(
        governed=True,
        allowed=True,
        reason="allowed by bot routing policy",
        status="allowed",
        source="routing",
        trace_id=trace_id,
        idempotency_key=idempotency_key,
    )


def _collect_rules(data: Mapping[str, Any], kind: str, topic: str, bot: str) -> Iterable[dict[str, Any]]:
    keys = [kind, f"{kind}_rules"]
    if kind == "deny":
        keys.append("global_deny")

    for key in keys:
        yield from _normalize_rules(data.get(key), prefix=key)

    topics = data.get("topics")
    if isinstance(topics, Mapping):
        topic_cfg = topics.get(topic)
        if isinstance(topic_cfg, Mapping):
            yield from _normalize_rules(topic_cfg.get(kind), prefix=f"topics.{topic}.{kind}")
            bots = topic_cfg.get("bots")
            if isinstance(bots, Mapping):
                bot_cfg = bots.get(bot)
                if isinstance(bot_cfg, Mapping):
                    yield from _normalize_rules(bot_cfg.get(kind), prefix=f"topics.{topic}.bots.{bot}.{kind}")

    bots = data.get("bots")
    if isinstance(bots, Mapping):
        bot_cfg = bots.get(bot)
        if isinstance(bot_cfg, Mapping):
            yield from _normalize_rules(bot_cfg.get(kind), prefix=f"bots.{bot}.{kind}")


def _normalize_rules(value: Any, *, prefix: str) -> Iterable[dict[str, Any]]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    rules: list[dict[str, Any]] = []
    for index, item in enumerate(values):
        if isinstance(item, str):
            rules.append({"name": f"{prefix}[{index}]", "topic": item})
        elif isinstance(item, Mapping):
            rule = dict(item)
            rule.setdefault("name", f"{prefix}[{index}]")
            rules.append(rule)
    return rules


def _first_matching_rule(rules: Iterable[dict[str, Any]], context: Mapping[str, str]) -> dict[str, Any] | None:
    for rule in rules:
        if _matches_rule(rule, context):
            return rule
    return None


def _matches_rule(rule: Mapping[str, Any], context: Mapping[str, str]) -> bool:
    for key in ("topic", "bot", "action", "target"):
        expected = rule.get(key)
        if expected is None:
            continue
        if key == "action":
            normalized_expected = _text(expected)
            if normalized_expected in POLICY_ACTIONS:
                # Runtime bot-routing.yml historically uses `action` to describe
                # policy outcomes such as deny_and_alert, not outbound send type.
                continue
        allowed = expected if isinstance(expected, list) else [expected]
        normalized = {_text(item) for item in allowed}
        if context.get(key) not in normalized and "*" not in normalized:
            return False
    contains = _text(rule.get("content_contains"))
    if contains and contains not in context.get("content", ""):
        return False
    patterns = _text_list(rule.get("patterns"))
    if patterns and not _matches_any_pattern(patterns, context):
        return False
    return True


def _matches_any_pattern(patterns: Iterable[str], context: Mapping[str, str]) -> bool:
    haystack = "\n".join(
        value
        for value in (
            context.get("topic", ""),
            context.get("bot", ""),
            context.get("action", ""),
            context.get("target", ""),
            context.get("content", ""),
        )
        if value
    )
    for pattern in patterns:
        if not pattern:
            continue
        try:
            if re.search(pattern, haystack, flags=re.IGNORECASE):
                return True
        except re.error:
            if pattern.lower() in haystack.lower():
                return True
    return False


def _text_list(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [_text(item) for item in values if _text(item)]


def _is_duplicate(key: str, trace_id: str | None) -> bool:
    db_path = get_hermes_home() / "gateway" / "arbiter.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS arbiter_idempotency ("
            "key TEXT PRIMARY KEY, trace_id TEXT, created_at TEXT NOT NULL)"
        )
        cur = conn.execute(
            "INSERT OR IGNORE INTO arbiter_idempotency(key, trace_id, created_at) VALUES (?, ?, ?)",
            (key, trace_id, datetime.now(timezone.utc).isoformat()),
        )
        return cur.rowcount == 0


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
