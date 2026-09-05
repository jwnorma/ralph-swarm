"""Live compatibility tests for the beads CLI.

ralph-swarm shells out to `bd` (status, build scheduling, the generated
worker scripts) and its prompts teach agents a specific bd command
vocabulary. Beads evolves quickly; these tests exercise that exact
surface against the installed binary so a breaking bd release fails
here, loudly, instead of silently corrupting swarm runs mid-flight.

Skipped when `bd` is not installed.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("bd") is None, reason="bd CLI not installed")

JQ = shutil.which("jq")


def bd(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run a bd command with the same actor env workers use."""
    env = {**os.environ, "BEADS_ACTOR": "pytest", "BD_ACTOR": "pytest"}
    result = subprocess.run(  # noqa: S603, S607
        ["bd", *args], capture_output=True, text=True, cwd=cwd, env=env
    )
    if check and result.returncode != 0:
        pytest.fail(f"`bd {' '.join(args)}` exited {result.returncode}:\n{result.stderr.strip()}")
    return result


def bd_json(*args: str, cwd: Path):
    result = bd(*args, cwd=cwd)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"`bd {' '.join(args)}` printed non-JSON stdout:\n{result.stdout[:500]}")


def list_all(cwd: Path) -> list[dict]:
    """status.py's exact listing command."""
    return bd_json("list", "--json", "--flat", "--all", "--limit", "0", cwd=cwd)


def first_or_self(payload) -> dict:
    """bd show --json may return a bare object or a one-element list.

    ralph's worker scripts and Python both tolerate either shape via
    `if type == "array" then .[0] else . end`; mirror that here.
    """
    return payload[0] if isinstance(payload, list) else payload


def create_issue(cwd: Path, title: str, *extra_args: str) -> str:
    """Create an issue and return its id (ids are opaque, so diff the list)."""
    before = {issue["id"] for issue in list_all(cwd)}
    bd("create", title, *extra_args, cwd=cwd)
    new = [issue["id"] for issue in list_all(cwd) if issue["id"] not in before]
    assert len(new) == 1, f"expected exactly one new issue, got {new}"
    return new[0]


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A fresh git repo with an initialized beads database."""
    subprocess.run(["git", "init", "-q", "."], cwd=tmp_path, check=True)  # noqa: S603, S607
    subprocess.run(  # noqa: S603, S607
        ["git", "config", "beads.role", "maintainer"], cwd=tmp_path, check=True
    )
    bd("init", cwd=tmp_path)
    return tmp_path


def test_issue_lifecycle_claim_release_close(project: Path) -> None:
    """The full worker claim flow: create -> claim -> verify -> release -> close.

    Exercises every bd invocation build.py/cleanup.py/status.py make:
    """
    issue_id = create_issue(
        project,
        "Compat: lifecycle probe",
        "-t",
        "task",
        "-p",
        "P1",
        "--description",
        "compat test",
        "--acceptance",
        "this test passing",
    )

    # list shape used by status.py and plan progress
    issues = {i["id"]: i for i in list_all(project)}
    assert issue_id in issues
    issue = issues[issue_id]
    for field in ("id", "title", "status", "priority", "issue_type"):
        assert field in issue, f"list --json missing field: {field}"
    assert issue["status"] == "open"
    assert issue["issue_type"] == "task"
    assert issue["priority"] == 1, "P1 should map to numeric priority 1 in JSON output"

    # claim (build.py worker claim)
    bd("update", issue_id, "--status", "in_progress", "--assignee", "ralph-1", cwd=project)
    shown = first_or_self(bd_json("show", issue_id, "--json", cwd=project))
    assert shown["assignee"] == "ralph-1"
    assert shown["status"] == "in_progress"

    # cleanup.py's in-progress listing
    in_progress = bd_json(
        "list", "--status", "in_progress", "--json", "--flat", "--limit", "0", cwd=project
    )
    assert issue_id in {i["id"] for i in in_progress}

    # release (build.py failure path). Note: bd omits the assignee key once
    # cleared (jq in the worker scripts then yields null, which correctly
    # fails the "claimed_by != worker_id" check).
    bd("update", issue_id, "--status", "open", "--assignee", "", cwd=project)
    shown = first_or_self(bd_json("show", issue_id, "--json", cwd=project))
    assert shown["status"] == "open"
    assert shown.get("assignee", "") in ("", None)

    # close (worker completion)
    bd("close", issue_id, "--reason", "compat verified", cwd=project)
    shown = first_or_self(bd_json("show", issue_id, "--json", cwd=project))
    assert shown["status"] == "closed"


def test_ready_respects_dependencies(project: Path) -> None:
    """`bd ready` filtering and the `bd dep <blocker> --blocks <blocked>` form.

    The dep syntax was changed by bd 1.2 (the old `bd dep add X --blocks Y`
    errors with 'unknown flag'); the planning prompts teach agents the
    current form, so guard it here.
    """
    blocker_id = create_issue(project, "Compat: blocker", "-t", "task", "-p", "P1")
    blocked_id = create_issue(project, "Compat: blocked", "-t", "task", "-p", "P2")

    # build.md's availability command
    ready = bd_json("ready", "--unassigned", "--json", "--limit", "0", cwd=project)
    ready_ids = {i["id"] for i in ready}
    assert blocker_id in ready_ids
    assert blocked_id in ready_ids

    # current dependency syntax (positional order matters: blocker blocks blocked)
    bd("dep", blocker_id, "--blocks", blocked_id, cwd=project)

    ready = bd_json("ready", "--json", "--limit", "0", cwd=project)
    ready_ids = {i["id"] for i in ready}
    assert blocker_id in ready_ids, "unblocked issue should still be ready"
    assert blocked_id not in ready_ids, "blocked issue must not be ready"

    # unblocking re-admits the blocked issue
    bd("close", blocker_id, "--reason", "done", cwd=project)
    ready_ids = {i["id"] for i in bd_json("ready", "--json", "--limit", "0", cwd=project)}
    assert blocked_id in ready_ids


def test_epic_hierarchy(project: Path) -> None:
    """Epic creation and --parent linking as taught by the planning prompts."""
    epic_id = create_issue(project, "Epic: Compat", "-t", "epic", "-p", "P1")
    child_id = create_issue(
        project, "Compat: child task", "-t", "task", "-p", "P2", "--description", "child"
    )

    issues = {i["id"]: i for i in list_all(project)}
    assert issues[epic_id]["issue_type"] == "epic"
    assert issues[child_id]["issue_type"] == "task"

    bd("update", child_id, "--parent", epic_id, cwd=project)


@pytest.mark.skipif(JQ is None, reason="jq not installed")
def test_worker_script_jq_expressions(project: Path) -> None:
    """The generated worker scripts parse `bd show --json` with jq.

    build.py emits these exact expressions into worker-1.sh; if bd changes
    the show output shape in a way the dual-shape guard can't handle, the
    claim verification in the worker loop silently breaks.
    """
    issue_id = create_issue(project, "Compat: jq probe", "-t", "task")
    bd("update", issue_id, "--status", "in_progress", "--assignee", "ralph-2", cwd=project)

    raw = bd("show", issue_id, "--json", cwd=project).stdout
    for expression, expected in (
        ('if type == "array" then .[0].assignee else .assignee end', "ralph-2"),
        ('if type == "array" then .[0].status else .status end', "in_progress"),
    ):
        result = subprocess.run(  # noqa: S603, S607
            [JQ, "-r", expression], input=raw, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == expected, f"jq expression no longer matches: {expression}"
