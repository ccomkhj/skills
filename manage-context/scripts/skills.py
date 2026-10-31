#!/usr/bin/env python3
"""See the role every skill plays in a project, and switch skills with one command.

    skills.py [list] [--project DIR] [--role auto|name|slash|off] [--all] [--json]
    skills.py set NAME... STATE [--scope global|project] [--project DIR] [--apply]
    skills.py set --plugin NAME... on|off [--scope global|project] [--project DIR] [--apply]

STATE: auto (on), name (name-only), slash (user-invocable-only), off.
Without --scope, `set` writes where the current value comes from: the project file if a
project setting decides the skill here, else global. It prints a dry run (role before ->
after, every file edit); --apply writes it with backups and an undo file (apply_plan.py).
Changes take effect in the next session.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_plan  # noqa: E402
import inventory  # noqa: E402

ALIAS = {
    "auto": "on", "on": "on",
    "name": "name-only", "name-only": "name-only",
    "slash": "user-invocable-only", "user": "user-invocable-only",
    "user-invocable-only": "user-invocable-only", "uio": "user-invocable-only",
    "off": "off",
}
SHORT = {"on": "auto", "name-only": "name", "user-invocable-only": "/slash", "off": "off", None: "-"}
HEAD = {
    "on": "AUTO: model sees name + description and may run it unasked; /name works",
    "name-only": "NAME ONLY: model sees just the name; /name works",
    "user-invocable-only": "/SLASH ONLY: hidden from the model; you type /name",
    "off": "OFF: hidden from both",
}
SET_BY = {
    "default": "default", "global": "global setting", "project": "project setting",
    "project-shared": "project setting (shared)", "frontmatter": "SKILL.md frontmatter (locked)",
    "plugin": "plugin", "policy": "managed policy (locked)",
}
SCOPE = {"global": "global", "project": "this project", "account": "claude.ai",
         "synced": "org", "bundled": "built-in", "plugin": "plugin", "elsewhere": "other project"}


def set_by_text(e: dict) -> str:
    t = SET_BY.get(e["set_by"], e["set_by"] or "")
    g = e["layers"].get("global")
    if e["set_by"] in ("project", "project-shared") and g and g != e["role"]:
        t += f" (global: {SHORT[g]})"
    return t


def elsewhere_text(items: list[dict], limit: int = 3, raw: bool = False) -> str:
    parts = [f"{Path(x['project']).name}: {x['value'] if raw else SHORT[x['value']]}" for x in items[:limit]]
    return ", ".join(parts) + (f" +{len(items) - limit}" if len(items) > limit else "")


def cmd_list(inv: dict, role: str | None, show_all: bool):
    f = inv["files"]
    print(f"{inv['project']} · global {f['global']} · project {f['project']}")
    own = [e for e in inv["skills"] if e["scope"] in inventory.OVERRIDABLE]
    for r in inventory.STATES:
        if role and r != role:
            continue
        rows = [e for e in own if e["role"] == r]
        tok = sum(inventory.tokens(e, r) for e in rows)
        print(f"\n{HEAD[r]} · {len(rows)}" + (f" · ~{tok:,} tokens" if tok else ""))
        w = max([len(e["name"]) for e in rows] + [10])
        for e in rows:
            extra = []
            if e["model_only"]:
                extra.append("no /name (user-invocable: false)")
            if e["elsewhere"]:
                extra.append("elsewhere " + elsewhere_text(e["elsewhere"]))
            t = inventory.tokens(e, r)
            print(f"  {e['name']:<{w}}  {SCOPE[e['scope']]:<12} {set_by_text(e):<34}"
                  f"{('~' + str(t)) if t else '':>6}  {' · '.join(extra)}".rstrip())
    if role:
        return
    print("\nPLUGINS: their skills ignore skillOverrides; switch the whole plugin")
    by = {e["name"]: e for e in inv["skills"]}
    for p in inv["plugins"]:
        roles: dict[str, int] = {}
        for m in p["members"]:
            r = by[m]["role"]
            roles[SHORT[r]] = roles.get(SHORT[r], 0) + 1
        mix = ", ".join(f"{n} {k}" for k, n in roles.items())
        how = {"marketplace": f"({SET_BY.get(p['set_by'], 'not enabled')})" if p["set_by"] else "(not enabled)",
               "skills-dir": "(folder in ~/.claude/skills; no switch)",
               "synced": "(claude.ai org; manage there)"}[p["kind"]]
        el = f" · elsewhere {elsewhere_text(p['elsewhere'], raw=True)}" if p.get("elsewhere") else ""
        ign = sum(1 for m in p["members"] if by[m]["layers"])
        ign = f" · {ign} skillOverrides ignored" if ign else ""
        n = len(p["members"])
        print(f"  {'on ' if p['enabled'] else 'off'}  {p['name']:<24} {n:>3} skill{'s' * (n != 1)}"
              f"{' (' + mix + ')' if mix and p['enabled'] else ''} {how}{el}{ign}")
    only = [e for e in inv["skills"] if e["scope"] == "elsewhere"]
    print(f"\nONLY IN OTHER PROJECTS · {len(only)}" + ("" if show_all else " (--all lists them)"))
    if show_all:
        for e in only:
            print(f"  {e['name']:<32} {', '.join(e['installed_in'])}")
    if inv["stale"]:
        print(f"\nOVERRIDES WITH NO SKILL ON DISK · {len(inv['stale'])} "
              "(built-in command, bundled skill, or removed skill)")
        print("  " + ", ".join(f"{s['name']}={'/'.join(SHORT[v] for v in s['layers'].values())}"
                               for s in inv["stale"]))
    if inv["broken_links"]:
        print("\nBROKEN LINKS in ~/.claude/skills")
        for b in inv["broken_links"]:
            print(f"  {b}")


def cmd_set(inv: dict, project: Path, names: list[str], state: str, scope: str | None,
            plugin: bool, do_apply: bool):
    actions, errors = [], []
    if plugin:
        if state not in ("on", "off"):
            sys.exit("a plugin is on or off")
        plugins = {p["name"]: p for p in inv["plugins"]}
        for n in names:
            p = plugins.get(n.split("@")[0])
            if not p:
                errors.append(f"{n}: no such plugin" + hint(n, plugins))
            elif p["kind"] != "marketplace":
                errors.append(f"{n}: {p['kind']} plugin has no setting ({p['where']}); see references/levers.md")
            else:
                sc = scope or "global"
                print(f"• plugin {p['name']}: {'on' if p['enabled'] else 'off'} → {state} ({sc})")
                actions.append({"kind": "plugin", "target": p["name"], "plugin_id": p["id"],
                                "action": "enable" if state == "on" else "disable", "scope": sc})
    else:
        by = {e["name"]: e for e in inv["skills"]}
        for n in names:
            e = by.get(n)
            if not e:
                errors.append(f"{n}: no such skill" + hint(n, by))
            elif e["scope"] == "plugin":
                errors.append(f"{n}: plugin skills ignore skillOverrides; "
                              f"use `set --plugin {e['plugin']} off`, or edit its SKILL.md")
            elif e["scope"] == "elsewhere":
                errors.append(f"{n}: installed only in {', '.join(e['installed_in'])}; run this there")
            else:
                sc = scope or ("project" if e["set_by"] in ("project", "project-shared") else "global")
                after = inventory.predict(e, state, sc)
                d = inventory.tokens(e, after) - inventory.tokens(e, e["role"])
                note = "" if after != e["role"] else (
                    " (no change here: " + ("locked by its SKILL.md)" if e["locked"] else
                                            "a project setting wins; use --scope project)" if sc == "global" else "already so)"))
                print(f"• {n}: {SHORT[e['role']]} → {SHORT[after]} ({sc})"
                      + (f", {'+' if d > 0 else '−'}~{abs(d):,} tokens/session" if d else "") + note)
                actions.append({"kind": "skill", "target": n, "action": state, "scope": sc,
                                "source": e["scope"]})
    edits = []
    for a in actions:
        try:
            es, warns = apply_plan.compile_action(a, project)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        for w in warns:
            print(f"  ! {w}")
        edits.extend(es)
    for e in errors:
        print(f"  ✗ {e}")
    if not edits:
        sys.exit("\nNo applicable edits.")
    apply_plan.run(edits, do_apply, "set")


def hint(n: str, known) -> str:
    m = difflib.get_close_matches(n, list(known), n=3)
    return f" (did you mean {', '.join(m)}?)" if m else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", nargs="?", default="list", choices=("list", "set"))
    ap.add_argument("args", nargs="*", help="set: NAME... STATE")
    ap.add_argument("--project", default=os.getcwd())
    ap.add_argument("--role", choices=("auto", "name", "slash", "off"))
    ap.add_argument("--all", action="store_true", help="list skills that live only in other projects")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--scope", choices=("global", "project"))
    ap.add_argument("--plugin", action="store_true", help="set: NAMEs are plugins")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    project = Path(a.project).resolve()
    inv = inventory.build(project)
    if a.cmd == "list":
        if a.json:
            print(json.dumps(inv, indent=1))
        else:
            cmd_list(inv, ALIAS.get(a.role) if a.role else None, a.all)
        return
    if len(a.args) < 2 or a.args[-1].lower() not in ALIAS:
        ap.error("set needs NAME... STATE (auto | name | slash | off)")
    cmd_set(inv, project, a.args[:-1], ALIAS[a.args[-1].lower()], a.scope, a.plugin, a.apply)


if __name__ == "__main__":
    main()
