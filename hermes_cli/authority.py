"""Read-only Hermes authority scorecard and managed-agent registry helpers.

This module intentionally starts in dry-run/read-only mode. It does not restart
services, kill sessions, mutate queues, or control unmanaged processes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_HOME = Path.home() / ".hermes"
DEFAULT_POLICY_PATH = DEFAULT_HOME / "config" / "authority-policy.yml"
DEFAULT_AUDIT_PATH = DEFAULT_HOME / "audit" / "authority.log"
DEFAULT_REGISTRY_DIR = DEFAULT_HOME / "agent-registry"


@dataclass(frozen=True)
class AuthorityLevel:
    """One authority level from the dry-run policy file."""

    approval: str = "user"


@dataclass(frozen=True)
class AuthorityPolicy:
    """Parsed authority policy with safe defaults."""

    mode: str = "dry_run"
    levels: dict[str, AuthorityLevel] = field(default_factory=dict)
    promotion_gates: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuthorityPaths:
    """Filesystem paths used by authority reporting."""

    policy_path: Path = DEFAULT_POLICY_PATH
    audit_path: Path = DEFAULT_AUDIT_PATH
    registry_dir: Path = DEFAULT_REGISTRY_DIR


@dataclass(frozen=True)
class AuthorityScorecard:
    """Read-only promotion readiness snapshot."""

    mode: str
    observation_days: int
    observation_success_rate: float
    audit_log_missing: int
    dry_run_match_rate: float
    rollback_verified: bool
    managed_agent_count: int
    l2_candidate: bool
    l3_candidate: bool
    policy_exists: bool
    audit_exists: bool


_DEFAULT_LEVELS = {
    "L0": AuthorityLevel("none"),
    "L1": AuthorityLevel("none"),
    "L2": AuthorityLevel("policy"),
    "L3": AuthorityLevel("user"),
    "L4": AuthorityLevel("explicit"),
}

_DEFAULT_GATES = {
    "observation_days": 7,
    "min_observation_success_rate": 0.98,
    "max_audit_log_missing": 0,
    "min_dry_run_match_rate": 1.0,
    "rollback_verified": True,
}


def load_authority_policy(path: str | Path = DEFAULT_POLICY_PATH) -> AuthorityPolicy:
    """Load policy YAML; fail closed to dry-run defaults on missing/broken file."""

    policy_path = Path(path)
    if not policy_path.exists():
        return AuthorityPolicy(levels=dict(_DEFAULT_LEVELS), promotion_gates=dict(_DEFAULT_GATES))

    try:
        raw = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return AuthorityPolicy(levels=dict(_DEFAULT_LEVELS), promotion_gates=dict(_DEFAULT_GATES))

    raw_levels = raw.get("levels") if isinstance(raw, dict) else {}
    levels = dict(_DEFAULT_LEVELS)
    if isinstance(raw_levels, dict):
        for name, value in raw_levels.items():
            if isinstance(name, str) and isinstance(value, dict):
                levels[name] = AuthorityLevel(str(value.get("approval", levels.get(name, AuthorityLevel()).approval)))

    gates = dict(_DEFAULT_GATES)
    raw_gates = raw.get("promotion_gates") if isinstance(raw, dict) else {}
    if isinstance(raw_gates, dict):
        gates.update(raw_gates)

    mode = str(raw.get("mode", "dry_run")) if isinstance(raw, dict) else "dry_run"
    if mode not in {"dry_run", "read_only"}:
        mode = "dry_run"
    return AuthorityPolicy(mode=mode, levels=levels, promotion_gates=gates)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _tail_lines(path: Path, max_lines: int = 10000, max_bytes: int = 2 * 1024 * 1024) -> list[str]:
    """Read a bounded tail from a log file without loading unbounded data."""

    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            data = handle.read(max_bytes)
    except OSError:
        return []
    return data.decode("utf-8", errors="replace").splitlines()[-max_lines:]


def _audit_metrics(path: Path) -> tuple[int, float, int, float, bool, bool]:
    """Return days, success_rate, missing_count, dry_run_match_rate, rollback, exists."""

    if not path.exists():
        return 0, 0.0, 1, 0.0, False, False

    dates: set[str] = set()
    observation_total = observation_success = 0
    dry_total = dry_match = 0
    missing = 0
    rollback_verified = False

    for line in _tail_lines(path):
        match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", line)
        if match:
            dates.add(match.group(1))
        if "audit_missing=1" in line:
            missing += 1
        if "observation_success=" in line:
            observation_total += 1
            if "observation_success=1" in line:
                observation_success += 1
        if "dry_run_match=" in line:
            dry_total += 1
            if "dry_run_match=1" in line:
                dry_match += 1
        if "rollback_verified=1" in line:
            rollback_verified = True

    success_rate = observation_success / observation_total if observation_total else 0.0
    dry_rate = dry_match / dry_total if dry_total else 0.0
    return len(dates), success_rate, missing, dry_rate, rollback_verified, True


def _managed_agent_count(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    count = 0
    for item in path.glob("*.json"):
        try:
            raw = json.loads(item.read_text(encoding="utf-8"))
        except Exception:
            continue
        if raw.get("managed") is not False:
            count += 1
    return count


def build_scorecard(paths: AuthorityPaths = AuthorityPaths()) -> AuthorityScorecard:
    """Build the read-only authority promotion scorecard."""

    policy = load_authority_policy(paths.policy_path)
    days, success_rate, missing, dry_rate, rollback, audit_exists = _audit_metrics(paths.audit_path)
    gates = policy.promotion_gates

    l2_candidate = (
        days >= _as_int(gates.get("observation_days"), 7)
        and success_rate >= _as_float(gates.get("min_observation_success_rate"), 0.98)
        and missing <= _as_int(gates.get("max_audit_log_missing"), 0)
        and dry_rate >= _as_float(gates.get("min_dry_run_match_rate"), 1.0)
        and (rollback or not _as_bool(gates.get("rollback_verified"), True))
        and policy.mode in {"dry_run", "read_only"}
    )

    return AuthorityScorecard(
        mode=policy.mode,
        observation_days=days,
        observation_success_rate=success_rate,
        audit_log_missing=missing,
        dry_run_match_rate=dry_rate,
        rollback_verified=rollback,
        managed_agent_count=_managed_agent_count(paths.registry_dir),
        l2_candidate=l2_candidate,
        l3_candidate=False,
        policy_exists=paths.policy_path.exists(),
        audit_exists=audit_exists,
    )


def format_authority_report(paths: AuthorityPaths = AuthorityPaths()) -> str:
    """Format a concise Korean status report for CLI/Telegram."""

    s = build_scorecard(paths)
    judgment = "L2 일부 가능" if s.l2_candidate else "승급 보류"
    if s.l3_candidate:
        judgment = "L3 후보"
    return "\n".join(
        [
            "Hermes 권한 점검",
            f"- 모드: {s.mode}",
            f"- 관측 일수: {s.observation_days}일",
            f"- 관측 성공률: {s.observation_success_rate:.1%}",
            f"- dry-run 일치율: {s.dry_run_match_rate:.1%}",
            f"- 감사 로그 누락: {s.audit_log_missing}건",
            f"- rollback 검증: {'완료' if s.rollback_verified else '미완료'}",
            f"- 관리형 에이전트: {s.managed_agent_count}개",
            f"- 승급 판단: {judgment}",
            "- 실제 권한 승급: 수동 승인 필요",
        ]
    )
