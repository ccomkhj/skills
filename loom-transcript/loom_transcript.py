#!/usr/bin/env python3
"""Fetch a public Loom video's transcript. Stdlib only.

Usage: python loom_transcript.py <loom-url> [--timestamps]
Prints JSON to stdout. On failure prints {"error": ...} and exits 1.
"""
import json
import re
import sys
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"


def fail(msg):
    print(json.dumps({"error": msg}))
    sys.exit(1)


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def video_id(url):
    m = re.search(r"loom\.com/(?:share|embed)/([0-9a-f]{32})", url)
    return m.group(1) if m else None


def parse_vtt(vtt):
    """Return (plain_text, segments). segments = [{start, text}]."""
    segments = []
    for block in re.split(r"\n\s*\n", vtt.strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines or lines[0].startswith("WEBVTT"):
            continue
        ts = next((l for l in lines if "-->" in l), None)
        if ts is None:
            continue
        start = ts.split("-->")[0].strip().split(".")[0]
        text_lines = lines[lines.index(ts) + 1:]
        text = re.sub(r"<[^>]*>", "", " ".join(text_lines)).strip()
        if text:
            segments.append({"start": start, "text": text})
    plain = " ".join(s["text"] for s in segments)
    return plain, segments


def main():
    args = [a for a in sys.argv[1:] if a != "--timestamps"]
    want_ts = "--timestamps" in sys.argv[1:]
    if not args:
        fail("No Loom URL given. Usage: loom_transcript.py <url> [--timestamps]")

    vid = video_id(args[0])
    if not vid:
        fail("Not a Loom share link. Expected loom.com/share/<32-char-id>.")

    # Metadata via oEmbed. Failure here => video does not exist or is private.
    try:
        meta = json.loads(get(f"https://www.loom.com/v1/oembed?url=https://www.loom.com/share/{vid}"))
    except urllib.error.HTTPError:
        fail("Video not found or private. I can only read public/shareable Loom videos.")
    except urllib.error.URLError as e:
        fail(f"Network error reaching Loom: {e.reason}")

    # Signed transcript URL is embedded in the share page HTML.
    try:
        html = get(f"https://www.loom.com/share/{vid}")
    except urllib.error.URLError as e:
        fail(f"Network error reaching Loom: {e.reason}")

    m = re.search(r"https://cdn\.loom\.com/mediametadata/captions/[^\"'\\]+\.vtt[^\"'\\]*", html)
    if not m:
        fail("This Loom has no transcript available (captions not generated, or the video is private).")

    try:
        vtt = get(m.group(0).replace("\\u0026", "&").replace("&amp;", "&"))
    except urllib.error.URLError as e:
        fail(f"Network error fetching transcript: {e.reason}")

    plain, segments = parse_vtt(vtt)
    if not plain:
        fail("This Loom has no transcript available (captions empty).")

    out = {
        "title": meta.get("title"),
        "duration_seconds": meta.get("duration"),
        "description": meta.get("description"),
        "transcript": plain,
    }
    if want_ts:
        out["segments"] = segments
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
