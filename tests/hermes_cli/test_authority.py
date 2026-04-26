import pytest

from hermes_cli.commands import GATEWAY_KNOWN_COMMANDS, resolve_command, telegram_bot_commands


SAMPLE_POLICY = """
mode: dry_run
levels:
  L0:
    approval: none
  L1:
    approval: none
  L2:
    approval: policy
  L3:
    approval: user
  L4:
    approval: explicit
promotion_gates:
  observation_days: 7
  min_observation_success_rate: 0.98
  max_audit_log_missing: 0
  min_dry_run_match_rate: 1.0
  rollback_verified: true
"""


def test_authority_command_is_registered_for_cli_gateway_and_telegram():
    cmd = resolve_command("authority")
    assert cmd is not None
    assert cmd.name == "authority"
    assert "authority" in GATEWAY_KNOWN_COMMANDS
    assert any(name == "authority" for name, _desc in telegram_bot_commands())


def test_load_policy_defaults_to_dry_run_on_missing_file(tmp_path):
    from hermes_cli.authority import load_authority_policy

    policy = load_authority_policy(tmp_path / "missing.yml")

    assert policy.mode == "dry_run"
    assert policy.levels["L3"].approval == "user"
    assert policy.levels["L4"].approval == "explicit"


def test_authority_scorecard_detects_promotion_readiness(tmp_path):
    from hermes_cli.authority import AuthorityPaths, build_scorecard

    policy_path = tmp_path / "authority-policy.yml"
    policy_path.write_text(SAMPLE_POLICY)
    audit_path = tmp_path / "authority.log"
    audit_path.write_text("".join(
        f"2026-04-{20 + idx:02d} check observation_success=1 dry_run_match=1 rollback_verified=1\n"
        for idx in range(7)
    ))
    registry_dir = tmp_path / "agent-registry"
    registry_dir.mkdir()
    (registry_dir / "agent-codex-demo.json").write_text('{"id":"agent-codex-demo","tool":"codex","managed":true}')

    scorecard = build_scorecard(AuthorityPaths(policy_path=policy_path, audit_path=audit_path, registry_dir=registry_dir))

    assert scorecard.mode == "dry_run"
    assert scorecard.observation_days == 7
    assert scorecard.audit_log_missing == 0
    assert scorecard.dry_run_match_rate == pytest.approx(1.0)
    assert scorecard.rollback_verified is True
    assert scorecard.l2_candidate is True
    assert scorecard.l3_candidate is False
    assert scorecard.managed_agent_count == 1


def test_format_authority_report_is_short_korean_status(tmp_path):
    from hermes_cli.authority import AuthorityPaths, format_authority_report

    policy_path = tmp_path / "authority-policy.yml"
    policy_path.write_text(SAMPLE_POLICY)
    audit_path = tmp_path / "authority.log"
    audit_path.write_text("2026-04-26 check observation_success=1 dry_run_match=1 rollback_verified=1\n")
    registry_dir = tmp_path / "agent-registry"
    registry_dir.mkdir()

    report = format_authority_report(AuthorityPaths(policy_path=policy_path, audit_path=audit_path, registry_dir=registry_dir))

    assert "Hermes 권한 점검" in report
    assert "모드: dry_run" in report
    assert "승급 판단" in report
    assert len(report.splitlines()) <= 12


def test_enforcing_mode_fails_closed_to_dry_run(tmp_path):
    from hermes_cli.authority import load_authority_policy

    policy_path = tmp_path / "authority-policy.yml"
    policy_path.write_text("mode: enforcing\n")

    assert load_authority_policy(policy_path).mode == "dry_run"


def test_invalid_gate_values_do_not_crash_report(tmp_path):
    from hermes_cli.authority import AuthorityPaths, format_authority_report

    policy_path = tmp_path / "authority-policy.yml"
    policy_path.write_text("""
mode: dry_run
promotion_gates:
  observation_days: not-an-int
  min_observation_success_rate: not-a-float
  max_audit_log_missing: not-an-int
  min_dry_run_match_rate: not-a-float
""")
    audit_path = tmp_path / "authority.log"
    audit_path.write_text("2026-04-26 check observation_success=1 dry_run_match=1\n")
    registry_dir = tmp_path / "agent-registry"
    registry_dir.mkdir()

    report = format_authority_report(AuthorityPaths(policy_path=policy_path, audit_path=audit_path, registry_dir=registry_dir))

    assert "승급 판단: 승급 보류" in report
