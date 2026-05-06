"""Context landing policy for gateway sessions.

This module is deliberately side-effect-light: it calculates threshold crossing,
formats user-facing Telegram-safe messages, and can write a minimal markdown
landing note. The gateway decides when/how to deliver messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from hermes_constants import get_hermes_home


_DEFAULT_THRESHOLDS = [0.72, 0.82, 0.90]
_STAGE_BY_THRESHOLD = {
    0.72: "prepare",
    0.82: "save",
    0.90: "urgent",
}


@dataclass
class ContextLandingState:
    """Per-session de-duplication state for landing notifications."""

    last_threshold: float = 0.0
    last_notified_at: float = 0.0
    last_note_path: str = ""


@dataclass(frozen=True)
class ContextLandingEvent:
    should_notify: bool
    should_write_note: bool
    should_compress: bool
    stage: str
    threshold: float
    percent: int
    message: str


_EMPTY_EVENT = ContextLandingEvent(
    should_notify=False,
    should_write_note=False,
    should_compress=False,
    stage="",
    threshold=0.0,
    percent=0,
    message="",
)


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _as_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def resolve_context_landing_config(user_config: dict[str, Any] | None) -> dict[str, Any]:
    """Return normalized context_landing config.

    Defaults are conservative and disabled. Automatic compression remains owned by
    ``compression.threshold``; this policy only lands/saves before that point.
    """

    raw = (user_config or {}).get("context_landing")
    if not isinstance(raw, dict):
        raw = {}
    compression_raw = (user_config or {}).get("compression")
    compression_threshold = 0.95
    if isinstance(compression_raw, dict):
        compression_threshold = _as_float(compression_raw.get("threshold"), 0.95)

    thresholds_raw = raw.get("notify_thresholds", _DEFAULT_THRESHOLDS)
    if isinstance(thresholds_raw, (list, tuple)) and thresholds_raw:
        thresholds = sorted({_as_float(item, 0.0) for item in thresholds_raw if _as_float(item, 0.0) > 0})
    else:
        thresholds = list(_DEFAULT_THRESHOLDS)

    return {
        "enabled": _as_bool(raw.get("enabled"), False),
        "prepare_threshold": _as_float(raw.get("prepare_threshold"), 0.72),
        "save_threshold": _as_float(raw.get("save_threshold"), 0.82),
        "notify_thresholds": thresholds,
        "min_notify_interval_seconds": int(_as_float(raw.get("min_notify_interval_seconds"), 900)),
        "auto_landing_note": _as_bool(raw.get("auto_landing_note"), True),
        "telegram_notify": _as_bool(raw.get("telegram_notify"), True),
        "compression_threshold": compression_threshold,
    }


def _stage_for_threshold(threshold: float, cfg: dict[str, Any]) -> str:
    if threshold >= 0.90:
        return "urgent"
    if threshold >= float(cfg.get("save_threshold", 0.82)):
        return "save"
    if threshold >= float(cfg.get("prepare_threshold", 0.72)):
        return "prepare"
    return _STAGE_BY_THRESHOLD.get(threshold, "prepare")


def _message_for_stage(stage: str, percent: int, compression_threshold: float) -> str:
    compression_pct = max(0, min(100, round(compression_threshold * 100)))
    if stage == "urgent":
        return (
            f"컨텍스트 {percent}%입니다. 자동 압축은 {compression_pct}% 유지 중이며, "
            "압축 전 복구 정보를 우선 저장합니다."
        )
    if stage == "save":
        return (
            f"컨텍스트 {percent}%입니다. 새 작업 확장보다 검증/저장을 우선합니다. "
            "압축 전 복구 가능한 상태를 먼저 남깁니다."
        )
    return (
        f"컨텍스트 {percent}%입니다. 자동 압축은 {compression_pct}% 유지, "
        "지금부터 저장 준비 모드로 전환합니다."
    )


def evaluate_context_landing(
    context_tokens: int,
    context_length: Optional[int],
    config: dict[str, Any],
    state: ContextLandingState,
    now: Optional[float] = None,
    *,
    commit_state: bool = True,
) -> ContextLandingEvent:
    """Evaluate threshold crossing and update *state* when firing.

    Returns ``should_compress=False`` by design: this policy must not lower the
    user's configured automatic compression threshold.
    """

    if not config.get("enabled") or not context_length or context_length <= 0 or context_tokens < 0:
        return _EMPTY_EVENT

    ratio = context_tokens / context_length
    percent = max(0, min(100, round(ratio * 100)))
    crossed = [t for t in config.get("notify_thresholds", _DEFAULT_THRESHOLDS) if ratio >= t]
    if not crossed:
        return _EMPTY_EVENT

    threshold = max(crossed)
    current_time = float(now if now is not None else datetime.now().timestamp())
    if threshold <= state.last_threshold:
        return _EMPTY_EVENT
    if (
        threshold <= state.last_threshold
        and state.last_notified_at
        and current_time - state.last_notified_at < int(config.get("min_notify_interval_seconds", 900))
    ):
        return _EMPTY_EVENT

    stage = _stage_for_threshold(threshold, config)
    if commit_state:
        state.last_threshold = threshold
        state.last_notified_at = current_time
    return ContextLandingEvent(
        should_notify=True,
        should_write_note=bool(config.get("auto_landing_note", True)),
        should_compress=False,
        stage=stage,
        threshold=threshold,
        percent=percent,
        message=_message_for_stage(stage, percent, float(config.get("compression_threshold", 0.95))),
    )


def build_landing_note(
    *,
    percent: int,
    stage: str,
    model: str | None,
    provider: str | None,
    context_tokens: int,
    context_length: int | None,
    platform: str | None,
    session_id: str | None,
    workdir: str | None,
) -> str:
    """Build a compact markdown note that future sessions can recover from."""

    created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return "\n".join([
        "# Hermes Context Landing",
        "",
        f"- created: {created}",
        f"- stage: {stage}",
        f"- context: {percent}% ({context_tokens}/{context_length or 'unknown'} tokens)",
        f"- model: {model or 'unknown'}",
        f"- provider: {provider or 'unknown'}",
        f"- platform: {platform or 'unknown'}",
        f"- session_id: {session_id or 'unknown'}",
        f"- workdir: {workdir or 'unknown'}",
        "",
        "## Recovery note",
        "",
        "이 파일은 자동 압축 전 복구를 위한 최소 landing note입니다. ",
        "작업별 HANDOFF/WORKLOG가 있으면 그것을 우선 확인하세요.",
        "",
    ])


def write_landing_note(note: str, *, root: Path | None = None, now_label: str | None = None) -> Path:
    """Write *note* under ~/.hermes/landing-notes and return the path.

    Uses exclusive create and microsecond labels by default so concurrent gateway
    sessions do not overwrite each other's landing notes.
    """

    base = root or (Path(get_hermes_home()) / "landing-notes")
    base.mkdir(parents=True, exist_ok=True)
    label = now_label or datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    for suffix in [""] + [f"-{idx}" for idx in range(1, 100)]:
        path = base / f"{label}-context-landing{suffix}.md"
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(note)
            return path
        except FileExistsError:
            continue
    raise FileExistsError(f"Could not create unique context landing note under {base}")
