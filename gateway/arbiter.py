"""Gateway arbiter for topic→bot routing and idempotent send guards.

First implementation is gateway-local and opt-in.
Existing send paths bypass the arbiter unless metadata includes:
- arbiter_topic
- arbiter_bot_name

Optional metadata keys:
- arbiter_action
- arbiter_trace_id
- arbiter_routing_yml
- arbiter_idempotency_db
- arbiter_heartbeat_dir
"""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

DEFAULT_ROUTING_YML = Path("/home/sudol/.hermes/config/bot-routing.yml")
DEFAULT_IDEMPOTENCY_DB = Path("/home/sudol/.hermes/idempotency.db")
DEFAULT_HEARTBEAT_DIR = Path("/home/sudol/.hermes/heartbeat")
DEFAULT_HEARTBEAT_MAX_AGE_SEC = 60


@dataclass
class Decision:
    allow: bool
    reason: str
    trace_id: str
    alert_slack: bool = False
    alert_telegram: bool = False
    require_human_confirmation: bool = False
    fallback_bot: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RoutingCache:
    """Reload-on-change cache for bot-routing yaml."""

    def __init__(self, path: Path | str = DEFAULT_ROUTING_YML):
        self.path = Path(path)
        self.data: Optional[dict[str, Any]] = None
        self.hash: Optional[str] = None
        self.loaded_at: float = 0.0
        self.reload()

    def reload(self) -> bool:
        if not self.path.exists():
            logger.error("routing yml missing: %s", self.path)
            self.data = None
            return False

        raw = self.path.read_bytes()
        new_hash = hashlib.sha256(raw).hexdigest()
        if new_hash == self.hash and self.data is not None:
            return False

        try:
            parsed = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            logger.error("yaml parse failed: %s", exc)
            self.data = None
            return False

        if not isinstance(parsed, dict) or parsed.get("version") != 1:
            logger.error("routing yml schema version mismatch")
            self.data = None
            return False

        self.data = parsed
        self.hash = new_hash
        self.loaded_at = time.time()
        logger.info("routing yml reloaded, hash=%s", new_hash[:8])
        return True


def _make_trace_id(bot_name: str) -> str:
    return f"tg-{bot_name}:{int(time.time() * 1000)}:{uuid.uuid4().hex[:5]}"


def _action_hash(action: dict[str, Any]) -> str:
    payload = action.get("payload", "")
    canonical = f"{action.get('type', '')}:{payload}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _idempotency_check(trace_id: str, action_hash: str, ttl: int, db_path: Path | str) -> bool:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS seen (
                action_hash TEXT PRIMARY KEY,
                trace_id TEXT,
                first_seen INTEGER
            )
            """
        )
        row = db.execute(
            "SELECT first_seen FROM seen WHERE action_hash = ?", (action_hash,)
        ).fetchone()
        now = int(time.time())
        if row is not None and (now - row[0]) < ttl:
            return True
        db.execute(
            "INSERT OR REPLACE INTO seen(action_hash, trace_id, first_seen) VALUES (?, ?, ?)",
            (action_hash, trace_id, now),
        )
        db.commit()
    return False


def _match_global_deny(topic: str, action: dict[str, Any], routing_data: dict[str, Any]) -> Optional[dict[str, Any]]:
    payload_str = str(action.get("payload", ""))
    for rule in routing_data.get("global_deny", []):
        rule_topic = rule.get("topic", "*")
        if rule_topic != "*" and rule_topic != topic:
            continue
        for pat in rule.get("patterns", []):
            try:
                if re.search(pat, payload_str):
                    return rule
            except re.error as exc:
                logger.warning("invalid regex in rule %s: %s", rule.get("name"), exc)
    return None


def _primary_alive(primary_bot: Optional[str], heartbeat_dir: Path | str, max_age_sec: int = DEFAULT_HEARTBEAT_MAX_AGE_SEC) -> bool:
    if primary_bot is None:
        return False
    hb = Path(heartbeat_dir) / f"{primary_bot}.ts"
    if not hb.exists():
        return False
    age = time.time() - hb.stat().st_mtime
    return age < max_age_sec


def arbitrate_send(
    bot_name: str,
    topic: str,
    action: dict[str, Any],
    *,
    trace_id: Optional[str] = None,
    routing_cache: Optional[RoutingCache] = None,
    idempotency_db: Path | str = DEFAULT_IDEMPOTENCY_DB,
    heartbeat_dir: Path | str = DEFAULT_HEARTBEAT_DIR,
    heartbeat_max_age_sec: int = DEFAULT_HEARTBEAT_MAX_AGE_SEC,
) -> Decision:
    cache = routing_cache or RoutingCache()
    tid = trace_id or _make_trace_id(bot_name)

    if cache.data is None:
        if bot_name == "AHC_A8_bot":
            return Decision(allow=False, reason="arbiter_minimal_mode_receive_only", trace_id=tid)
        return Decision(allow=False, reason="arbiter_yaml_unavailable", trace_id=tid, alert_telegram=True)

    topics = cache.data.get("topics", {})
    t = topics.get(topic)
    if t is None:
        return Decision(allow=False, reason="unknown_topic", trace_id=tid, alert_slack=True)

    if not t.get("enabled", True):
        return Decision(allow=False, reason="topic_disabled", trace_id=tid)

    is_primary = bot_name == t.get("primary")
    failover_list = t.get("failover") or []
    is_failover = bot_name in failover_list
    if not (is_primary or is_failover):
        return Decision(allow=False, reason="bot_not_authorized_for_topic", trace_id=tid, alert_slack=True)

    if is_failover and _primary_alive(t.get("primary"), heartbeat_dir, heartbeat_max_age_sec):
        return Decision(
            allow=False,
            reason="primary_alive_failover_denied",
            trace_id=tid,
            fallback_bot=t.get("primary"),
        )

    hit = _match_global_deny(topic, action, cache.data)
    if hit:
        action_type = hit.get("action", "deny_and_alert")
        return Decision(
            allow=False,
            reason=f"global_deny:{hit.get('name', 'unknown')}",
            trace_id=tid,
            alert_slack=True,
            alert_telegram=(action_type == "deny_and_alert"),
            require_human_confirmation=(action_type == "require_human_confirmation"),
            metadata={
                "matched_rule": hit.get("name"),
                "rule_reason": hit.get("reason"),
                "rule_action": action_type,
            },
        )

    ah = _action_hash(action)
    ttl_sec = cache.data.get("idempotency", {}).get("action_hash_ttl_seconds", 3600)
    if _idempotency_check(tid, ah, ttl_sec, idempotency_db):
        return Decision(allow=False, reason="duplicate_action_denied_by_idempotency", trace_id=tid)

    return Decision(allow=True, reason="ok", trace_id=tid)


def arbitrate_receive(
    bot_name: str,
    message: dict[str, Any],
    *,
    routing_cache: Optional[RoutingCache] = None,
) -> str:
    cache = routing_cache or RoutingCache()
    if cache.data is None:
        return "dev-command"

    rules = cache.data.get("inbound_classification", {})
    text = message.get("text", "") or ""

    for prefix, topic in (rules.get("by_command_prefix") or {}).items():
        if text.startswith(prefix):
            return topic

    hint = (rules.get("by_bot_token_hint") or {}).get(bot_name)
    if hint:
        return hint

    return rules.get("default_fallback", "dev-command")


def maybe_arbitrate_delivery(metadata: Optional[dict[str, Any]]) -> Optional[Decision]:
    if not metadata:
        return None
    topic = metadata.get("arbiter_topic")
    bot_name = metadata.get("arbiter_bot_name")
    if not topic or not bot_name:
        return None

    action = metadata.get("arbiter_action") or {"type": "message", "payload": metadata.get("content", "")}
    routing_path = metadata.get("arbiter_routing_yml") or DEFAULT_ROUTING_YML
    db_path = metadata.get("arbiter_idempotency_db") or DEFAULT_IDEMPOTENCY_DB
    hb_dir = metadata.get("arbiter_heartbeat_dir") or DEFAULT_HEARTBEAT_DIR
    trace_id = metadata.get("arbiter_trace_id")

    cache = RoutingCache(routing_path)
    return arbitrate_send(
        bot_name,
        topic,
        action,
        trace_id=trace_id,
        routing_cache=cache,
        idempotency_db=db_path,
        heartbeat_dir=hb_dir,
    )
