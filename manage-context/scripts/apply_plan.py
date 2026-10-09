#!/usr/bin/env python3
"""Apply a manage-context plan (exported from the HTML report) to Claude Code config.

    apply_plan.py PLAN.json [--project DIR]            # dry run: print every edit
    apply_plan.py PLAN.json [--project DIR] --apply    # write, with backups + undo file
    apply_plan.py --undo UNDO.json --apply              # revert a previous apply

Each plan action becomes primitive JSON edits (set / delete / list-add / list-remove)
on a known config file. Only the combinations in `compile_action` are accepted.
Files are re-read immediately before writing and replaced atomically, so edits made
by a running Claude Code since the dry run are kept. Values from ~/.claude.json are
never printed: an MCP server entry shows as "<server config>".
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
CLAUDE_JSON = HOME / ".claude.json"
STATE_DIR = CLAUDE_DIR / "manage-context"
PARKED = STATE_DIR / "parked-mcp-servers.json"


class _Absent:
    def __repr__(self):
        return "(absent)"


ABSENT = _Absent()

SKILL_STATES = {"on", "name-only", "user-invocable-only", "off"}
NAME_RE = re.compile(r"^[\w.:@ /-]{1,200}$")


def tilde(p: Path | str) -> str:
    return str(p).replace(str(HOME), "~")


def settings_file(scope: str, project: Path) -> Path:
    return {
        "global": CLAUDE_DIR / "settings.json",
        "project": project / ".claude" / "settings.local.json",
    }[scope]


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def get(doc: dict, keys: list):
    cur = doc
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return ABSENT
        cur = cur[k]
    return cur


# ---------- plan -> primitive edits ----------


def edit(file: Path, keys: list, op: str, value=None, secret=False) -> dict:
    return {"file": str(file), "keys": keys, "op": op, "value": value, "secret": secret}


def compile_action(a: dict, project: Path) -> tuple[list[dict], list[str]]:
    kind, target = a.get("kind"), a.get("target", "")
    action, scope = a.get("action"), a.get("scope")
    warn: list[str] = []
    if not isinstance(target, str) or not NAME_RE.match(target):
        raise ValueError(f"invalid target name: {target!r}")

    if kind == "skill":
        if action not in SKILL_STATES or scope not in ("global", "project"):
            raise ValueError(f"skill {target}: unsupported {action}/{scope}")
        if a.get("source") == "plugin-skill" or ":" in target:
            raise ValueError(f"skill {target}: plugin skills ignore skillOverrides; disable the plugin")
        f = settings_file(scope, project)
        keys = ["skillOverrides", target]
        if action == "on":
            return [edit(f, keys, "delete")], warn
        if scope == "global":
            for layer in (project / ".claude" / "settings.json", settings_file("project", project)):
                v = get(load(layer), keys)
                if v is not ABSENT:
                    warn.append(f"{tilde(layer)} sets {target}={v!r}, which overrides the global value here")
        return [edit(f, keys, "set", action)], warn

    if kind == "plugin":
        pid = a.get("plugin_id")
        if action not in ("disable", "enable") or scope not in ("global", "project"):
            raise ValueError(f"plugin {target}: unsupported {action}/{scope}")
        installed = load(CLAUDE_DIR / "plugins" / "installed_plugins.json")
        known = set((installed.get("plugins") or installed).keys())
        if pid not in known:
            raise ValueError(f"plugin {target}: {pid!r} is not an installed marketplace plugin")
        f = settings_file(scope, project)
        if scope == "global":
            for layer in (project / ".claude" / "settings.json", settings_file("project", project)):
                if get(load(layer), ["enabledPlugins", pid]) is True:
                    warn.append(f"{tilde(layer)} enables {pid}; it stays on in this project")
        return [edit(f, ["enabledPlugins", pid], "set", action == "enable")], warn

    if kind == "mcp":
        if action not in ("disable", "enable"):
            raise ValueError(f"mcp {target}: unsupported action {action}")
        add = "list_add" if action == "disable" else "list_remove"
        if scope == "project":
            if a.get("source") == "mcpjson":
                f = settings_file("project", project)
                return [edit(f, ["disabledMcpjsonServers"], add, target)], warn
            keys = ["projects", str(project), "disabledMcpServers"]
            return [edit(CLAUDE_JSON, keys, add, target)], warn
        if scope == "global" and a.get("source") == "user":
            cfg = get(load(CLAUDE_JSON), ["mcpServers", target])
            if action == "disable":
                if cfg is ABSENT:
                    raise ValueError(f"mcp {target}: not in ~/.claude.json mcpServers")
                return [
                    edit(PARKED, [target], "set", cfg, secret=True),
                    edit(CLAUDE_JSON, ["mcpServers", target], "delete", secret=True),
                ], warn
            parked = get(load(PARKED), [target])
            if parked is ABSENT:
                raise ValueError(f"mcp {target}: nothing parked under that name")
            return [
                edit(CLAUDE_JSON, ["mcpServers", target], "set", parked, secret=True),
                edit(PARKED, [target], "delete", secret=True),
            ], warn
        raise ValueError(
            f"mcp {target}: no {scope} switch for a {a.get('source')} server "
            "(claude.ai: disconnect on claude.ai; plugin: disable the plugin)"
        )

    raise ValueError(f"unsupported kind: {kind!r}")


# ---------- primitive edits ----------


def apply_edit(doc: dict, e: dict):
    """Apply one edit in place; return its inverse (or None if it was a no-op)."""
    *parents, leaf = e["keys"]
    cur = doc
    for k in parents:
        cur = cur.setdefault(k, {})
    before = copy.deepcopy(cur[leaf]) if leaf in cur else ABSENT
    op = e["op"]
    if op in ("delete", "list_remove") and before is ABSENT:
        prune(doc, parents)
        return None
    if op == "set":
        if before == e["value"]:
            return None
        cur[leaf] = e["value"]
        inv = ("delete", None) if before is ABSENT else ("set", before)
    elif op == "delete":
        if before is ABSENT:
            return None
        del cur[leaf]
        inv = ("set", before)
    elif op in ("list_add", "list_remove"):
        lst = cur.get(leaf)
        lst = list(lst) if isinstance(lst, list) else []
        present = e["value"] in lst
        if (op == "list_add") == present:
            return None
        lst = lst + [e["value"]] if op == "list_add" else [x for x in lst if x != e["value"]]
        cur[leaf] = lst
        inv = ("list_remove" if op == "list_add" else "list_add", e["value"])
    else:
        raise ValueError(f"bad op {op}")
    prune(doc, parents)
    return {**e, "op": inv[0], "value": inv[1] if inv[0] != "delete" else None, "before": before}


def prune(doc: dict, parents: list):
    """Drop containers left empty along the path, deepest first."""
    for depth in range(len(parents), 0, -1):
        holder = doc
        for k in parents[: depth - 1]:
            holder = holder[k]
        if holder.get(parents[depth - 1]) == {}:
            del holder[parents[depth - 1]]


def describe(e: dict, before) -> str:
    path = "".join(f"[{json.dumps(k)}]" for k in e["keys"])
    if e.get("secret"):
        show = lambda v: "(absent)" if v is ABSENT else "<server config>"  # noqa: E731
    else:
        show = lambda v: "(absent)" if v is ABSENT else json.dumps(v)  # noqa: E731
    op = e["op"]
    if op == "set":
        return f"{path}: {show(before)} → {show(e['value'])}"
    if op == "delete":
        return f"{path}: {show(before)} → (removed)"
    verb = "add" if op == "list_add" else "remove"
    return f"{path}: {verb} {json.dumps(e['value'])}"


def write_atomic(path: Path, doc: dict, private: bool):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w") as fh:
        fh.write(text)
    mode = 0o600 if private or not path.exists() else path.stat().st_mode & 0o777
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def run(edits: list[dict], do_apply: bool, label: str) -> Path | None:
    by_file: dict[str, list[dict]] = {}
    for e in edits:
        by_file.setdefault(e["file"], []).append(e)

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = STATE_DIR / "backups" / stamp
    inverses: list[dict] = []
    changed = 0
    for file, es in by_file.items():
        path = Path(file)
        doc = load(path)  # fresh read, right before writing
        print(f"\n{tilde(path)}")
        file_changed = False
        for e in es:
            before = get(doc, e["keys"])
            inv = apply_edit(doc, e)
            if inv is None:
                print(f"  = {describe(e, before)} (already so, skipped)")
                continue
            print(f"  ~ {describe(e, before)}")
            inverses.append({k: v for k, v in inv.items() if k != "before"})
            file_changed = True
            changed += 1
        if do_apply and file_changed:
            if path.exists():
                backup_dir.mkdir(parents=True, exist_ok=True)
                dest = backup_dir / (path.name if path != CLAUDE_JSON else "claude.json")
                if dest.exists():
                    dest = backup_dir / f"{abs(hash(file))}-{path.name}"
                shutil.copy2(path, dest)
                os.chmod(dest, 0o600)
            write_atomic(path, doc, private=path in (CLAUDE_JSON, PARKED))

    if not do_apply:
        print(f"\nDry run: {changed} edit(s). Re-run with --apply to write.")
        return None
    if not changed:
        print("\nNothing to change.")
        return None
    undo = STATE_DIR / "undo" / f"{stamp}-{label}.json"
    write_atomic(undo, {"manage_context_undo": 1, "edits": list(reversed(inverses))}, private=True)
    print(f"\nApplied {changed} edit(s). Backups: {tilde(backup_dir)}")
    print(f"Undo: apply_plan.py --undo {tilde(undo)} --apply")
    print("Changes take effect in the next Claude Code session.")
    return undo


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan", nargs="?")
    ap.add_argument("--project", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--undo", help="undo file written by a previous --apply")
    args = ap.parse_args()

    if args.undo:
        doc = load(Path(os.path.expanduser(args.undo)))
        if doc.get("manage_context_undo") != 1:
            sys.exit("not a manage-context undo file")
        run(doc["edits"], args.apply, "undo")
        return
    if not args.plan:
        ap.error("PLAN.json is required (or --undo)")

    plan = load(Path(args.plan))
    if plan.get("manage_context_plan") != 1:
        sys.exit("not a manage-context plan (missing manage_context_plan: 1)")
    project = Path(args.project or plan.get("project") or os.getcwd()).resolve()
    if plan.get("project") and Path(plan["project"]).resolve() != project:
        sys.exit(f"plan is for {plan['project']}, not {project}; pass --project to confirm")

    edits, errors = [], []
    for a in plan.get("actions") or []:
        try:
            es, warns = compile_action(a, project)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        tag = f"{a['kind']} {a['target']}: {a['action']} ({a['scope']}, ~{a.get('est_tokens', '?')} tokens)"
        print(f"• {tag}")
        for w in warns:
            print(f"  ! {w}")
        edits.extend(es)
    if errors:
        print("\nRejected:")
        for e in errors:
            print(f"  ✗ {e}")
    if not edits:
        sys.exit("\nNo applicable edits.")
    run(edits, args.apply, "plan")


if __name__ == "__main__":
    main()
