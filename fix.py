"""Fix an issue in your own Python repository.

    python fix.py --repo ./my-project --issue "Dates before 1970 crash the parser"
    python fix.py --repo ./my-project --issue issue.md --test "python -m pytest -q tests/test_dates.py" --apply

The agent works on a copy inside the Docker sandbox; your repository changes only with --apply. Choose the model
with LLM_MODEL, LLM_BASE_URL and LLM_API_KEY, and turn components on with the AGENT_* switches (see the README).
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import sandbox
from agent import MODEL, run_agent
from utils import SKIP, changed, copy_back, diff_dirs

parser = argparse.ArgumentParser()
parser.add_argument("--repo", required=True, help="the repository to fix")
parser.add_argument("--issue", required=True, help="the issue, or a file that contains it")
parser.add_argument("--test", default="python -m pytest -q", help="the command that must pass")
parser.add_argument("--setup", help="run once, with network, before the agent (default: install requirements.txt)")
parser.add_argument("--apply", action="store_true", help="write the fix into the repository")
args = parser.parse_args()

repo = Path(args.repo).resolve()
issue = Path(args.issue).read_text(encoding="utf-8") if Path(args.issue).is_file() else args.issue
workdir = Path(tempfile.mkdtemp(prefix="fix-"))
shutil.copytree(repo, workdir, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*SKIP))
install = "python -m venv --system-site-packages .venv && pip install -q -r requirements.txt"  # PATH puts .venv first
setup = args.setup if args.setup is not None else install if (repo / "requirements.txt").exists() else ""
if setup:
    code, output = sandbox.run(workdir, setup, timeout=900, network=True)   # the only step with network
    if code:
        sys.exit(f"setup failed:\n{output}")

print(f"Fixing {repo.name} with {MODEL}...", flush=True)
run_agent(f"{issue}\n\nRun the tests with: {args.test}", workdir, seed=0, original=repo, code=".", test=args.test)
passed = sandbox.run(workdir, args.test, timeout=300)[0] == 0
print(diff_dirs(repo, workdir) or "No change.")
print(f"The tests {'pass' if passed else 'still fail'}.")
if args.apply and passed:
    copy_back(changed(repo, workdir), workdir, repo)
    print(f"Applied to {repo}.")
shutil.rmtree(workdir, ignore_errors=True)
