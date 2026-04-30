#!/usr/bin/env python3
"""No-send smoke checks for the Hermes <-> OpenClaw opt-in bridge.

The script is safe to run before and after a gateway restart. It does not edit
runtime config, restart services, or send external messages.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "detail": self.detail}


def _hermes_command() -> list[str]:
    return [sys.executable, "-m", "hermes_cli.main"]


def _run(cmd: Sequence[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        list(cmd),
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _trim(value: str, limit: int = 1200) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[:limit] + " ... [truncated]"


def check_plugin_list() -> CheckResult:
    cmd = [*_hermes_command(), "plugins", "list"]
    try:
        proc = _run(cmd, timeout=60)
    except Exception as exc:
        return CheckResult("hermes plugins list", False, f"command failed: {exc}")

    output = proc.stdout + proc.stderr
    if proc.returncode != 0:
        return CheckResult(
            "hermes plugins list",
            False,
            f"exit={proc.returncode}: {_trim(output)}",
        )
    bridge_lines = [line for line in output.splitlines() if "openclaw-bridge" in line]
    if not bridge_lines:
        return CheckResult(
            "hermes plugins list",
            False,
            "openclaw-bridge was not listed",
        )
    bridge_status = "\n".join(bridge_lines).lower()
    if "enabled" not in bridge_status or "not enabled" in bridge_status:
        return CheckResult(
            "hermes plugins list",
            False,
            f"openclaw-bridge was listed but not enabled: {_trim(bridge_status)}",
        )
    return CheckResult("hermes plugins list", True, "openclaw-bridge is enabled")


def check_migration_dry_run() -> CheckResult:
    cmd = [*_hermes_command(), "claw", "migrate", "--dry-run"]
    try:
        proc = _run(cmd, timeout=120)
    except Exception as exc:
        return CheckResult("hermes claw migrate --dry-run", False, f"command failed: {exc}")

    output = proc.stdout + proc.stderr
    if proc.returncode != 0:
        return CheckResult(
            "hermes claw migrate --dry-run",
            False,
            f"exit={proc.returncode}: {_trim(output)}",
        )
    return CheckResult("hermes claw migrate --dry-run", True, "dry-run exited successfully")


def check_arbiter_no_send() -> list[CheckResult]:
    from gateway.arbiter import RoutingCache, arbitrate_send

    old_home = os.environ.get("HERMES_HOME")
    results: list[CheckResult] = []

    try:
        with tempfile.TemporaryDirectory(prefix="hermes-openclaw-smoke-") as tmp:
            tmp_home = Path(tmp)
            os.environ["HERMES_HOME"] = str(tmp_home)
            metadata = {
                "arbiter_topic": "openclaw-smoke",
                "arbiter_bot_name": "openclaw",
                "arbiter_action_type": "send",
                "arbiter_trace_id": "smoke-trace",
                "arbiter_idempotency_key": "smoke-idempotency-1",
            }

            missing = arbitrate_send(
                metadata=metadata,
                target="telegram:smoke",
                content="smoke content",
                cache=RoutingCache(tmp_home / "config" / "bot-routing.yml"),
            )
            results.append(
                CheckResult(
                    "arbiter missing routing fail-closed",
                    missing.governed and not missing.allowed,
                    missing.reason,
                )
            )

            routing_path = tmp_home / "config" / "bot-routing.yml"
            routing_path.parent.mkdir(parents=True, exist_ok=True)
            routing_path.write_text(
                json.dumps(
                    {
                        "topics": {
                            "openclaw-smoke": {
                                "bots": {
                                    "openclaw": {
                                        "allow": [
                                            {
                                                "name": "smoke-allow",
                                                "action": "send",
                                                "target": "telegram:smoke",
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            allowed = arbitrate_send(
                metadata=metadata,
                target="telegram:smoke",
                content="smoke content",
                cache=RoutingCache(routing_path),
            )
            results.append(
                CheckResult(
                    "arbiter temp allow policy",
                    allowed.governed and allowed.allowed,
                    allowed.reason,
                )
            )

            duplicate = arbitrate_send(
                metadata=metadata,
                target="telegram:smoke",
                content="smoke content",
                cache=RoutingCache(routing_path),
            )
            results.append(
                CheckResult(
                    "arbiter duplicate idempotency denied",
                    duplicate.governed and not duplicate.allowed,
                    duplicate.reason,
                )
            )
    finally:
        if old_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = old_home

    return results


def run_checks(*, skip_cli: bool) -> list[CheckResult]:
    results: list[CheckResult] = []
    if not skip_cli:
        results.append(check_plugin_list())
        results.append(check_migration_dry_run())
    results.extend(check_arbiter_no_send())
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-cli",
        action="store_true",
        help="Skip hermes CLI checks and run only import/arbiter no-send checks.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    results = run_checks(skip_cli=args.skip_cli)
    ok = all(result.ok for result in results)

    if args.json:
        print(json.dumps({"ok": ok, "checks": [item.as_dict() for item in results]}, indent=2))
    else:
        for result in results:
            mark = "PASS" if result.ok else "FAIL"
            print(f"[{mark}] {result.name}: {result.detail}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
