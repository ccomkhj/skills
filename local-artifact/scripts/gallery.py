#!/usr/bin/env python3
"""Local artifact gallery: publish, list, open, delete HTML pages.

Each page lives in <root>/<slug>/ with index.html (plus any supporting files)
and meta.json. Root is $LOCAL_ARTIFACTS_DIR or ~/.local/share/local-artifacts.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("LOCAL_ARTIFACTS_DIR", "~/.local/share/local-artifacts")).expanduser()
MAX_BYTES = 16 * 1024 * 1024
SCRIPT_HOSTS = ("cdnjs.cloudflare.com", "cdn.jsdelivr.net/npm/", "unpkg.com",
                "cdn.tailwindcss.com", "code.jquery.com")
STYLE_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "page"


def title_of(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return m.group(1).strip() if m else ""


def check(html, size):
    """Return contract warnings (see references/page-contract.md)."""
    warn = []
    title = title_of(html)
    if not title:
        warn.append("no <title>")
    elif not 2 <= len(title.split()) <= 4 or ":" in title:
        warn.append(f"title {title!r} should be a 2-4 word name, no colon")
    if size > MAX_BYTES:
        warn.append(f"page is {size / 1e6:.1f} MB, limit 16 MB")
    if not re.search(r":root\s*\{[^}]*--", html):
        warn.append("no color tokens (--vars) on :root")
    if not re.search(r"prefers-color-scheme:\s*dark", html):
        warn.append("no @media (prefers-color-scheme: dark) override")
    if not re.search(r':root\[data-theme="dark"\]', html):
        warn.append('no :root[data-theme="dark"] override')
    if not re.search(r"body\s*\{[^}]*background", html, re.S):
        warn.append("body has no explicit background")
    for src in re.findall(r"<script[^>]+src=[\"']([^\"']+)", html, re.I):
        if not src.startswith(("http:", "https:", "//")):
            continue
        if not any(h in src for h in SCRIPT_HOSTS):
            warn.append(f"script host not allowed: {src}")
        elif "tailwindcss" not in src and not re.search(r"@\d+\.\d+\.\d+|/\d+\.\d+\.\d+/", src):
            warn.append(f"script not pinned to an exact version: {src}")
    for href in re.findall(r"<link[^>]+href=[\"'](https?:[^\"']+)", html, re.I):
        if not any(h in href for h in STYLE_HOSTS):
            warn.append(f"external stylesheet not from Google Fonts: {href}")
    if re.search(r"localStorage|sessionStorage", html) and "catch" not in html:
        warn.append("browser storage used without try/catch")
    return warn


def load_meta(d):
    try:
        return json.loads((d / "meta.json").read_text())
    except (OSError, ValueError):
        return {"slug": d.name, "title": d.name, "updated": ""}


def entries():
    if not ROOT.is_dir():
        return []
    metas = [load_meta(d) for d in ROOT.iterdir() if (d / "index.html").is_file()]
    return sorted(metas, key=lambda m: m.get("updated", ""), reverse=True)


def open_path(p):
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([opener, str(p)], check=False)


def cmd_publish(a):
    src = Path(a.path).expanduser().resolve()
    page = src / "index.html" if src.is_dir() else src
    if not page.is_file():
        sys.exit(f"✗ {page} not found")
    html = page.read_text(errors="replace")
    slug = a.slug or slugify(title_of(html) or src.stem)
    dest = ROOT / slug
    existed = dest.is_dir()
    meta = load_meta(dest) if existed else {"created": now()}
    staged = ROOT / f".{slug}.tmp"
    shutil.rmtree(staged, ignore_errors=True)
    if src.is_dir():
        shutil.copytree(src, staged)
    else:
        staged.mkdir(parents=True)
        shutil.copy2(src, staged / "index.html")
    size = sum(f.stat().st_size for f in staged.rglob("*") if f.is_file())
    meta.update(slug=slug, title=title_of(html) or slug, source=str(src), updated=now())
    if a.description:
        meta["description"] = a.description
    (staged / "meta.json").write_text(json.dumps(meta, indent=2))
    shutil.rmtree(dest, ignore_errors=True)
    staged.rename(dest)
    url = (dest / "index.html").as_uri()
    print(f"{'updated' if existed else 'published'} {slug}\n{url}")
    for w in check(html, size):
        print(f"  ! {w}")
    if not a.no_open:
        open_path(dest / "index.html")


def cmd_list(a):
    rows = entries()[: a.limit]
    if not rows:
        print(f"(no pages in {ROOT})")
    for m in rows:
        desc = f" — {m['description']}" if m.get("description") else ""
        print(f"{m['slug']:<32} {m.get('updated', '')[:16]:<17} {m.get('title', '')}{desc}")


def cmd_open(a):
    page = ROOT / a.slug / "index.html"
    if not page.is_file():
        sys.exit(f"✗ no page {a.slug!r}; run list")
    print(page.as_uri())
    open_path(page)


def cmd_link(a):
    d = ROOT / a.slug
    if not (d / "index.html").is_file():
        sys.exit(f"✗ no page {a.slug!r}")
    meta = load_meta(d)
    meta["artifact_url"] = a.url
    (d / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"linked {a.slug} → {a.url}")


def cmd_delete(a):
    d = ROOT / a.slug
    if not (d / "index.html").is_file():
        sys.exit(f"✗ no page {a.slug!r}")
    if not a.yes:
        sys.exit(f"would delete {d} (pass --yes after the user confirms)")
    shutil.rmtree(d)
    print(f"deleted {a.slug}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("publish", help="copy a page (file or dir with index.html) into the gallery")
    s.add_argument("path")
    s.add_argument("--slug", help="gallery name; reuse one to update that page")
    s.add_argument("--description", help="one sentence shown in list")
    s.add_argument("--no-open", action="store_true")
    s.set_defaults(fn=cmd_publish)
    s = sub.add_parser("list", help="pages, most recently updated first")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(fn=cmd_list)
    s = sub.add_parser("open", help="open a page in the browser")
    s.add_argument("slug")
    s.set_defaults(fn=cmd_open)
    s = sub.add_parser("link", help="remember the claude.ai artifact URL of a page")
    s.add_argument("slug")
    s.add_argument("url")
    s.set_defaults(fn=cmd_link)
    s = sub.add_parser("delete", help="remove a page permanently")
    s.add_argument("slug")
    s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_delete)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
