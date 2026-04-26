"""Telegram/gateway context status, anchors, and lightweight notes."""

from __future__ import annotations

import json
import os
import re
import tempfile
import fcntl
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


@dataclass(frozen=True)
class ContextPaths:
    """Filesystem paths for context management."""

    anchor_path: Path = get_hermes_home() / "context" / "anchors.json"
    notes_dir: Path = get_hermes_home() / "context" / "notes"
    allowed_anchor_roots: tuple[Path, ...] | None = None


def _platform_value(source: Any) -> str:
    platform = getattr(source, "platform", "unknown")
    return str(getattr(platform, "value", platform) or "unknown")


def _session_key(source: Any, session_entry: Any | None = None) -> str:
    if session_entry is not None:
        key = str(getattr(session_entry, "session_key", "") or "").strip()
        if key:
            return key
    platform = _platform_value(source)
    chat_id = str(getattr(source, "chat_id", "") or "unknown")
    thread_id = str(getattr(source, "thread_id", "") or "")
    return f"{platform}:{chat_id}:{thread_id}" if thread_id else f"{platform}:{chat_id}"


def _load_anchors(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError):
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def _secure_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _safe_session_slug(session_key: str) -> str:
    return re.sub(r"[^0-9A-Za-z_.-]+", "_", str(session_key))[:120] or "unknown"


def _session_notes_dir(paths: ContextPaths, session_key: str) -> Path:
    return Path(paths.notes_dir) / _safe_session_slug(session_key)


def _open_new_secure(path: Path, mode: str):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    if "b" in mode:
        return os.fdopen(fd, mode)
    return os.fdopen(fd, mode, encoding="utf-8")


def _save_anchors(path: Path, anchors: dict[str, str]) -> None:
    _secure_mkdir(path.parent)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        os.chmod(tmp.name, 0o600)
        json.dump(anchors, tmp, ensure_ascii=False, indent=2, sort_keys=True)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)
    os.chmod(path, 0o600)


def _allowed_anchor_roots(paths: ContextPaths, session_key: str) -> tuple[Path, ...]:
    configured_roots = getattr(paths, "allowed_anchor_roots", None)
    if configured_roots is not None:
        roots = configured_roots
    else:
        roots = (_session_notes_dir(paths, session_key),)
        extra_roots = os.environ.get("HERMES_CONTEXT_ANCHOR_ROOTS", "").strip()
        if extra_roots:
            roots = roots + tuple(Path(part) for part in extra_roots.split(os.pathsep) if part.strip())
    return tuple(root.expanduser().resolve() for root in roots)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _validate_anchor_file(path: Path, paths: ContextPaths, session_key: str) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"anchor file not found: {path.name}")
    if not any(_is_relative_to(path, root) for root in _allowed_anchor_roots(paths, session_key)):
        raise PermissionError("anchor file is outside allowed context roots")
    if path.name in {"anchors.json", "anchors.json.lock"} or path.name.startswith(".anchors.json"):
        raise PermissionError("internal context metadata cannot be pinned")
    if re.search(r"(?i)(secret|token|credential|password|passwd|config|session|auth)", path.name):
        raise PermissionError("anchor file name looks sensitive")
    if path.suffix.lower() not in {".md", ".txt", ".json", ".yaml", ".yml"}:
        raise PermissionError("anchor file type is not allowed")
    if path.stat().st_size > 2 * 1024 * 1024:
        raise PermissionError("anchor file is too large")
    try:
        path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise PermissionError("anchor file must be UTF-8 text") from exc


def display_context_path(file_path: str | Path) -> str:
    """Return a non-sensitive display path for Telegram responses."""

    path = Path(file_path).expanduser()
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    return resolved.name


def _copy_anchor_snapshot(session_key: str, resolved: Path, paths: ContextPaths) -> Path:
    anchor_dir = _session_notes_dir(paths, session_key) / "_anchors"
    _secure_mkdir(anchor_dir)
    target = anchor_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{resolved.name}"
    with resolved.open("rb") as src, _open_new_secure(target, "wb") as dst:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            dst.write(chunk)
    return target.resolve()


def _set_context_pin(session_key: str, resolved: Path, paths: ContextPaths) -> None:
    anchor_path = Path(paths.anchor_path)
    _secure_mkdir(anchor_path.parent)
    lock_path = anchor_path.with_suffix(anchor_path.suffix + ".lock")
    fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        anchors = _load_anchors(anchor_path)
        anchors[str(session_key)] = str(resolved)
        _save_anchors(anchor_path, anchors)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def save_context_pin(session_key: str, file_path: str | Path, *, paths: ContextPaths = ContextPaths()) -> Path:
    """Pin a safe text-file snapshot as the context anchor for a gateway session."""

    session_key = str(session_key)
    resolved = Path(file_path).expanduser().resolve()
    _validate_anchor_file(resolved, paths, session_key)
    pinned_snapshot = _copy_anchor_snapshot(session_key, resolved, paths)
    _set_context_pin(session_key, pinned_snapshot, paths)
    return pinned_snapshot


def get_context_pin(session_key: str, *, paths: ContextPaths = ContextPaths()) -> str | None:
    return _load_anchors(Path(paths.anchor_path)).get(str(session_key))


def _slugify_title(title: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣._-]+", "-", title.strip()).strip("-._")
    return slug[:60] or "context-note"


def _message_preview(message: dict[str, Any], limit: int = 240) -> str:
    role = str(message.get("role") or "unknown")
    content = str(message.get("content") or "").replace("\n", " ").strip()
    content = re.sub(
        r"(?i)(api[_-]?key|secret|password|passwd|token|credential)\s*[:=]\s*\S+",
        r"\1=[REDACTED]",
        content,
    )
    if len(content) > limit:
        content = content[: limit - 1] + "…"
    return f"- {role}: {content}" if content else f"- {role}:"


def save_context_note(
    *,
    title: str,
    source: Any,
    session_entry: Any,
    transcript: list[dict[str, Any]],
    paths: ContextPaths = ContextPaths(),
) -> Path:
    """Create a new markdown note with compact context metadata and recent tail."""

    clean_title = title.strip() or "Hermes 컨텍스트 메모"
    now = datetime.now()
    session_id = str(getattr(session_entry, "session_id", "") or "unknown")
    key = _session_key(source, session_entry)
    notes_dir = _session_notes_dir(paths, key)
    _secure_mkdir(notes_dir)
    filename = f"{now.strftime('%Y%m%d-%H%M%S')}-{_slugify_title(clean_title)}.md"
    note_path = notes_dir / filename

    anchor = get_context_pin(key, paths=paths) or ""
    recent = transcript[-12:]
    lines = [
        f"# {clean_title}",
        "",
        f"created: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"platform: {_platform_value(source)}",
        f"chat_id: {getattr(source, 'chat_id', '')}",
        f"thread_id: {getattr(source, 'thread_id', '') or ''}",
        f"session_id: {session_id}",
        f"session_key: {key}",
        f"anchor: {display_context_path(anchor) if anchor else ''}",
        f"messages: {len(transcript)}",
        "",
        "## 최근 메시지",
        *( _message_preview(msg) for msg in recent ),
        "",
    ]
    content = "\n".join(lines)
    counter = 0
    while True:
        candidate = note_path if counter == 0 else notes_dir / f"{now.strftime('%Y%m%d-%H%M%S')}-{_slugify_title(clean_title)}-{counter}.md"
        try:
            with _open_new_secure(candidate, "w") as handle:
                handle.write(content)
            note_path = candidate
            break
        except FileExistsError:
            counter += 1
    return note_path


def format_context_status(
    *,
    source: Any,
    session_entry: Any,
    transcript: list[dict[str, Any]],
    paths: ContextPaths = ContextPaths(),
) -> str:
    """Return a short Korean context status report for Telegram."""

    key = _session_key(source, session_entry)
    anchor = get_context_pin(key, paths=paths)
    anchor_display = display_context_path(anchor) if anchor else "없음"
    session_id = str(getattr(session_entry, "session_id", "") or "unknown")
    last_prompt = int(getattr(session_entry, "last_prompt_tokens", 0) or 0)
    total_tokens = int(getattr(session_entry, "total_tokens", 0) or 0)
    updated = getattr(session_entry, "updated_at", None)
    updated_text = updated.strftime("%Y-%m-%d %H:%M") if hasattr(updated, "strftime") else "unknown"
    lines = [
        "🧭 Hermes 컨텍스트",
        f"플랫폼: {_platform_value(source)}",
        f"채널: {getattr(source, 'chat_id', '')}",
    ]
    thread_id = getattr(source, "thread_id", None)
    if thread_id:
        lines.append(f"스레드: {thread_id}")
    lines.extend([
        f"세션: {session_id}",
        f"메시지: {len(transcript)}",
        f"토큰: {total_tokens:,} / 최근 프롬프트 {last_prompt:,}",
        f"최근 활동: {updated_text}",
        f"앵커: {anchor_display}",
        "명령: /context save <제목> · /context pin <파일>",
    ])
    return "\n".join(lines)
