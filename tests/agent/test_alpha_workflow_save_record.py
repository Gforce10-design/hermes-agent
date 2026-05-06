"""Alpha workflow save-sync record tests."""

import pytest

from agent.alpha_workflow_save_record import AlphaSaveRecordError, build_save_record


def test_build_save_record_distinguishes_branch_push_from_mainline_update():
    record = build_save_record(
        task_id="alpha-task-1",
        work_type="code",
        review_gate="xrev",
        verification={"commands": ["pytest"], "result": "pass", "evidence": ["14 passed"]},
        artifacts={"obsidian": ["raw/dev/note.md"], "git_commit": "abc123"},
        branch_state={"branch": "main", "pushed": True, "upstream_or_mainline_updated": False},
        machine_state={"a8": "local", "desktop": "skipped", "g3": "not_applicable"},
    )

    assert record["branch_state"]["pushed"] is True
    assert record["branch_state"]["upstream_or_mainline_updated"] is False
    assert record["branch_state"]["note"] == "branch push is not mainline merge"
    assert record["machine_state"]["a8"] == "local"


def test_build_save_record_requires_all_machine_states():
    with pytest.raises(AlphaSaveRecordError, match="machine_state"):
        build_save_record(
            task_id="alpha-task-1",
            work_type="docs",
            review_gate="docs-light-review",
            verification={"commands": [], "result": "pass", "evidence": ["file exists"]},
            artifacts={"obsidian": ["raw/dev/note.md"]},
            branch_state={"branch": "main", "pushed": False, "upstream_or_mainline_updated": False},
            machine_state={"a8": "local"},
        )


def test_build_save_record_rejects_code_without_xrev_review_gate():
    with pytest.raises(AlphaSaveRecordError, match="xrev"):
        build_save_record(
            task_id="alpha-task-1",
            work_type="code",
            review_gate="docs-light-review",
            verification={"commands": ["pytest"], "result": "pass", "evidence": ["passed"]},
            artifacts={"git_commit": "abc123"},
            branch_state={"branch": "main", "pushed": False, "upstream_or_mainline_updated": False},
            machine_state={"a8": "local", "desktop": "skipped", "g3": "not_applicable"},
        )


def test_build_save_record_rejects_secret_like_artifacts():
    with pytest.raises(AlphaSaveRecordError, match="secret"):
        build_save_record(
            task_id="alpha-task-1",
            work_type="docs",
            review_gate="docs-light-review",
            verification={"commands": [], "result": "pass", "evidence": ["file exists"]},
            artifacts={"token": "secret-token-value"},
            branch_state={"branch": "main", "pushed": False, "upstream_or_mainline_updated": False},
            machine_state={"a8": "local", "desktop": "skipped", "g3": "not_applicable"},
        )
