#!/usr/bin/env python3
"""Measure what a Claude Code session loaded into context and write an HTML report.

Reads the session transcript (~/.claude/projects/<slug>/<session>.jsonl), which
records the injected payload: system prompt, tool schemas, skill listing,
deferred tool names, MCP instructions, agent listing and memory files. Each
item is sized by characters, then every item is scaled by one chars-per-token
ratio so the baseline matches the real first-turn usage in the same transcript.
Config files are read only to map items to the setting that controls them.

    scan.py [--project DIR] [--session ID|PATH] [--out DIR]

Writes <out>/context-report.html and <out>/context-report.json; prints a summary.
Never copies memory-file contents, session context or MCP config values into
the report: only names, paths, sizes and short skill/tool description previews.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
CLAUDE_JSON = HOME / ".claude.json"
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE = SCRIPT_DIR / "report_template.html"

DEFAULT_CPT = 3.5  # chars per token when calibration is impossible
CPT_RANGE = (2.0, 5.0)  # outside this the calibration is distrusted
PREVIEW = 160


# ---------- small helpers ----------


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def project_slug(project: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", str(project))


def norm(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", s).lower()


def preview(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= PREVIEW else text[: PREVIEW - 1] + "…"


def find_transcript(project: Path, session: str | None) -> Path:
    if session and session.endswith(".jsonl") and Path(session).exists():
        return Path(session)
    d = CLAUDE_DIR / "projects" / project_slug(project)
    sid = session or os.environ.get("CLAUDE_CODE_SESSION_ID")
    if sid and (d / f"{sid}.jsonl").exists():
        return d / f"{sid}.jsonl"
    files = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        sys.exit(f"No transcripts in {d}. Start a Claude Code session in {project}.")
    return files[0]


# ---------- config: who controls what ----------


class Config:
    """Settings layers and install locations relevant to context items."""

    def __init__(self, project: Path):
        self.project = project
        self.layers = {  # precedence low -> high
            "global": CLAUDE_DIR / "settings.json",
            "project-shared": project / ".claude" / "settings.json",
            "project": project / ".claude" / "settings.local.json",
        }
        self.settings = {k: load_json(p, {}) or {} for k, p in self.layers.items()}
        cj = load_json(CLAUDE_JSON, {}) or {}
        self.user_mcp = set((cj.get("mcpServers") or {}).keys())
        pcfg = (cj.get("projects") or {}).get(str(project), {}) or {}
        self.local_mcp = set((pcfg.get("mcpServers") or {}).keys())
        self.disabled_mcp = set(pcfg.get("disabledMcpServers") or [])
        self.mcpjson = set(
            (
                (load_json(project / ".mcp.json", {}) or {}).get("mcpServers") or {}
            ).keys()
        )
        inst = load_json(CLAUDE_DIR / "plugins" / "installed_plugins.json", {}) or {}
        self.plugin_ids = {}  # short name -> plugin@marketplace
        for pid in (inst.get("plugins") or inst).keys():
            self.plugin_ids.setdefault(pid.split("@")[0], pid)
        self.synced = set()
        for m in (CLAUDE_DIR / "plugins" / "synced").glob("*/manifest.json"):
            for p in (load_json(m, {}) or {}).get("plugins", []):
                self.synced.add(p.get("name"))
        self.skill_dirs = {
            "project": project / ".claude" / "skills",
            "personal": CLAUDE_DIR / "skills",
        }

    def merged(self, key: str) -> dict:
        """Per-key effective value and the layer that set it."""
        out = {}
        for layer, s in self.settings.items():
            for k, v in (s.get(key) or {}).items():
                out[k] = (v, layer)
        return out

    def skills_dir_plugin(self, name: str) -> Path | None:
        for base in self.skill_dirs.values():
            d = base / name
            if (d / "plugin.json").exists() or (d / ".claude-plugin").exists():
                return d
        return None

    def skill_source(self, name: str) -> tuple[str, str, str | None]:
        """(kind, group label, path) for a listed skill name."""
        if ":" in name:
            plugin = name.split(":", 1)[0]
            return ("plugin-skill", plugin, None)
        for kind, base in self.skill_dirs.items():
            d = base / name
            if (d / "SKILL.md").exists() or d.is_symlink():
                real = d.resolve()
                return (kind, kind, str(real))
        if (self.project / ".claude" / "commands" / f"{name}.md").exists():
            return ("project", "project", None)
        if (CLAUDE_DIR / "commands" / f"{name}.md").exists():
            return ("personal", "personal", None)
        return ("bundled", "bundled", None)

    def plugin_kind(self, plugin: str) -> str:
        if plugin in self.plugin_ids:
            return "marketplace"
        if plugin in self.synced:
            return "synced"
        if self.skills_dir_plugin(plugin):
            return "skills-dir"
        return "unknown"

    def mcp_kind(self, display: str) -> str:
        if display.startswith("claude.ai "):
            return "claudeai"
        if display.startswith("plugin:"):
            return "plugin"
        if display in self.mcpjson:
            return "mcpjson"
        if display in self.local_mcp:
            return "local"
        if display in self.user_mcp:
            return "user"
        return "unknown"


# ---------- transcript parsing ----------


def parse_transcript(path: Path) -> dict:
    out = {
        "snapshot": None,
        "skills": {},  # name -> (text, turn)
        "deferred": {},  # name -> turn
        "surfaced": {},  # name -> (definition json, turn)
        "mcp_blocks": {},  # server display -> (text, turn)
        "mcp_names": set(),
        "agents": {},  # type -> (line, builtin, turn)
        "memory": {},  # path -> (chars, turn)
        "context": {},  # label -> (chars, turn)
        "misc": {},  # attachment type -> (chars, turn)
        "first_user": "",
        "first_usage": None,
        "first_model": None,
        "session_id": path.stem,
        "started": None,
    }
    turn = 1
    for line in path.open():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("isSidechain"):
            continue
        t = d.get("type")
        out["started"] = out["started"] or d.get("timestamp")
        if t == "assistant":
            usage = (d.get("message") or {}).get("usage")
            if usage and out["first_usage"] is None:
                out["first_usage"] = sum(
                    usage.get(k) or 0
                    for k in (
                        "input_tokens",
                        "cache_creation_input_tokens",
                        "cache_read_input_tokens",
                    )
                )
                out["first_model"] = d["message"].get("model")
                turn = 2
            continue
        if t == "user" and not out["first_user"] and turn == 1:
            c = (d.get("message") or {}).get("content")
            out["first_user"] = (
                c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
            )
            continue
        if t != "attachment":
            continue
        a = d.get("attachment") or {}
        at = a.get("type")
        if at == "prompt_snapshot":
            if a.get("tools") and out["snapshot"] is None:
                out["snapshot"] = a
        elif at == "skill_listing":
            prev = out["skills"]
            if a.get("isInitial"):
                out["skills"] = {}
            for name, text in split_skill_listing(a.get("content", ""), a.get("names")):
                out["skills"][name] = (text, first_turn(prev, name, turn))
        elif at == "deferred_tools_delta":
            for n in a.get("removedNames") or []:
                out["deferred"].pop(n, None)
            for n in a.get("addedNames") or []:
                out["deferred"].setdefault(n, turn)
            for s in a.get("surfacedDefinitions") or []:
                out["surfaced"][s["name"]] = (
                    json.dumps(s.get("definition"), ensure_ascii=False),
                    first_turn(out["surfaced"], s["name"], turn),
                )
            for s in (a.get("pendingMcpServers") or []) + [
                f.get("name") for f in a.get("failedMcpServers") or []
            ]:
                out["mcp_names"].add(s)
        elif at == "mcp_instructions_delta":
            for n in a.get("removedNames") or []:
                out["mcp_blocks"].pop(n, None)
            for n, b in zip(a.get("addedNames") or [], a.get("addedBlocks") or []):
                out["mcp_blocks"][n] = (b, first_turn(out["mcp_blocks"], n, turn))
                out["mcp_names"].add(n)
        elif at == "agent_listing_delta":
            builtin = set(a.get("builtInTypes") or [])
            for n in a.get("removedTypes") or []:
                out["agents"].pop(n, None)
            for n, ln in zip(a.get("addedTypes") or [], a.get("addedLines") or []):
                out["agents"][n] = (
                    ln,
                    n in builtin,
                    first_turn(out["agents"], n, turn),
                )
        elif at == "instructions":
            for f in a.get("files") or []:
                p = f.get("path")
                out["memory"][p] = (
                    len(f.get("content") or ""),
                    first_turn(out["memory"], p, turn),
                )
        elif at == "session_context":
            for k, v in (a.get("context") or {}).items():
                out["context"][k] = (len(str(v)), first_turn(out["context"], k, turn))
        elif at not in ("total_tokens_reminder",):
            size = len(json.dumps(a, ensure_ascii=False))
            out["misc"][at] = (size, first_turn(out["misc"], at, turn))
    return out


def first_turn(store: dict, key, turn: int) -> int:
    """Re-sent listings (after compaction or a reload) keep the turn an item first appeared."""
    seen = store.get(key)
    return seen[-1] if seen else turn


def split_skill_listing(content: str, names: list | None) -> list[tuple[str, str]]:
    """Split '- name: description' entries; descriptions may span lines."""
    known = set(names or [])
    entries, cur_name, cur = [], None, []
    for ln in content.splitlines():
        name = ln[2:].split(": ", 1)[0].rstrip(":") if ln.startswith("- ") else None
        if name and (not known or name in known):
            if cur_name:
                entries.append((cur_name, "\n".join(cur)))
            cur_name, cur = name, [ln]
        elif cur_name:
            cur.append(ln)
    if cur_name:
        entries.append((cur_name, "\n".join(cur)))
    return entries


# ---------- MCP name resolution ----------


def mcp_server_for_tool(tool: str, servers: set[str], cfg: Config) -> str | None:
    if not tool.startswith("mcp__"):
        return None
    prefix = tool[5:].rsplit("__", 1)[0]  # e.g. plugin_linear_linear, claude_ai_Miro
    by_norm = {norm(s): s for s in servers}
    if norm(prefix) in by_norm:
        return by_norm[norm(prefix)]
    if prefix.startswith("claude_ai_"):
        return "claude.ai " + prefix[len("claude_ai_") :].replace("_", " ")
    if prefix.startswith("plugin_"):
        rest = prefix[len("plugin_") :]
        for plugin in sorted(cfg.plugin_ids, key=len, reverse=True):
            if norm(rest).startswith(norm(plugin) + "_"):
                return f"plugin:{plugin}:{rest[len(plugin) + 1 :]}"
        return "plugin:" + rest.replace("_", ":", 1)
    return prefix


# ---------- build items ----------


def build(project: Path, transcript: Path) -> dict:
    cfg = Config(project)
    tr = parse_transcript(transcript)
    items: list[dict] = []
    flags: list[dict] = []

    def add(**kw):
        kw.setdefault("turn", 1)
        kw.setdefault("actions", [])
        kw.setdefault("state", "on")
        kw.setdefault("note", "")
        kw.setdefault("preview", "")
        kw.setdefault("rollup", False)
        kw["id"] = f"{kw['kind']}:{kw['name']}"
        items.append(kw)
        return kw

    snap = tr["snapshot"] or {}
    sp = [p for p in snap.get("systemPrompt") or [] if "DYNAMIC_BOUNDARY" not in p]
    if sp:
        add(
            kind="system",
            name="System prompt",
            category="Built-in (fixed)",
            group="System prompt",
            chars=sum(map(len, sp)) + len(snap.get("cliPrefix") or ""),
            preview=preview(sp[0]),
        )
    for tool in snap.get("tools") or []:
        add(
            kind="tool",
            name=tool["name"],
            category="Built-in (fixed)",
            group="Tool definitions",
            chars=len(json.dumps(tool.get("schema") or tool, ensure_ascii=False)),
            preview=preview(tool.get("description") or ""),
        )

    # MCP servers: deferred names + instructions + eagerly surfaced definitions
    servers = set(tr["mcp_names"]) | cfg.user_mcp | cfg.local_mcp | cfg.mcpjson
    mcp: dict[str, dict] = {}
    builtin_deferred = []
    for name, turn in tr["deferred"].items():
        srv = mcp_server_for_tool(name, servers, cfg)
        if srv is None:
            builtin_deferred.append((name, turn))
            continue
        m = mcp.setdefault(srv, {"chars": 0, "tools": 0, "turn": turn, "parts": []})
        m["chars"] += len(name) + 1
        m["tools"] += 1
        m["turn"] = min(m["turn"], turn)
    for name, (defn, turn) in tr["surfaced"].items():
        srv = mcp_server_for_tool(name, servers, cfg)
        if srv is None:
            continue
        m = mcp.setdefault(srv, {"chars": 0, "tools": 0, "turn": turn, "parts": []})
        m["chars"] += len(defn)
        m["parts"].append("eager definitions")
    for srv, (block, turn) in tr["mcp_blocks"].items():
        m = mcp.setdefault(srv, {"chars": 0, "tools": 0, "turn": turn, "parts": []})
        m["chars"] += len(block)
        m["parts"].append("server instructions")
    if builtin_deferred:
        add(
            kind="deferred",
            name="Built-in deferred tool names",
            category="Built-in (fixed)",
            group="Deferred tool names",
            chars=sum(len(n) + 1 for n, _ in builtin_deferred),
            preview=", ".join(n for n, _ in builtin_deferred[:12]),
        )

    plugin_members: dict[str, list[dict]] = {}

    for srv, m in sorted(mcp.items()):
        kind = cfg.mcp_kind(srv)
        actions, note = [], ""
        plugin = srv.split(":")[1] if kind == "plugin" else None
        if kind in ("claudeai", "plugin", "user", "local", "unknown"):
            actions.append(
                {"value": "disable", "label": "Disable", "scopes": ["project"]}
            )
        if kind == "mcpjson":
            actions.append(
                {"value": "disable", "label": "Disable", "scopes": ["project"]}
            )
        if kind == "user":
            actions[0]["scopes"].append("global")
        if kind == "claudeai":
            note = "Global: disconnect it at claude.ai → Settings → Connectors."
        if kind == "plugin":
            note = f"Global: disable the {plugin} plugin."
        desc = f"{m['tools']} deferred tool names"
        if m["parts"]:
            desc += " + " + " + ".join(sorted(set(m["parts"])))
        it = add(
            kind="mcp",
            name=srv,
            category="MCP servers",
            group={"claudeai": "claude.ai connectors", "plugin": "Plugin MCP"}.get(
                kind, "Configured MCP"
            ),
            chars=m["chars"],
            turn=m["turn"],
            preview=desc,
            actions=actions,
            note=note,
            source=kind,
        )
        if srv in cfg.disabled_mcp:
            flags.append(
                {
                    "item": it["id"],
                    "text": f"{srv} is in disabledMcpServers for this project but still loaded.",
                }
            )
        if plugin:
            plugin_members.setdefault(plugin, []).append(it)

    jsonoff = set()
    for layer, s in cfg.settings.items():
        for n in s.get("disabledMcpjsonServers") or []:
            if n not in cfg.mcpjson:
                jsonoff.add((n, layer))
    loaded = {i["name"] for i in items if i["kind"] == "mcp"}
    for n, layer in sorted(jsonoff):
        if n in loaded:
            flags.append(
                {
                    "item": f"mcp:{n}",
                    "text": (
                        f"{n} is listed in disabledMcpjsonServers ({layer}) but that key only "
                        "affects servers defined in .mcp.json; it is still loaded."
                    ),
                }
            )

    # Skills
    overrides = cfg.merged("skillOverrides")
    for name, (text, turn) in tr["skills"].items():
        kind, group, path = cfg.skill_source(name)
        ov = overrides.get(name)
        state = ov[0] if ov else "on"
        name_only = text.strip() == f"- {name}" or text.strip() == f"- {name}:"
        actions, note = [], ""
        if kind == "plugin-skill":
            plugin = group
            note = "Plugin skill: skillOverrides do not apply. Use the plugin row."
            group = f"plugin: {plugin}"
            if ov:
                flags.append(
                    {
                        "item": f"skill:{name}",
                        "text": (
                            f'{name} has skillOverrides "{ov[0]}" ({ov[1]}) but plugin skills '
                            "ignore skillOverrides; it is still listed."
                        ),
                    }
                )
        else:
            plugin = None
            for v, lbl in (
                ("name-only", "Name only"),
                ("user-invocable-only", "User-invocable only"),
                ("off", "Off"),
            ):
                actions.append(
                    {"value": v, "label": lbl, "scopes": ["global", "project"]}
                )
            if ov:
                actions.append(
                    {"value": "on", "label": "On (remove override)", "scopes": [ov[1]]}
                )
                if ov[0] in ("off", "user-invocable-only") and not name_only:
                    flags.append(
                        {
                            "item": f"skill:{name}",
                            "text": f'{name} is "{ov[0]}" ({ov[1]}) but still listed.',
                        }
                    )
        it = add(
            kind="skill",
            name=name,
            category="Skills",
            group=group if kind != "bundled" else "bundled (ships with Claude Code)",
            chars=len(text) + 1,
            name_chars=len(f"- {name}") + 1,
            turn=turn,
            preview=preview(text[len(f"- {name}:") :]) or "(name only, no description)",
            actions=actions,
            state=state + (" · name-only" if name_only and state == "on" else ""),
            note=note,
            path=path,
            source=kind,
        )
        if plugin:
            plugin_members.setdefault(plugin, []).append(it)

    # Agents
    for name, (ln, builtin, turn) in tr["agents"].items():
        plugin = name.split(":")[0] if ":" in name else None
        it = add(
            kind="agent",
            name=name,
            category="Agent types",
            group=(
                "built-in" if builtin else (f"plugin: {plugin}" if plugin else "custom")
            ),
            chars=len(ln) + 1,
            turn=turn,
            preview=preview(ln),
            note="" if builtin or not plugin else "Plugin agent: use the plugin row.",
        )
        if plugin and not builtin:
            plugin_members.setdefault(plugin, []).append(it)

    # Plugin roll-up rows (not counted again in totals)
    enabled = cfg.merged("enabledPlugins")
    for plugin, members in sorted(plugin_members.items()):
        pkind = cfg.plugin_kind(plugin)
        pid = cfg.plugin_ids.get(plugin)
        actions, note = [], ""
        if pkind == "marketplace":
            actions = [
                {
                    "value": "disable",
                    "label": "Disable plugin",
                    "scopes": ["global", "project"],
                }
            ]
            ev = enabled.get(pid)
            if ev and ev[0] is False:
                flags.append(
                    {
                        "item": f"plugin:{plugin}",
                        "text": f"{pid} is false in enabledPlugins ({ev[1]}) but its content is loaded.",
                    }
                )
        elif pkind == "synced":
            note = "Synced from your claude.ai organization; manage it on claude.ai."
            ev = next(
                (v for k, v in enabled.items() if k.split("@")[0] == plugin), None
            )
            if ev and ev[0] is False:
                flags.append(
                    {
                        "item": f"plugin:{plugin}",
                        "text": (
                            f"{plugin} is false in enabledPlugins ({ev[1]}) but is an "
                            "org-synced plugin from claude.ai, so that setting does not unload it."
                        ),
                    }
                )
        elif pkind == "skills-dir":
            note = f"Loaded from {cfg.skills_dir_plugin(plugin)}; another app may manage it."
        else:
            note = "Not installed locally; likely provided by your claude.ai account."
        add(
            kind="plugin",
            name=plugin,
            category="Plugins (roll-up)",
            group=pkind,
            chars=sum(m["chars"] for m in members),
            preview=f"{len(members)} item{'s' * (len(members) != 1)}: "
            + ", ".join(sorted({m["kind"] for m in members})),
            actions=actions,
            note=note,
            plugin_id=pid,
            members=[m["id"] for m in members],
            rollup=True,
            source=pkind,
        )

    # Memory, context and conversation (sizes only)
    for p, (chars, turn) in tr["memory"].items():
        add(
            kind="memory",
            name=p.replace(str(HOME), "~"),
            category="Memory files",
            group="CLAUDE.md / AGENTS.md",
            chars=chars,
            turn=turn,
            preview="Contents not copied into the report.",
        )
    for label, (chars, turn) in tr["context"].items():
        add(
            kind="context",
            name=label,
            category="Session context",
            group="Injected context",
            chars=chars,
            turn=turn,
        )
    for label, (chars, turn) in tr["misc"].items():
        add(
            kind="context",
            name=label,
            category="Session context",
            group="Harness reminders",
            chars=chars,
            turn=turn,
        )
    if tr["first_user"]:
        add(
            kind="conversation",
            name="First user message",
            category="Conversation",
            group="Conversation",
            chars=len(tr["first_user"]),
        )

    # Calibration: one chars-per-token ratio against first-turn usage
    counted = [i for i in items if not i["rollup"]]
    base_chars = sum(i["chars"] for i in counted if i["turn"] == 1)
    real = tr["first_usage"]
    cpt, calibrated = DEFAULT_CPT, False
    if real and base_chars:
        implied = base_chars / real
        if CPT_RANGE[0] <= implied <= CPT_RANGE[1]:
            cpt, calibrated = implied, True
    for i in items:
        i["tokens"] = round(i["chars"] / cpt)
        if i.get("name_chars"):
            i["name_tokens"] = max(1, round(i["name_chars"] / cpt))
    estimated = sum(i["tokens"] for i in counted if i["turn"] == 1)
    if real and not calibrated and real > estimated:
        add(
            kind="other",
            name="Unattributed",
            category="Built-in (fixed)",
            group="Unattributed",
            chars=0,
            preview="Framing and text not recorded in the transcript.",
        )["tokens"] = (
            real - estimated
        )

    later = sum(i["tokens"] for i in counted if i["turn"] > 1)
    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "transcript": str(transcript).replace(str(HOME), "~"),
        "session_id": tr["session_id"],
        "model": tr["first_model"],
        "first_turn_tokens": real,
        "later_tokens": later,
        "chars_per_token": round(cpt, 3),
        "calibrated": calibrated,
        "items": items,
        "flags": flags,
        "settings_files": {
            k: str(v).replace(str(HOME), "~") for k, v in cfg.layers.items()
        },
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", default=os.getcwd())
    ap.add_argument("--session", help="session id or path to a transcript .jsonl")
    ap.add_argument("--out", default=None, help="output directory")
    args = ap.parse_args()
    project = Path(args.project).resolve()
    transcript = find_transcript(project, args.session)
    report = build(project, transcript)
    out = Path(args.out or CLAUDE_DIR / "context-reports" / project_slug(project))
    out.mkdir(parents=True, exist_ok=True)
    (out / "context-report.json").write_text(json.dumps(report, indent=1))
    html = TEMPLATE.read_text().replace(
        "/*__REPORT_DATA__*/null", json.dumps(report).replace("</", "<\\/")
    )
    (out / "context-report.html").write_text(html)

    counted = [i for i in report["items"] if not i["rollup"]]
    by_cat: dict[str, int] = {}
    for i in counted:
        by_cat[i["category"]] = by_cat.get(i["category"], 0) + i["tokens"]
    plugin_ctl = {
        m for p in report["items"] if p["rollup"] and p["actions"] for m in p["members"]
    }
    actionable = sum(
        i["tokens"] for i in counted if i["actions"] or i["id"] in plugin_ctl
    )
    print(f"transcript: {report['transcript']}")
    print(
        f"first turn: {report['first_turn_tokens']} tokens · later baseline: +{report['later_tokens']}"
        f" · chars/token {report['chars_per_token']} ({'calibrated' if report['calibrated'] else 'default'})"
    )
    for cat, tok in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {cat:<22} {tok:>7}")
    print(f"actionable: ~{actionable} tokens · flags: {len(report['flags'])}")
    print(f"html: {out / 'context-report.html'}")


if __name__ == "__main__":
    main()
