"""Tests for the harness itself. Tests marked needs_docker need Docker and the sandbox image."""

import json
import shutil
import subprocess
import sys

import pytest

import agent
import tools
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
    assert tools.edit(tmp_path, "a.py\n<<<<<<< OLD\nx = 1\n=======\nx = 3\n>>>>>>> NEW").startswith("EDIT applied")
    assert (tmp_path / "a.py").read_text() == "x = 3\ny = 2\n"
    assert "appears 0 times" in tools.edit(tmp_path, "a.py\n<<<<<<< OLD\nz = 9\n=======\nz = 1\n>>>>>>> NEW")
    assert "does not exist" in tools.edit(tmp_path, "b.py\n<<<<<<< OLD\nx\n=======\ny\n>>>>>>> NEW")
    assert "does not exist" in tools.edit(tmp_path, "../a.py\n<<<<<<< OLD\nx\n=======\ny\n>>>>>>> NEW")
    assert "EDIT failed" in tools.edit(tmp_path, "a.py\nx = 3")


def test_edit_tolerates_wrong_indentation(tmp_path):
    (tmp_path / "b.py").write_text("def f(x):\n    if x:\n        return 1\n    return 0\n")
    # OLD and NEW are written with 4 spaces too few; the edit still lands, re-indented to fit the file.
    result = tools.edit(tmp_path, "b.py\n<<<<<<< OLD\nif x:\n    return 1\n=======\nif not x:\n    return 1\n>>>>>>> NEW")
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
    monkeypatch.setattr(tools.sandbox, "run", lambda workdir, command: (0, "1 passed"))
    trace = agent.run_agent("Fix the bug.", tmp_path, seed=7)
    assert [s["action"] for s in trace] == ["MALFORMED", "BASH", "EDIT", "DONE"]
    assert (tmp_path / "a.py").read_text() == "x = 2\n"


def test_long_output_is_shortened():
    half = tools.MAX_OUTPUT // 2
    text = "a" * (half + 250) + "b" * (half + 250)
    short = utils.shorten(text, tools.MAX_OUTPUT)
    assert short.startswith("a" * half) and short.endswith("b" * half) and "500 characters cut" in short


def test_every_task_file_is_shown_whole():
    for source in TASK.parent.glob("*/repo/src/*.py"):
        assert len(source.read_text(encoding="utf-8")) <= tools.MAX_OUTPUT, source


def docker_ready():
    try:
        image = subprocess.run(["docker", "image", "inspect", tools.sandbox.IMAGE], capture_output=True, timeout=30)
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


def test_pass_at_k_and_pass_hat_k():
    assert utils.pass_at_k(2, 5, 1) == utils.pass_hat_k(2, 5, 1) == 0.4   # for k = 1 both are just 2/5
    assert utils.pass_at_k(2, 5, 4) == 1.0      # 4 tries out of 5 must include one of the 2 passes
    assert utils.pass_hat_k(4, 5, 5) == 0.0     # one failure means "all 5 pass" never happened
    assert utils.pass_hat_k(5, 5, 3) == 1.0


def test_bootstrap_is_repeatable_and_brackets_the_mean():
    data = [[True, False], [True, True], [False, False], [True, False]]
    rate = lambda tasks: sum(x for t in tasks for x in t) / sum(len(t) for t in tasks)  # noqa: E731
    low, high = utils.bootstrap(data, rate)
    assert (low, high) == utils.bootstrap(data, rate)   # same seed, same interval
    assert low <= rate(data) <= high


def test_stats_script_tells_real_differences_from_noise(tmp_path):
    def write(folder, passed):                      # 15 tasks x 5 repeats, passed(task, repeat) -> bool
        (tmp_path / folder).mkdir()
        rows = [{"task": f"t{t}", "repeat": r, "passed": passed(t, r)} for r in range(5) for t in range(15)]
        (tmp_path / folder / "results.jsonl").write_text("\n".join(map(json.dumps, rows)))
    write("a", lambda t, r: (t + r) % 4 == 0)       # about 25% pass, varying by repeat
    write("b", lambda t, r: (t + r) % 4 != 3)       # about 75% pass: a big, consistent improvement
    run = lambda *folders: subprocess.run(          # noqa: E731
        [sys.executable, "stats.py", *[str(tmp_path / f) for f in folders]],
        capture_output=True, text=True, encoding="utf-8", cwd=TASK.parents[1]).stdout
    assert "pass^k" in run("a") and "noise band" in run("a")
    assert "REAL difference" in run("a", "b")
    assert "within noise" in run("a", "a")


def test_view_and_search(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("def f(x):\n    return x + 1\n\ndef g():\n    return f(2)\n")
    assert tools.view(tmp_path, "src/a.py").splitlines()[1] == "   2|     return x + 1"   # numbered lines
    assert tools.view(tmp_path, "src/a.py 4-5").splitlines() == ["   4| def g():", "   5|     return f(2)"]
    assert "VIEW failed" in tools.view(tmp_path, "../a.py") and "VIEW failed" in tools.view(tmp_path, "src/a.py x-y")
    assert tools.search(tmp_path, "f(").splitlines() == ["src/a.py:1: def f(x):", "src/a.py:5: return f(2)"]
    assert "No line contains" in tools.search(tmp_path, "zzz")
    assert agent.parse_action(block("VIEW: src/a.py 4-5")) == ("VIEW", "src/a.py 4-5")   # new tools parse too
    assert agent.parse_action(block("SEARCH: def g")) == ("SEARCH", "def g")


def test_edit_ignores_line_numbers_copied_from_view(tmp_path):
    (tmp_path / "c.py").write_text("def f(x):\n    return x - 1\n")
    edit = "c.py\n<<<<<<< OLD\n   2|     return x - 1\n=======\n   2|     return x + 1\n>>>>>>> NEW"
    assert tools.edit(tmp_path, edit).startswith("EDIT applied")
    assert (tmp_path / "c.py").read_text() == "def f(x):\n    return x + 1\n"


def test_edit_refuses_to_break_python_syntax(tmp_path):
    (tmp_path / "d.py").write_text("def f(x):\n    if x:\n        return 1\n    return 0\n")
    # Replacing only the body leaves the "if" with nothing under it: refused, file untouched.
    result = tools.edit(tmp_path, "d.py\n<<<<<<< OLD\n        return 1\n=======\n>>>>>>> NEW")
    assert result.startswith("EDIT refused") and "valid Python" in result
    assert (tmp_path / "d.py").read_text() == "def f(x):\n    if x:\n        return 1\n    return 0\n"
    assert utils.syntax_error("x = (") and utils.syntax_error("x = 1") is None
