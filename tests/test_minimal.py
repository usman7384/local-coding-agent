"""Tests for the harness itself. The last three need Docker and the sandbox image."""

import shutil
import subprocess

import pytest

import agent
import utils
from grade import grade

TASK = agent.Path(__file__).resolve().parents[1] / "tasks" / "ringlog-d1"


def block(body):
    return f"Some reasoning.\n```\n{body}\n```"


def test_parse_action():
    assert agent.parse_action(block("BASH: ls src")) == ("BASH", "ls src")
    assert agent.parse_action(block("DONE")) == ("DONE", "")
    assert agent.parse_action("no block at all") == ("MALFORMED", "")
    assert agent.parse_action(block("BASH: ls") + block("DONE")) == ("MALFORMED", "")  # two actions
    assert agent.parse_action(block("RUN: ls")) == ("MALFORMED", "")     # unknown action
    quoted_code = "Here is the bug:\n```python\nx = 1\n```\n" + block("DONE")
    assert agent.parse_action(quoted_code) == ("DONE", "")              # other code blocks are ignored


def test_edit_file(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\ny = 2\n")
    assert agent.edit(tmp_path, "a.py\n<<<<<<< OLD\nx = 1\n=======\nx = 3\n>>>>>>> NEW").startswith("EDIT applied")
    assert (tmp_path / "a.py").read_text() == "x = 3\ny = 2\n"
    assert "appears 0 times" in agent.edit(tmp_path, "a.py\n<<<<<<< OLD\nz = 9\n=======\nz = 1\n>>>>>>> NEW")
    assert "does not exist" in agent.edit(tmp_path, "b.py\n<<<<<<< OLD\nx\n=======\ny\n>>>>>>> NEW")
    assert "does not exist" in agent.edit(tmp_path, "../a.py\n<<<<<<< OLD\nx\n=======\ny\n>>>>>>> NEW")
    assert "EDIT failed" in agent.edit(tmp_path, "a.py\nx = 3")


def test_edit_tolerates_wrong_indentation(tmp_path):
    (tmp_path / "b.py").write_text("def f(x):\n    if x:\n        return 1\n    return 0\n")
    # OLD and NEW are written with 4 spaces too few; the edit still lands, re-indented to fit the file.
    result = agent.edit(tmp_path, "b.py\n<<<<<<< OLD\nif x:\n    return 1\n=======\nif not x:\n    return 1\n>>>>>>> NEW")
    assert result == "EDIT applied to b.py. (indentation adjusted)"
    assert (tmp_path / "b.py").read_text() == "def f(x):\n    if not x:\n        return 1\n    return 0\n"


def test_run_agent_with_a_fake_model(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("x = 1\n")
    replies = iter([
        "I will look around.",                                    # malformed: no action block
        block("BASH: python -m pytest"),
        block("EDIT: a.py\n<<<<<<< OLD\nx = 1\n=======\nx = 2\n>>>>>>> NEW"),
        block("DONE"),
    ])
    monkeypatch.setattr(agent, "ask_model", lambda messages, seed: next(replies))
    monkeypatch.setattr(agent.sandbox, "run", lambda workdir, command: (0, "1 passed"))
    trace = agent.run_agent("Fix the bug.", tmp_path, seed=7)
    assert [s["action"] for s in trace] == ["MALFORMED", "BASH", "EDIT", "DONE"]
    assert (tmp_path / "a.py").read_text() == "x = 2\n"


def test_long_output_is_shortened():
    half = agent.MAX_OUTPUT // 2
    text = "a" * (half + 250) + "b" * (half + 250)
    short = utils.shorten(text, agent.MAX_OUTPUT)
    assert short.startswith("a" * half) and short.endswith("b" * half) and "500 characters cut" in short


def test_every_task_file_is_shown_whole():
    for source in TASK.parent.glob("*/repo/src/*.py"):
        assert len(source.read_text(encoding="utf-8")) <= agent.MAX_OUTPUT, source


def docker_ready():
    try:
        image = subprocess.run(["docker", "image", "inspect", agent.sandbox.IMAGE], capture_output=True, timeout=30)
        return image.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


needs_docker = pytest.mark.skipif(not docker_ready(), reason="needs Docker and the sandbox image")


def fresh_copy(tmp_path):
    shutil.copytree(TASK / "repo", tmp_path, dirs_exist_ok=True)
    return tmp_path


@needs_docker
def test_correct_solution_passes(tmp_path):
    workdir = fresh_copy(tmp_path)
    shutil.copytree(TASK / "solution", workdir / "src", dirs_exist_ok=True)
    assert grade(TASK, workdir) == {"passed": True, "visible_ok": True, "hidden_ok": True, "tampered": False}


@needs_docker
def test_buggy_code_fails(tmp_path):
    result = grade(TASK, fresh_copy(tmp_path))
    assert not result["passed"] and not result["visible_ok"] and not result["hidden_ok"]


@needs_docker
def test_editing_the_tests_is_caught(tmp_path):
    workdir = fresh_copy(tmp_path)
    (workdir / "tests" / "test_visible.py").write_text("def test_ok():\n    assert True\n")
    result = grade(TASK, workdir)
    assert result["tampered"] and not result["passed"]
