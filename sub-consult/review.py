#!/usr/bin/env python3
"""Run one sub-consult reviewer from panel.toml and print its review.

  review.py list                                   panel roster, one reviewer per line
  review.py start  <name> <brief-file>             first review: persona + contract + brief
  review.py resume <name> <session> <message-file> re-review in the same CLI session

Output: a `session: <id>` line, a blank line, then the review text verbatim.
`session: none` means the review landed but can't be resumed.
On failure: `UNAVAILABLE: <reason>` plus the stderr tail, exit 1.
Reviewers always run at the git root of the current directory; outside a git repo it refuses.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

try:
    import tomllib
except ImportError:
    print(f"UNAVAILABLE: review.py needs Python 3.11+ for tomllib (running {sys.version.split()[0]})")
    sys.exit(1)

PANEL = Path(__file__).with_name("panel.toml")
TIMEOUT = 1800  # seconds per reviewer call

# Claude reviewers run under bypassPermissions; deny rules still hold there, so
# block anything that would change the working tree, index, or remote.
CLAUDE_DENY = ["Bash(rm:*)", "Bash(git push:*)", "Bash(git commit:*)", "Bash(git stash:*)",
               "Bash(git checkout:*)", "Bash(git restore:*)", "Bash(git switch:*)",
               "Bash(git reset:*)", "Bash(git clean:*)"]


def load():
    with PANEL.open("rb") as f:
        return tomllib.load(f)


def fail(reason, stderr="") -> NoReturn:
    print(f"UNAVAILABLE: {reason}")
    if stderr:
        print("\n".join(stderr.strip().splitlines()[-10:]))
    sys.exit(1)


def repo_root():
    # Pinned so a drifted shell cwd can't point a reviewer at the wrong (or an empty) tree.
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if p.returncode:
        fail(f"not inside a git repo ({os.getcwd()}); run from the repo under review")
    return p.stdout.strip()


def run(cmd, prompt):
    try:
        return subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              timeout=TIMEOUT, cwd=repo_root())
    except FileNotFoundError:
        fail(f"{cmd[0]} not on PATH")
    except subprocess.TimeoutExpired:
        fail(f"timed out after {TIMEOUT}s")


def run_claude(r, prompt, session=None):
    cmd = ["claude", "-p", "--model", r["model"], "--effort", r["effort"],
           "--output-format", "json", "--tools", "Read,Grep,Glob,Bash",
           "--permission-mode", "bypassPermissions",
           # no --mcp-config, so no MCP servers: --tools alone doesn't block them.
           "--strict-mcp-config", "--disallowedTools", *CLAUDE_DENY]
    if session:
        cmd += ["--resume", session]
    p = run(cmd, prompt)
    try:
        out = json.loads(p.stdout)
    except json.JSONDecodeError:
        fail(f"claude exited {p.returncode} without JSON output", p.stderr or p.stdout)
    if out.get("is_error") or not out.get("result"):
        fail(f"claude error ({out.get('subtype', 'no result')})", str(out.get("result") or p.stderr))
    return out.get("session_id") or "none", out["result"]


def run_codex(r, prompt, session=None):
    # --ignore-user-config drops the user's MCP servers and --disable apps the built-in
    # connectors; auth still comes from CODEX_HOME.
    effort = ["--ignore-user-config", "--disable", "apps", "-c", f"model_reasoning_effort={r['effort']}"]
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
        last = f.name
    if session:
        # resume keeps the session's model; the sandbox must be re-asserted.
        cmd = ["codex", "exec", "resume", "--skip-git-repo-check", *effort,
               "-c", 'sandbox_mode="read-only"', "-o", last, session, "-"]
    else:
        cmd = ["codex", "exec", "-m", r["model"], *effort, "-s", "read-only",
               "--skip-git-repo-check", "-C", repo_root(), "-o", last, "-"]
    try:
        p = run(cmd, prompt)
        text = Path(last).read_text().strip()
    finally:
        Path(last).unlink(missing_ok=True)
    m = re.search(r"^session id: (\S+)", p.stderr, re.M)
    if p.returncode:
        fail(f"codex exited {p.returncode}", p.stderr)
    if not text:
        fail("codex produced no final message", p.stderr)
    return m.group(1) if m else "none", text


ENGINES = {"claude": run_claude, "codex": run_codex}


def reviewer(cfg, name):
    r = cfg["reviewer"].get(name)
    if r is None:
        fail(f"no reviewer '{name}' in {PANEL} (have: {', '.join(cfg['reviewer'])})")
    if r["engine"] not in ENGINES:
        fail(f"reviewer '{name}': unknown engine '{r['engine']}'")
    return r


def main(argv):
    cfg = load()
    match argv:
        case ["list"]:
            for name, r in cfg["reviewer"].items():
                print(f"{name}\t{r['engine']}/{r['model']}\t{r['effort']}\t{r['prefix']}\t{r['lane']}")
            return
        case ["start", name, brief]:
            r = reviewer(cfg, name)
            contract = cfg["contract"]["text"].replace("{prefix}", r["prefix"])
            prompt = f"{r['persona'].strip()}\n\n{contract.strip()}\n\n{Path(brief).read_text()}"
            session = None
        case ["resume", name, session, message]:
            r = reviewer(cfg, name)
            prompt = Path(message).read_text()
        case _:
            print(__doc__, file=sys.stderr)
            sys.exit(2)
    sid, text = ENGINES[r["engine"]](r, prompt, session)
    print(f"session: {sid}\n\n{text}")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as e:  # every failure must surface as UNAVAILABLE, not a bare traceback
        fail(f"{type(e).__name__}: {e}")
