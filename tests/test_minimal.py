"""Tests for the harness itself. Tests marked needs_docker need Docker and the sandbox image."""

import io
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


def call(name, **args):
    """A fake model reply that calls one tool, the way the chat API returns it."""
    return {"content": "Some reasoning.", "tool_calls": [{"id": f"call_{name}", "type": "function",
                                                          "function": {"name": name, "arguments": json.dumps(args)}}]}


def answer(text="Fixed."):
    """A fake model reply without a tool call: the agent is done."""
    return {"content": text}


def fake_model(monkeypatch, replies, seen=None):
    """Replace the model with a list of replies; record (messages, tool names, seed) of every call in `seen`."""
    replies, seen = iter(replies), seen if seen is not None else []
    monkeypatch.setattr(agent, "ask_model", lambda messages, tools, seed: (
        seen.append((messages, [t.__name__ for t in tools], seed)) or next(replies), TOKENS))


def test_tool_specs_and_calls(tmp_path):
    spec = utils.tool_spec(tools.view)["function"]
    assert spec["name"] == "view" and spec["parameters"]["required"] == ["path"]        # start and end are optional
    assert spec["parameters"]["properties"]["start"] == {"type": "integer"}
    (tmp_path / "a.py").write_text("x = 1\n")
    run = lambda name, arguments: utils.call_tool(  # noqa: E731
        {"view": tools.view}, tmp_path, {"function": {"name": name, "arguments": arguments}})
    assert run("view", '{"path": "a.py"}') == ("view", {"path": "a.py"}, "   1| x = 1")
    assert run("delete", '{"path": "a.py"}')[0] == "malformed"                # unknown tool: nothing runs
    assert run("view", '{"path": ')[0] == "malformed"                         # arguments are not JSON
    assert run("view", '{"file": "a.py"}')[0] == "malformed"                  # arguments do not fit the tool
    assert "The tools are: view" in run("view", "{}")[2]                      # the model is told what exists


def test_edit_file(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\ny = 2\n")
    assert tools.edit(tmp_path, "a.py", "x = 1", "x = 3").startswith("edit applied")
    assert (tmp_path / "a.py").read_text() == "x = 3\ny = 2\n"
    assert "appears 0 times" in tools.edit(tmp_path, "a.py", "z = 9", "z = 1")
    assert "does not exist" in tools.edit(tmp_path, "b.py", "x", "y")
    assert "does not exist" in tools.edit(tmp_path, "../a.py", "x", "y")


def test_edit_tolerates_wrong_indentation(tmp_path):
    (tmp_path / "b.py").write_text("def f(x):\n    if x:\n        return 1\n    return 0\n")
    # old and new are written with 4 spaces too few; the edit still lands, re-indented to fit the file.
    result = tools.edit(tmp_path, "b.py", "if x:\n    return 1", "if not x:\n    return 1")
    assert result == "edit applied to b.py. (indentation adjusted)"
    assert (tmp_path / "b.py").read_text() == "def f(x):\n    if not x:\n        return 1\n    return 0\n"


def test_run_agent_with_a_fake_model(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("x = 1\n")
    fake_model(monkeypatch, [call("run", command="ls"),                    # malformed: no such tool
                             call("bash", command="python -m pytest"),
                             call("edit", path="a.py", old="x = 1", new="x = 2"),
                             answer()])
    monkeypatch.setattr(tools.sandbox, "run", lambda workdir, command: (0, "1 passed"))
    trace = agent.run_agent("Fix the bug.", tmp_path, seed=7, original=tmp_path)   # verify passes: one try
    assert [s["action"] for s in trace] == ["malformed", "bash", "edit", "done"]
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
    assert tools.view(tmp_path, "src/a.py", 4, 5).splitlines() == ["   4| def g():", "   5|     return f(2)"]
    assert "view failed" in tools.view(tmp_path, "../a.py")
    assert tools.search(tmp_path, "f(").splitlines() == ["src/a.py:1: def f(x):", "src/a.py:5: return f(2)"]
    assert "No line contains" in tools.search(tmp_path, "zzz")


def test_edit_ignores_line_numbers_copied_from_view(tmp_path):
    (tmp_path / "c.py").write_text("def f(x):\n    return x - 1\n")
    assert tools.edit(tmp_path, "c.py", "   2|     return x - 1", "   2|     return x + 1").startswith("edit applied")
    assert (tmp_path / "c.py").read_text() == "def f(x):\n    return x + 1\n"


def test_edit_refuses_to_break_python_syntax(tmp_path):
    (tmp_path / "d.py").write_text("def f(x):\n    if x:\n        return 1\n    return 0\n")
    # Replacing only the body leaves the "if" with nothing under it: refused, file untouched.
    result = tools.edit(tmp_path, "d.py", "        return 1\n", "")
    assert result.startswith("edit refused") and "valid Python" in result
    assert (tmp_path / "d.py").read_text() == "def f(x):\n    if x:\n        return 1\n    return 0\n"
    assert utils.syntax_error("x = (") and utils.syntax_error("x = 1") is None


def test_steady_removes_run_to_run_noise():
    text = "==== 1 failed, 3 passed in 0.18s ====\nassert <Cache object at 0x7e9c8cac7620> == 3"
    assert utils.steady(text) == "==== 1 failed, 3 passed ====\nassert <Cache object at 0x...> == 3"


def test_open_files_panel_shows_current_file_content(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("x = 1\n")
    seen = []                                       # what the model received at each step
    fake_model(monkeypatch, [call("view", path="a.py"), call("edit", path="a.py", old="x = 1", new="x = 2"), answer()],
               seen)
    monkeypatch.setattr(tools.sandbox, "run", lambda workdir, command: (0, "1 passed"))  # verify passes
    agent.run_agent("Fix the bug.", tmp_path, seed=1, original=tmp_path)
    assert "Current content" not in seen[0][0][-1]["content"]           # nothing opened yet at step 1
    assert "   1| x = 1" in seen[1][0][-1]["content"]                   # after view: the file is shown
    assert "   1| x = 2" in seen[2][0][-1]["content"]                   # after edit: the new content, fresh from disk
    assert [m["role"] for m in seen[1][0][2:4]] == ["assistant", "tool"]  # each call is answered by its result


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
    seen = []                                       # (messages, tools, seed) of every model call
    fake_model(monkeypatch, [call("edit", path="src/a.py", old="x = 1", new="x = 2"), answer(), answer()], seen)
    failing = "F\nE   assert 2 == 3\nFAILED tests/test_visible.py::test_a - assert 2 == 3\n1 failed"
    monkeypatch.setattr(tools.sandbox, "run", lambda workdir, command: (1, failing))      # the visible tests fail
    trace = agent.run_agent("Fix it.", work, seed=1, original=original)
    assert [s["action"] for s in trace] == ["edit", "done", "RETRY", "done"]        # one retry, then no tries left
    messages, _, seed = seen[2]                     # the first call of the second try
    assert len(messages) == 2                       # a fresh conversation: system prompt and bug report only
    assert "Lesson from failed try 1" in messages[1]["content"] and "+x = 2" in messages[1]["content"]
    assert "E   assert 2 == 3" in messages[1]["content"]
    assert seed == 104                              # steps keep counting, so the second try samples differently


def test_stalls_count_test_runs_that_fail_exactly_like_the_last_failing_run():
    failing = "F\nE   assert 1 == 2\nFAILED tests/test_visible.py::test_a - assert 1 == 2\n1 failed"
    trace = [{"action": "bash", "result": failing}, {"action": "bash", "result": "a.py"},  # ls in between is ignored
             {"action": "bash", "result": failing}, {"action": "edit", "result": "edit applied"}]
    assert utils.stalls(trace) == 1
    assert utils.fingerprint("3 passed") is None


def test_edit_refuses_to_change_the_tests(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_visible.py").write_text("assert 1 == 2\n")
    result = tools.edit(tmp_path, "tests/test_visible.py", "assert 1 == 2", "assert 1 == 1")
    assert result.startswith("edit refused") and (tmp_path / "tests" / "test_visible.py").read_text() == "assert 1 == 2\n"


@needs_docker
def test_bash_cannot_change_the_tests(tmp_path):
    workdir = fresh_copy(tmp_path)
    before = (workdir / "tests" / "test_visible.py").read_text()
    code, _ = tools.sandbox.run(workdir, "echo 'def test_ok(): pass' > tests/test_visible.py; touch tests/test_new.py")
    assert code != 0 and (workdir / "tests" / "test_visible.py").read_text() == before
    assert sorted(p.name for p in (workdir / "tests").glob("*.py")) == ["test_visible.py"]
    assert tools.sandbox.run(workdir, "echo ok > src/scratch.txt")[0] == 0            # src/ stays writable


def test_explorer_switch_adds_a_read_only_guess(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    seen = []
    fake_model(monkeypatch, [call("view", path="src/a.py"), answer("src/a.py x: should be 2"), answer()], seen)
    monkeypatch.setattr(tools.sandbox, "run", lambda workdir, command: (0, "1 passed"))
    monkeypatch.setattr(agent, "EXPLORER", True)
    trace = agent.run_agent("Fix it.", tmp_path, seed=1, original=tmp_path / "src")
    assert [s["action"] for s in trace] == ["EXPLORE", "done"] and trace[0]["result"] == "src/a.py x: should be 2"
    assert seen[0][1] == ["view", "search"] and seen[2][1] == ["bash", "view", "search", "edit"]   # read-only first
    assert "Its guess: src/a.py x: should be 2" in seen[2][0][1]["content"]          # the fixer gets the guess


def test_critic_switch_rejects_only_with_a_failing_assert(tmp_path, monkeypatch):
    original, work = tmp_path / "original", tmp_path / "work"
    for folder in (original, work / "src"):
        folder.mkdir(parents=True)
        (folder / "a.py").write_text("x = 1\n")
    seen = []
    fake_model(monkeypatch, [call("edit", path="src/a.py", old="x = 1", new="x = 2"), answer(),   # try 1: green
                             call("reject", check="from a import x; assert x == 3"),            # the critic objects
                             answer()], seen)                                                   # try 2
    monkeypatch.setattr(tools.sandbox, "run", lambda workdir, command: (     # its assert fails, the tests pass
        (1, "AssertionError") if "python -c" in command else (0, "1 passed")))
    monkeypatch.setattr(agent, "CRITIC", True)
    trace = agent.run_agent("Fix it.", work, seed=1, original=original)
    assert [s["action"] for s in trace] == ["edit", "done", "REVIEW", "RETRY", "done"]
    assert trace[2]["result"].startswith("REJECT: from a import x") and seen[2][1] == ["reject"]
    assert "a reviewer rejected the change" in seen[3][0][1]["content"]              # the lesson carries the reason


def test_gateway_retries_transient_failures_only(monkeypatch):
    calls = []
    answer = {"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 5, "completion_tokens": 1}}

    class Response(io.BytesIO):
        def __enter__(self):
            return self

    def urlopen(request, timeout):
        calls.append(request)
        if len(calls) == 1:
            raise agent.urllib.error.HTTPError(agent.URL, 503, "busy", {}, None)   # a server error: retried
        return Response(json.dumps(answer).encode())
    monkeypatch.setattr(agent.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(agent.time, "sleep", lambda seconds: None)
    assert agent.ask_model([], [], seed=1) == ({"content": "ok"}, {"tokens_in": 5, "tokens_out": 1})
    assert len(calls) == 2 and "tools" not in json.loads(calls[0].data)           # no tools: none are sent
    assert utils.transient(agent.urllib.error.HTTPError(agent.URL, 429, "", {}, None))
    assert not utils.transient(agent.urllib.error.HTTPError(agent.URL, 401, "", {}, None))  # a wrong key: no retry
