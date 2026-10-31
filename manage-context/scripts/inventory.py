#!/usr/bin/env python3
"""Every skill Claude Code can load from a project, and the role it plays there.

A role is the effective skillOverrides state, resolved the way Claude Code 2.1.316
does it (references/levers.md):

    on                   "Auto": the model sees name + description and may invoke it; /name works
    name-only            the model sees only the name
    user-invocable-only  "/slash only": hidden from the model, /name still works
    off                  hidden from both

First match wins:
  1. local plugin skill (marketplace or skills-dir plugin): skillOverrides are ignored.
     Off while the plugin is disabled, else the skill's frontmatter decides.
  2. a managed-policy override names it (locked)
  3. frontmatter `disable-model-invocation: true` -> user-invocable-only (locked; an `off`
     override still hides it)
  4. the highest settings layer that names it: project (settings.local.json) >
     project-shared (settings.json) > global (~/.claude/settings.json)
  5. on
Frontmatter `user-invocable: false` hides /name (model only); reported as `model_only`.

Reads names, paths, frontmatter flags and settings. ~/.claude.json is read only for
its project paths (keys), never its values.

    inventory.py [--project DIR]     # prints the inventory as JSON
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
CLAUDE_JSON = HOME / ".claude.json"
STATES = ("on", "name-only", "user-invocable-only", "off")
LAYERS = ("global", "project-shared", "project")  # precedence low -> high
ACCOUNT_PREFIX = "anthropic-skills"  # claude.ai account skills, synced into ~/.claude/skills/synced
MANAGED = (
    Path("/Library/Application Support/ClaudeCode/managed-settings.json"),
    Path("/etc/claude-code/managed-settings.json"),
)
CPT = 3.5  # chars per token for skills not in a transcript
# Scopes whose skills obey skillOverrides (local plugin skills do not).
OVERRIDABLE = {"global", "project", "account", "synced", "bundled"}


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def tilde(p) -> str:
    s, h = str(p), str(HOME)
    return "~" + s[len(h):] if s == h or s.startswith(h + "/") else s


def layer_files(project: Path) -> dict[str, Path]:
    return {
        "global": CLAUDE_DIR / "settings.json",
        "project-shared": project / ".claude" / "settings.json",
        "project": project / ".claude" / "settings.local.json",
    }


def frontmatter(md: Path | None) -> dict[str, str]:
    """Top-level scalar keys of a SKILL.md / command frontmatter (no YAML dependency)."""
    try:
        text = md.read_text(errors="replace") if md else ""
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    out: dict[str, str] = {}
    key = None
    for ln in text[3 : end if end > 0 else 0].splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", ln)
        if m:
            key, val = m.group(1), m.group(2).strip()
            out[key] = "" if val in (">", "|", ">-", "|-", ">+", "|+") else val.strip("\"'")
        elif key and ln[:1] in (" ", "\t") and ln.strip():
            out[key] = (out[key] + " " + ln.strip()).strip()
    return out


def _flag(v: str | None, default: bool) -> bool:
    if v is None or v == "":
        return default
    return v.strip().lower() in ("true", "yes", "on", "1")


def _is_plugin_dir(d: Path) -> bool:
    return (d / "plugin.json").exists() or (d / ".claude-plugin" / "plugin.json").exists()


def _manifest(root: Path) -> dict:
    return load_json(root / ".claude-plugin" / "plugin.json") or load_json(root / "plugin.json") or {}


def _paths(v) -> list[str]:
    return [v] if isinstance(v, str) else [x for x in (v or []) if isinstance(x, str)]


def plugin_members(root: Path, short: str) -> list[tuple[str, Path, str]]:
    """(full name, file, kind) for a plugin's skills and commands; best effort."""
    man = _manifest(root)
    pname = man.get("name") or short
    dirs: list[Path] = []
    for p in _paths(man.get("skills")) + ["skills"]:
        d = (root / p).resolve()
        if (d / "SKILL.md").exists():
            dirs.append(d)
        else:
            dirs.extend(x.parent for x in sorted(d.glob("*/SKILL.md")))
    out, seen = [], set()
    for d in dirs:
        fm = frontmatter(d / "SKILL.md")
        full = f"{pname}:{fm.get('name') or d.name}"
        if full not in seen:
            seen.add(full)
            out.append((full, d / "SKILL.md", "skill"))
    for p in _paths(man.get("commands")) + ["commands"]:
        q = root / p
        for md in [q] if q.suffix == ".md" else sorted(q.glob("*.md")):
            full = f"{pname}:{md.stem}"
            if md.exists() and full not in seen:
                seen.add(full)
                out.append((full, md, "command"))
    return out


def merged(settings: dict[str, dict], key: str) -> dict[str, tuple]:
    """Effective value per name and the layer that set it."""
    out = {}
    for layer in LAYERS:
        for k, v in (settings[layer].get(key) or {}).items():
            out[k] = (v, layer)
    return out


def known_projects(here: Path) -> list[Path]:
    """Other projects Claude Code has opened (keys of ~/.claude.json projects)."""
    cj = load_json(CLAUDE_JSON, {}) or {}
    out = []
    for p in (cj.get("projects") or {}).keys():
        pp = Path(p)
        if pp not in (HOME, here) and pp.is_dir():
            out.append(pp)
    return sorted(out)


def _entry(name, kind, scope, md, where, **kw) -> dict:
    fm = frontmatter(md)
    desc = " ".join(x for x in (fm.get("description", ""), fm.get("when_to_use", "")) if x)
    return {
        "name": name,
        "kind": kind,  # skill | command
        "scope": scope,  # global | project | plugin | account | synced | bundled | elsewhere
        "where": where,
        "path": tilde(md.resolve()) if md else None,
        "listing_chars": len(f"- {name}: {desc}") + 1 if desc else len(f"- {name}") + 1,
        "preview": " ".join(desc.split())[:160],
        "dmi": _flag(fm.get("disable-model-invocation"), False),
        "model_only": not _flag(fm.get("user-invocable"), True),
        "plugin": kw.pop("plugin", None),
        "layers": {},
        "elsewhere": [],
        "installed_in": [],
        **kw,
    }


def resolve(e: dict, policy: dict, plugins: dict) -> tuple:
    """(role, set_by, locked) for one entry; see the module docstring."""
    name = e["name"]
    if e["scope"] == "elsewhere":
        return None, None, None
    if e["scope"] == "plugin":
        p = plugins.get(e["plugin"]) or {}
        if p.get("kind") == "marketplace" and not p.get("enabled"):
            return "off", "plugin", "plugin"
        if e["dmi"]:
            return "user-invocable-only", "frontmatter", "plugin"
        return "on", "plugin", "plugin"
    if policy.get(name) in STATES:
        return policy[name], "policy", "policy"
    top = next(((e["layers"][k], k) for k in reversed(LAYERS) if k in e["layers"]), None)
    if e["dmi"]:
        if top and top[0] == "off":
            return "off", top[1], "frontmatter"
        return "user-invocable-only", "frontmatter", "frontmatter"
    return (top[0], top[1], None) if top else ("on", "default", None)


def predict(e: dict, target: str, scope: str) -> str | None:
    """Role after setting `target` at `scope` (global | project); mirrors apply_plan.py."""
    if e["scope"] not in OVERRIDABLE or e.get("locked") == "policy":
        return e.get("role")
    layers = dict(e["layers"])
    if scope == "global":
        if target == "on":
            layers.pop("global", None)
        else:
            layers["global"] = target
    else:
        lower = layers.get("project-shared", layers.get("global"))
        if target == "on" and lower in (None, "on"):
            layers.pop("project", None)
        else:
            layers["project"] = target
    probe = {**e, "layers": layers}
    return resolve(probe, {}, {})[0]


def build(project: Path, listed: dict[str, str] | None = None) -> dict:
    """Inventory for `project`. `listed` maps skill names in a session's listing to their text."""
    project = project.resolve()
    files = layer_files(project)
    settings = {k: load_json(p, {}) or {} for k, p in files.items()}
    ov = {
        k: {n: v for n, v in (s.get("skillOverrides") or {}).items() if v in STATES}
        for k, s in settings.items()
    }
    policy: dict[str, str] = {}
    for m in MANAGED:
        policy.update(((load_json(m, {}) or {}).get("skillOverrides")) or {})

    skills: dict[str, dict] = {}

    def put(e: dict):
        if e["name"] in skills:
            skills[e["name"]].setdefault("shadows", []).append(e["where"])
        else:
            skills[e["name"]] = e

    # project skills first: a project skill shadows a personal one of the same name
    pdir = project / ".claude"
    for md in sorted((pdir / "skills").glob("*/SKILL.md")):
        put(_entry(md.parent.name, "skill", "project", md, tilde(md.parent)))
    for md in sorted((pdir / "commands").glob("*.md")):
        put(_entry(md.stem, "command", "project", md, tilde(md)))

    plugins: dict[str, dict] = {}
    broken: list[str] = []
    gdir = CLAUDE_DIR / "skills"
    for d in sorted(gdir.iterdir()) if gdir.is_dir() else []:
        if d.name.startswith(".") or d.name == "synced":
            continue
        if d.is_symlink() and not d.exists():
            broken.append(f"{tilde(d)} → {tilde(os.readlink(d))}")
            continue
        if _is_plugin_dir(d):
            short = _manifest(d).get("name") or d.name
            plugins[short] = {"name": short, "id": None, "kind": "skills-dir", "enabled": True,
                              "set_by": None, "where": tilde(d.resolve()), "members": []}
            for full, md, kind in plugin_members(d, short):
                put(_entry(full, kind, "plugin", md, f"plugin {short}", plugin=short))
                plugins[short]["members"].append(full)
        elif (d / "SKILL.md").exists():
            where = tilde(d) + (f" → {tilde(d.resolve())}" if d.is_symlink() else "")
            put(_entry(d.name, "skill", "global", d / "SKILL.md", where))
    for md in sorted((CLAUDE_DIR / "commands").glob("*.md")):
        put(_entry(md.stem, "command", "global", md, tilde(md)))
    for man in sorted((gdir / "synced").glob("*/manifest.json")):
        for s in (load_json(man, {}) or {}).get("skills") or []:
            n = s.get("name")
            if n:
                md = man.parent / n / "SKILL.md"
                put(_entry(f"{ACCOUNT_PREFIX}:{n}", "skill", "account",
                           md if md.exists() else None, "claude.ai account"))

    enabled = merged(settings, "enabledPlugins")
    inst = load_json(CLAUDE_DIR / "plugins" / "installed_plugins.json", {}) or {}
    for pid, entries in (inst.get("plugins") or {}).items():
        short = pid.split("@")[0]
        e0 = entries[0] if isinstance(entries, list) and entries else entries or {}
        val, layer = enabled.get(pid, (None, None))
        prev = plugins.get(short)
        if prev and (prev["enabled"] or val is not True):
            continue  # same short name from two marketplaces: keep the enabled one
        root = Path(e0.get("installPath") or "")
        plugins[short] = {"name": short, "id": pid, "kind": "marketplace", "enabled": val is True,
                          "set_by": layer, "where": pid, "members": []}
        for full, md, kind in plugin_members(root, short):
            put(_entry(full, kind, "plugin", md, f"plugin {pid}", plugin=short))
            plugins[short]["members"].append(full)
    for m in (CLAUDE_DIR / "plugins" / "synced").glob("*/manifest.json"):
        for p in (load_json(m, {}) or {}).get("plugins") or []:
            if p.get("name") and p["name"] not in plugins:
                plugins[p["name"]] = {"name": p["name"], "id": None, "kind": "synced", "enabled": True,
                                      "set_by": None, "where": "claude.ai organization", "members": []}

    # names only the session listing knows: bundled skills, org-synced plugin skills
    for name in listed or {}:
        if name in skills:
            continue
        prefix = name.split(":", 1)[0] if ":" in name else None
        if prefix is None:
            put(_entry(name, "skill", "bundled", None, "ships with Claude Code"))
        elif prefix == ACCOUNT_PREFIX:
            put(_entry(name, "skill", "account", None, "claude.ai account"))
        elif plugins.get(prefix, {}).get("kind") in ("marketplace", "skills-dir"):
            put(_entry(name, "skill", "plugin", None, f"plugin {prefix}", plugin=prefix))
            plugins[prefix]["members"].append(name)
        else:
            put(_entry(name, "skill", "synced", None, f"{prefix} (claude.ai organization)"))
    for e in skills.values():
        if listed and e["name"] in listed:
            e["listing_chars"] = len(listed[e["name"]]) + 1

    # other projects: where a skill is switched differently, and skills that live only there
    others = known_projects(project)
    for p in others:
        pfiles = layer_files(p)
        for layer in ("project-shared", "project"):
            s = load_json(pfiles[layer], {}) or {}
            for n, v in (s.get("skillOverrides") or {}).items():
                if (n in skills and skills[n]["scope"] in OVERRIDABLE and v in STATES
                        and v != ov["global"].get(n, "on")):
                    skills[n]["elsewhere"].append({"project": tilde(p), "layer": layer, "value": v})
            for pid, v in (s.get("enabledPlugins") or {}).items():
                short = pid.split("@")[0]
                if short in plugins and v != (enabled.get(pid, (None,))[0] is True):
                    plugins[short].setdefault("elsewhere", []).append(
                        {"project": tilde(p), "layer": layer, "value": "on" if v else "off"})
        for md in sorted((p / ".claude" / "skills").glob("*/SKILL.md")):
            n = md.parent.name
            if n not in skills:
                put(_entry(n, "skill", "elsewhere", md, tilde(md.parent)))
            if skills[n]["scope"] == "elsewhere":
                skills[n]["installed_in"].append(tilde(p))

    for e in skills.values():
        e["layers"] = {k: ov[k][e["name"]] for k in LAYERS if e["name"] in ov[k]}
        e["role"], e["set_by"], e["locked"] = resolve(e, policy, plugins)

    stale = [
        {"name": n, "layers": {k: ov[k][n] for k in LAYERS if n in ov[k]}}
        for n in sorted({n for k in LAYERS for n in ov[k]} - set(skills))
    ]
    mtimes = [f.stat().st_mtime for f in files.values() if f.exists()]
    return {
        "project": tilde(project),
        "files": {k: tilde(v) for k, v in files.items()},
        "skills": sorted(skills.values(), key=lambda e: e["name"]),
        "plugins": sorted(plugins.values(), key=lambda p: p["name"]),
        "stale": stale,
        "broken_links": broken,
        "projects_scanned": len(others),
        "disable_bundled": bool(settings["global"].get("disableBundledSkills")),
        "settings_mtime": max(mtimes) if mtimes else 0,
    }


def tokens(e: dict, role: str | None, cpt: float = CPT) -> int:
    """Listing cost of one skill in a given role."""
    if role == "on":
        return round(e["listing_chars"] / cpt)
    if role == "name-only":
        return max(1, round((len(f"- {e['name']}") + 1) / cpt))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", default=os.getcwd())
    args = ap.parse_args()
    print(json.dumps(build(Path(args.project)), indent=1))


if __name__ == "__main__":
    main()
