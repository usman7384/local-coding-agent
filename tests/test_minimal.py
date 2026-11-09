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
TOKENS = {"tokens_in": 100, "tokens_out": 20}      # what a fake model call reports


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
    monkeypatch.setattr(agent, "ask_model", lambda messages, seed: (next(replies), TOKENS))
    monkeypatch.setattr(tools.sandbox, "run", lambda workdir, command: (0, "1 passed"))
    trace = agent.run_agent("Fix the bug.", tmp_path, seed=7, original=tmp_path)   # verify passes: one try
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


def test_steady_removes_run_to_run_noise():
    text = "==== 1 failed, 3 passed in 0.18s ====\nassert <Cache object at 0x7e9c8cac7620> == 3"
    assert utils.steady(text) == "==== 1 failed, 3 passed ====\nassert <Cache object at 0x...> == 3"


def test_open_files_panel_shows_current_file_content(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("x = 1\n")
    replies = iter([block("VIEW: a.py"), block("EDIT: a.py\n<<<<<<< OLD\nx = 1\n=======\nx = 2\n>>>>>>> NEW"), block("DONE")])
    seen = []                                       # the messages the model received at each step
    monkeypatch.setattr(agent, "ask_model", lambda messages, seed: (seen.append(messages) or next(replies), TOKENS))
    monkeypatch.setattr(tools.sandbox, "run", lambda workdir, command: (0, "1 passed"))  # verify passes
    agent.run_agent("Fix the bug.", tmp_path, seed=1, original=tmp_path)
    assert "Current content" not in seen[0][-1]["content"]              # nothing opened yet at step 1
    assert "   1| x = 1" in seen[1][-1]["content"]                      # after VIEW: the file is shown
    assert "   1| x = 2" in seen[2][-1]["content"]                      # after EDIT: the NEW content, fresh from disk


def test_provenance_names_the_commit_and_the_model(monkeypatch):
    answers = {"http://ollama/api/tags": {"models": [{"name": "m:latest", "digest": "abcdef1234567890"}]},
               "http://ollama/api/version": {"version": "1.2.3"}}
    monkeypatch.setattr(utils, "get_json", answers.get)                 # no real server needed
    stamp = utils.provenance("m", "http://ollama/v1")
    assert stamp["model_digest"] == "abcdef123456" and stamp["ollama"] == "1.2.3"
    assert len(stamp["commit"].removesuffix("-dirty")) >= 7             # a short git commit id


def test_functions_and_docstrings_find_what_make_tasks_needs():
    source = "def f(x):\n    return x\n\n\nclass C:\n    def g(self):\n        pass\n"
    assert utils.functions(source) == [("f", 1, 2), ("C.g", 6, 7)]                 # methods are named Class.method
    assert utils.docstrings('def test_a():\n    """A works."""\n\n\ndef helper():\n    pass\n') == {"test_a": "A works."}
    body = ["    def pay(self, amount, *, fee=0) -> int:", "        total = amount + fee", "        for item in []:",
            "            total += item", "        if total == 0:", "            return self.left"]
    assert utils.local_names(body) == ["amount", "fee", "item", "total"]          # no self, no attributes, no ==


def test_verify_retries_once_with_a_lesson_when_the_visible_tests_fail(tmp_path, monkeypatch):
    original, work = tmp_path / "original", tmp_path / "work"
    for folder in (original, work / "src"):
        folder.mkdir(parents=True)
        (folder / "a.py").write_text("x = 1\n")
    replies = iter([block("EDIT: src/a.py\n<<<<<<< OLD\nx = 1\n=======\nx = 2\n>>>>>>> NEW"), block("DONE"), block("DONE")])
    seen = []                                       # (messages, seed) of every model call
    monkeypatch.setattr(agent, "ask_model", lambda messages, seed: (seen.append((messages, seed)) or next(replies), TOKENS))
    failing = "F\nE   assert 2 == 3\nFAILED tests/test_visible.py::test_a - assert 2 == 3\n1 failed"
    monkeypatch.setattr(tools.sandbox, "run", lambda workdir, command: (1, failing))      # the visible tests fail
    trace = agent.run_agent("Fix it.", work, seed=1, original=original)
    assert [s["action"] for s in trace] == ["EDIT", "DONE", "RETRY", "DONE"]        # one retry, then no tries left
    messages, seed = seen[2]                        # the first call of the second try
    assert len(messages) == 2                       # a fresh conversation: system prompt and bug report only
    assert "Lesson from failed try 1" in messages[1]["content"] and "+x = 2" in messages[1]["content"]
    assert "E   assert 2 == 3" in messages[1]["content"]
    assert seed == 104                              # steps keep counting, so the second try samples differently


def test_stalls_count_test_runs_that_fail_exactly_like_the_last_failing_run():
    failing = "F\nE   assert 1 == 2\nFAILED tests/test_visible.py::test_a - assert 1 == 2\n1 failed"
    trace = [{"action": "BASH", "result": failing}, {"action": "BASH", "result": "a.py"},  # ls in between is ignored
             {"action": "BASH", "result": failing}, {"action": "EDIT", "result": "EDIT applied"}]
    assert utils.stalls(trace) == 1
    assert utils.fingerprint("3 passed") is None


def test_edit_refuses_to_change_the_tests(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_visible.py").write_text("assert 1 == 2\n")
    result = tools.edit(tmp_path, "tests/test_visible.py\n<<<<<<< OLD\nassert 1 == 2\n=======\nassert 1 == 1\n>>>>>>> NEW")
    assert result.startswith("EDIT refused") and (tmp_path / "tests" / "test_visible.py").read_text() == "assert 1 == 2\n"


@needs_docker
def test_bash_cannot_change_the_tests(tmp_path):
    workdir = fresh_copy(tmp_path)
    before = (workdir / "tests" / "test_visible.py").read_text()
    code, _ = tools.sandbox.run(workdir, "echo 'def test_ok(): pass' > tests/test_visible.py; touch tests/test_new.py")
    assert code != 0 and (workdir / "tests" / "test_visible.py").read_text() == before
    assert sorted(p.name for p in (workdir / "tests").glob("*.py")) == ["test_visible.py"]
    assert tools.sandbox.run(workdir, "echo ok > src/scratch.txt")[0] == 0            # src/ stays writable
