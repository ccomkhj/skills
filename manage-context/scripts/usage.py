#!/usr/bin/env python3
"""Mine Claude Code transcripts for how often each skill, MCP server, agent and built-in tool was used.

Reads every ~/.claude/projects/*/*.jsonl within a day window and counts:

- skills: Skill tool calls (the model chose it), typed slash commands and
  @-mentions (the user chose it), and the sessions that listed it at all
- MCP servers: tool calls per server prefix (``mcp__<prefix>__<tool>``) and
  the sessions that loaded the server (its deferred tool names appeared)
- agents: Agent tool calls per subagent type
- tools: calls per built-in tool name (every session loads them, so no "listed")

Counts only. No prompt, message or tool-input text is copied out.

    usage.py [--days 90] [--project DIR]      # prints a summary as JSON
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
SLASH_RE = re.compile(r"<command-name>/([^<\s]+)</command-name>")
MARKERS = (
    '"name":"Skill"',
    '"name":"mcp__',
    '"name":"Agent"',
    '"type":"tool_use"',
    "<command-name>",
    '"skill_mention"',
    '"skill_listing"',
    '"deferred_tools_delta"',
)


def _ts(line: dict) -> str:
    return line.get("timestamp") or ""


class Stat:
    """Counts for one item, kept separately for all projects and for this project."""

    __slots__ = ("model", "user", "listed", "sessions_model", "sessions_user", "last_model", "last_user")

    def __init__(self):
        self.model = 0
        self.user = 0
        self.listed = 0
        self.sessions_model: set[str] = set()
        self.sessions_user: set[str] = set()
        self.last_model = ""
        self.last_user = ""

    def hit(self, who: str, sid: str, ts: str):
        if who == "model":
            self.model += 1
            self.sessions_model.add(sid)
            self.last_model = max(self.last_model, ts)
        else:
            self.user += 1
            self.sessions_user.add(sid)
            self.last_user = max(self.last_user, ts)

    def export(self) -> dict:
        return {
            "model": self.model,
            "user": self.user,
            "listed": self.listed,
            "sessions_model": len(self.sessions_model),
            "sessions_user": len(self.sessions_user),
            "last_model": self.last_model[:10],
            "last_user": self.last_user[:10],
        }


def _listing_names(a: dict) -> list[str]:
    if a.get("names"):
        return list(a["names"])
    out = []
    for ln in (a.get("content") or "").splitlines():
        if ln.startswith("- "):
            out.append(ln[2:].split(": ", 1)[0].rstrip(":"))
    return out


def collect(days: int, project: Path, root: Path = PROJECTS) -> dict:
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).isoformat()
    project_s = str(project.resolve())
    skills: dict[str, dict[str, Stat]] = {}
    mcp: dict[str, dict[str, Stat]] = {}
    agents: dict[str, dict[str, Stat]] = {}
    tools: dict[str, dict[str, Stat]] = {}
    sessions: dict[str, set[str]] = {"all": set(), "here": set()}

    def stat(store, name, scope) -> Stat:
        return store.setdefault(name, {}).setdefault(scope, Stat())

    for f in sorted(root.glob("*/*.jsonl")):
        try:
            if dt.datetime.fromtimestamp(f.stat().st_mtime, dt.timezone.utc).isoformat() < since:
                continue
            lines = f.open(errors="replace")
        except OSError:
            continue
        sid = f.stem
        cwd = None
        listed_this: set[str] = set()
        loaded_mcp: set[str] = set()
        with lines:
            for raw in lines:
                if cwd is None and '"cwd":"' in raw:
                    m = re.search(r'"cwd":"([^"]*)"', raw)
                    cwd = m.group(1) if m else ""
                if not any(k in raw for k in MARKERS):
                    continue
                try:
                    d = json.loads(raw)
                except ValueError:
                    continue
                ts = _ts(d)
                if not ts or ts < since:
                    continue
                scopes = ["all"] + (["here"] if (cwd or d.get("cwd")) == project_s else [])
                for s in scopes:
                    sessions[s].add(sid)
                t = d.get("type")
                if t == "attachment":
                    a = d.get("attachment") or {}
                    if a.get("type") == "skill_listing":
                        for n in _listing_names(a):
                            if n not in listed_this:
                                listed_this.add(n)
                                for s in scopes:
                                    stat(skills, n, s).listed += 1
                    elif a.get("type") == "deferred_tools_delta":
                        for n in a.get("addedNames") or []:
                            if n.startswith("mcp__"):
                                prefix = n[5:].rsplit("__", 1)[0]
                                if prefix not in loaded_mcp:
                                    loaded_mcp.add(prefix)
                                    for s in scopes:
                                        stat(mcp, prefix, s).listed += 1
                    elif a.get("type") == "skill_mention" and a.get("skillName"):
                        for s in scopes:
                            stat(skills, a["skillName"], s).hit("user", sid, ts)
                    continue
                msg = d.get("message") or {}
                content = msg.get("content")
                if t == "user":
                    text = content if isinstance(content, str) else json.dumps(content)
                    for n in SLASH_RE.findall(text):
                        for s in scopes:
                            stat(skills, n, s).hit("user", sid, ts)
                    continue
                if t != "assistant" or not isinstance(content, list):
                    continue
                for b in content:
                    if b.get("type") != "tool_use":
                        continue
                    name = b.get("name") or ""
                    inp = b.get("input") or {}
                    if name == "Skill" and inp.get("skill"):
                        for s in scopes:
                            stat(skills, inp["skill"], s).hit("model", sid, ts)
                    elif name.startswith("mcp__"):
                        prefix = name[5:].rsplit("__", 1)[0]
                        for s in scopes:
                            stat(mcp, prefix, s).hit("model", sid, ts)
                    elif name == "Agent" and inp.get("subagent_type"):
                        for s in scopes:
                            stat(agents, inp["subagent_type"], s).hit("model", sid, ts)
                    if name and not name.startswith("mcp__"):
                        for s in scopes:
                            stat(tools, name, s).hit("model", sid, ts)

    def export(store):
        return {
            n: {s: st.export() for s, st in by.items()} for n, by in sorted(store.items())
        }

    return {
        "days": days,
        "since": since[:10],
        "sessions": {k: len(v) for k, v in sessions.items()},
        "skills": export(skills),
        "mcp": export(mcp),
        "agents": export(agents),
        "tools": export(tools),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--project", default=".")
    args = ap.parse_args()
    print(json.dumps(collect(args.days, Path(args.project)), indent=1))


if __name__ == "__main__":
    main()
