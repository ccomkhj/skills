#!/usr/bin/env python3
"""Print the user's own typed prompts from recent Claude Code sessions, oldest first."""
import argparse, json, os, re, time
from pathlib import Path

ROOT = Path.home() / ".claude" / "projects"
SECRET = re.compile(r"(sk-[\w-]{16,}|gh[pousr]_\w{20,}|AKIA[0-9A-Z]{16}|xox[abp]-[\w-]{10,}|eyJ[\w-]{20,}\.[\w.-]+|\b[A-Za-z0-9+/_-]{40,}\b)")


def text_of(entry):
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return None
    c = entry.get("message", {}).get("content")
    if not isinstance(c, str):  # lists carry tool results / injected text
        return None
    args = re.search(r"<command-args>(.*?)</command-args>", c, re.S)
    if args:
        c = args.group(1)
    elif c.lstrip().startswith(("<", "Caveat:", "[Request interrupted")):
        return None
    c = re.sub(r"<pasted_content.*?</pasted_content>|\[Pasted text[^\]]*\]", "", c, flags=re.S)
    c = re.sub(r"\s+", " ", SECRET.sub("[REDACTED]", c)).strip()
    return c or None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--all", action="store_true", help="every project, not just the cwd's")
    p.add_argument("--days", type=float, help="only sessions modified in the last N days")
    p.add_argument("--sessions", type=int, default=10, help="newest N sessions (ignored with --days)")
    p.add_argument("--limit", type=int, default=200, help="keep the newest N prompts")
    p.add_argument("--chars", type=int, default=300, help="truncate each prompt")
    a = p.parse_args()

    here = ROOT / re.sub(r"[^A-Za-z0-9]", "-", os.getcwd())
    files = sorted(ROOT.glob("*/*.jsonl") if a.all else here.glob("*.jsonl"),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    if a.days:
        files = [f for f in files if f.stat().st_mtime > time.time() - a.days * 86400]
    else:
        files = files[: a.sessions]

    rows = []
    for f in files:
        for line in f.open(errors="ignore"):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            t = text_of(e)
            if t:
                rows.append((e.get("timestamp", ""), f.parent.name if a.all else "", t))
    rows.sort()
    for ts, proj, t in rows[-a.limit:]:
        t = t if len(t) <= a.chars else t[: a.chars] + "…"
        print(f"{ts[:10]}{' ' + proj if proj else ''}: {t}")
    if not rows:
        print("No prompts found.")


if __name__ == "__main__":
    main()
