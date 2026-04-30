"""OpenClaw -> Hermes migration helper.

This module is intentionally conservative.  It supports the ``hermes claw
migrate --dry-run`` preview path first and only writes when the caller creates a
``Migrator`` with ``execute=True``.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


PROFILE_FILES = (
    "AGENTS.md",
    "USER.md",
    "IDENTITY.md",
    "SOUL.md",
    "TOOLS.md",
    "HEARTBEAT.md",
    "BOOTSTRAP.md",
)


@dataclass(frozen=True)
class SelectedOptions:
    include_workspace_profiles: bool = True
    include_task_state: bool = True
    include_skills: bool = True
    include_secrets: bool = False


def resolve_selected_options(
    include: Iterable[str] | None,
    exclude: Iterable[str] | None,
    *,
    preset: str = "full",
) -> SelectedOptions:
    """Resolve migration options expected by ``hermes_cli.claw``."""
    include_set = {item.strip() for item in include or [] if str(item).strip()}
    exclude_set = {item.strip() for item in exclude or [] if str(item).strip()}

    if preset == "minimal":
        selected = SelectedOptions(include_task_state=False, include_skills=False)
    else:
        selected = SelectedOptions()

    values = selected.__dict__.copy()
    for name in include_set:
        key = _option_key(name)
        if key in values:
            values[key] = True
    for name in exclude_set:
        key = _option_key(name)
        if key in values:
            values[key] = False
    return SelectedOptions(**values)


def _option_key(name: str) -> str:
    normalized = name.strip().lower().replace("-", "_")
    aliases = {
        "workspace": "include_workspace_profiles",
        "workspaces": "include_workspace_profiles",
        "profiles": "include_workspace_profiles",
        "tasks": "include_task_state",
        "task_state": "include_task_state",
        "skills": "include_skills",
        "secrets": "include_secrets",
        "provider_keys": "include_secrets",
    }
    return aliases.get(normalized, normalized)


class Migrator:
    """Preview and optionally copy safe OpenClaw state into Hermes."""

    def __init__(
        self,
        *,
        source_root: Path,
        target_root: Path,
        execute: bool,
        workspace_target: Path | None,
        overwrite: bool,
        migrate_secrets: bool,
        output_dir: Path | None,
        selected_options: SelectedOptions,
        preset_name: str,
        skill_conflict_mode: str = "skip",
    ) -> None:
        self.source_root = Path(source_root)
        self.target_root = Path(target_root)
        self.execute = execute
        self.workspace_target = Path(workspace_target) if workspace_target else None
        self.overwrite = overwrite
        self.migrate_secrets = migrate_secrets
        self.output_dir = output_dir
        self.selected_options = selected_options
        self.preset_name = preset_name
        self.skill_conflict_mode = skill_conflict_mode

    def migrate(self) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        if not self.source_root.exists():
            return self._report([
                {
                    "kind": "source-root",
                    "status": "error",
                    "reason": f"not found: {self.source_root}",
                }
            ])

        if self.selected_options.include_workspace_profiles:
            items.extend(self._workspace_profile_items())

        if self.selected_options.include_task_state:
            items.extend(self._task_state_items())

        if self.selected_options.include_skills:
            items.extend(self._skill_items())

        if self.migrate_secrets and self.selected_options.include_secrets:
            items.append(
                {
                    "kind": "provider-keys",
                    "status": "skipped",
                    "reason": "secret migration is intentionally not implemented by this safe helper",
                }
            )

        return self._report(items)

    def _workspace_profile_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for workspace in self._workspace_dirs():
            for filename in PROFILE_FILES:
                source = workspace / filename
                if not source.is_file():
                    continue
                destination = self._workspace_destination(workspace) / filename
                items.append(self._copy_item(f"workspace-profile:{workspace.name}/{filename}", source, destination))
        return items

    def _workspace_dirs(self) -> list[Path]:
        workspaces: list[Path] = []
        for child in sorted(self.source_root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if any((child / filename).exists() for filename in PROFILE_FILES):
                workspaces.append(child)
        return workspaces

    def _workspace_destination(self, workspace: Path) -> Path:
        base = self.workspace_target or (self.target_root / "openclaw-imports" / "workspaces")
        return base / workspace.name

    def _task_state_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for rel in ("tasks/runs.sqlite", "msteams-pending-uploads.json"):
            source = self.source_root / rel
            if source.is_file():
                destination = self.target_root / "openclaw-imports" / "runtime" / rel
                items.append(self._copy_item(f"runtime-state:{rel}", source, destination))
        return items

    def _skill_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        skills_dir = self.source_root / "skills"
        if not skills_dir.is_dir():
            return items
        for source in sorted(skills_dir.rglob("*")):
            if not source.is_file():
                continue
            rel = source.relative_to(skills_dir)
            destination = self.target_root / "skills" / "openclaw-imports" / rel
            items.append(self._copy_item(f"skill:{rel.as_posix()}", source, destination))
        return items

    def _copy_item(self, kind: str, source: Path, destination: Path) -> dict[str, Any]:
        if destination.exists() and not self.overwrite:
            return {
                "kind": kind,
                "status": "conflict",
                "source": str(source),
                "destination": str(destination),
                "reason": "destination already exists",
            }
        if self.execute:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        return {
            "kind": kind,
            "status": "migrated",
            "source": str(source),
            "destination": str(destination),
        }

    def _report(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        summary = {"migrated": 0, "skipped": 0, "conflict": 0, "error": 0}
        for item in items:
            status = item.get("status", "skipped")
            if status in summary:
                summary[status] += 1
            else:
                summary["skipped"] += 1
        return {
            "preset": self.preset_name,
            "summary": summary,
            "items": items,
            "output_dir": str(self.output_dir) if self.output_dir else None,
        }
