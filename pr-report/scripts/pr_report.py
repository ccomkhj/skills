#!/usr/bin/env python3
"""PR health dashboard for one GitHub repo. Read-only; python3 stdlib + authenticated `gh`.

usage: pr_report.py [OWNER/REPO | URL] [--all] [--html] [--json PATH]
  (no repo)    current directory's repo, via `gh repo view`
  --all        list every open PR in the markdown, not just the 10 most urgent
  --html       also write a static page to ~/.cache/pr-report/ and open it
  --json PATH  write a small snapshot of the headline numbers (for comparing runs later)

Markdown goes to stdout. Definitions and thresholds: ../references/metrics.md
"""
import argparse, html, json, math, os, re, statistics, subprocess, sys, time, webbrowser
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
QUERY = os.path.join(HERE, "pr_query.graphql")
NOW = datetime.now(timezone.utc)
PAGE, OPEN_CAP, MERGED_CAP, MD_ROWS = 25, 100, 300, 10
NOT_DEPS = "-author:app/dependabot -author:app/renovate"
AI_RE = re.compile(r"copilot|coderabbit|claude|codex|cursor|devin|sourcery|greptile|\[bot\]$", re.I)
DEP_BOT_RE = re.compile(r"dependabot|renovate|github-actions|pre-commit|mergify|snyk", re.I)
REVERT_RE = re.compile(r'^Revert "|Reverts [\w./-]*#\d+|This reverts commit', re.M)
DOOR_RE = re.compile(r"\*\*Door:\*\*\s*(one|two)-way", re.I)
ICON = {"g": "🟢", "a": "🟡", "r": "🔴", "na": "⚪"}
PROMO_HEADS = ("dev", "develop")
# 🟢 below the first number, 🟡 up to the second, 🔴 beyond. Lower is better except coverage.
# One copy: grading and the "good:" hints both read it. Sources: ../references/metrics.md
LIMIT = {"cycle": (25, 72), "pickup": (4, 16), "size": (155, 228), "unreviewed": (.05, .2),
         "red_ci": (.001, .05), "reverts": (.0501, .15), "coverage": (.8, .5)}
BUCKETS = ((10, "XS", "tiny"), (100, "S", "small"), (400, "M", "medium"), (1000, "L", "large"), (math.inf, "XL", "huge"))


# ---------- fetch ----------
def gh(args, tries=3):
    err = ""
    for i in range(tries):
        out = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
        try:
            d = json.loads(out.stdout or "{}")
        except json.JSONDecodeError:
            d = {}
        if out.returncode == 0 and not d.get("errors"):
            return d
        err = (d.get("errors") or [{}])[0].get("message") or out.stderr.strip()
        if "Could not resolve" in err or "auth" in err.lower():
            break
        time.sleep(2 * (i + 1))  # GitHub 502s / partial RESOURCE_LIMITS pages are transient
    sys.exit(f"gh api failed: {err}")


def search_prs(q, cap):
    nodes, cursor, total = [], None, 0
    while len(nodes) < cap:
        a = ["graphql", "-F", f"query=@{QUERY}", "-f", f"q={q}", "-F", f"pageSize={PAGE}"]
        if cursor:
            a += ["-f", f"cursor={cursor}"]
        page = gh(a)["data"]["search"]
        nodes += [n for n in page["nodes"] if n]
        total = page["issueCount"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return nodes[:cap], total


def pick_window(repo):
    """90d, or 30d once 20 PRs merged there (enough to grade). Busy repos shrink to 14d/7d so every
    merged PR in the window is fetched in under a minute instead of sampling some."""
    parts = []
    for d in (90, 30, 14, 7):
        day = f"{NOW - timedelta(days=d):%Y-%m-%d}"
        parts.append(f'm{d}: search(query:"repo:{repo} is:pr is:merged merged:>={day} {NOT_DEPS}", type:ISSUE, first:0){{issueCount}}')
        parts.append(f'c{d}: search(query:"repo:{repo} is:pr is:closed is:unmerged closed:>={day} {NOT_DEPS}", type:ISSUE, first:0){{issueCount}}')
    parts.append(f'drafts: search(query:"repo:{repo} is:pr is:open draft:true", type:ISSUE, first:0){{issueCount}}')
    c = {k: v["issueCount"] for k, v in gh(["graphql", "-f", "query={" + " ".join(parts) + "}"])["data"].items()}
    win = 30 if c["m30"] >= 20 else 90
    for short in (14, 7):
        if c[f"m{win}"] > 150 and c[f"m{short}"] >= 20:
            win = short
    return win, c


def fetch_meta(owner, name, since):
    q = """query($o:String!,$n:String!,$s:GitTimestamp!){repository(owner:$o,name:$n){
      defaultBranchRef{name target{... on Commit{history(since:$s,first:100){totalCount
        nodes{committedDate associatedPullRequests(first:1){totalCount}}}}}}
      dev:ref(qualifiedName:"refs/heads/dev"){name} develop:ref(qualifiedName:"refs/heads/develop"){name}}}"""
    r = gh(["graphql", "-f", f"query={q}", "-f", f"o={owner}", "-f", f"n={name}", "-f", f"s={iso(since)}"])["data"]["repository"]
    ref = r["defaultBranchRef"] or {}
    h = (ref.get("target") or {}).get("history") or {"totalCount": 0, "nodes": []}
    meta = {"default": ref.get("name", "main"), "history_total": h["totalCount"],
            "history": [(c["committedDate"], c["associatedPullRequests"]["totalCount"] > 0) for c in h["nodes"]],
            "dev": next((b["name"] for b in (r["dev"], r["develop"]) if b and b["name"] != ref.get("name")), None)}
    if meta["dev"]:
        c = gh([f"repos/{owner}/{name}/compare/{meta['default']}...{meta['dev']}"])
        meta["promo_ahead"] = c.get("ahead_by", 0)
        meta["promo_oldest"] = min((x["commit"]["committer"]["date"] for x in c.get("commits", [])), default=None)
    return meta


# ---------- helpers ----------
def ts(s): return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None
def iso(d): return d.strftime("%Y-%m-%dT%H:%M:%SZ")
def login(x): return (x or {}).get("login") or "ghost"
def is_ai(a): return (a or {}).get("__typename") == "Bot" or bool(AI_RE.search(login(a)))
def is_dep_bot(p): return (p["author"] or {}).get("__typename") == "Bot" and bool(DEP_BOT_RE.search(login(p["author"])))
def hours(a, b): return (b - a).total_seconds() / 3600 if a and b else None
def size(p): return p["additions"] + p["deletions"]
def bucket(n): return next(b for lim, b, _ in BUCKETS if n < lim)
def plural(n, w): return f"{n:g} {w}{'s' * (n != 1)}"
def pct(a, b): return f"{100 * a / b:.0f}%" if b else "N/A"
def nums(ps): return " ".join(f"#{p['number']}" for p in ps)
def grade(v, g, a): return "g" if v < g else "a" if v <= a else "r"  # lower is better


def last_commit(p):
    c = p["commits"]["nodes"]
    return c[0]["commit"] if c else {}


def checks(p): return ((last_commit(p).get("statusCheckRollup") or {}).get("contexts") or {}).get("nodes") or []


def ci_state(p):
    """CI from individual checks, minus the pr-classify verdict: GitHub's rollup would count a reject as red CI."""
    cs = [c for c in checks(p) if c.get("context") != "pr-classify"]
    if not cs: return None
    if any(c.get("conclusion") in ("FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE")
           or c.get("state") in ("FAILURE", "ERROR") for c in cs): return "FAILURE"
    if any((c["__typename"] == "CheckRun" and c.get("status") != "COMPLETED") or c.get("state") in ("PENDING", "EXPECTED")
           for c in cs): return "PENDING"
    return "SUCCESS"


def verdict(p):
    d = next((c.get("description") or "" for c in checks(p) if c.get("context") == "pr-classify"), "")
    m = re.search(r"reject|safe|review", d, re.I)
    return m.group(0).lower() if m else None


def ready_at(p):
    """Opened as draft → the first ready event; otherwise createdAt. Draft time never counts as waiting."""
    for n in p["timelineItems"]["nodes"]:
        if n["__typename"] == "ReadyForReviewEvent":
            return ts(n["createdAt"])
        if n["__typename"] == "ConvertToDraftEvent":
            break
    return ts(p["createdAt"])


def human_reviews(p):
    me = login(p["author"])
    return [r for r in p["reviews"]["nodes"]
            if r["state"] != "PENDING" and r["submittedAt"] and not is_ai(r["author"]) and login(r["author"]) != me]


def bot_reviews(p): return [r for r in p["reviews"]["nodes"] if r["state"] != "PENDING" and is_ai(r["author"])]


def bdays(a, b):
    """Weekdays between a and b, fractional: a PR idle over a weekend has not waited two days."""
    d, t = 0.0, a
    while t < b:
        nxt = min(b, (t + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0))
        if t.weekday() < 5:
            d += (nxt - t).total_seconds() / 86400
        t = nxt
    return d


def dur(h):
    if h is None: return "N/A"
    if h < 1 / 60: return f"{h * 3600:.0f}s"
    if h < 1: return f"{h * 60:.0f}m"
    if h < 48: return f"{h:.0f}h"
    return f"{h / 24:.0f}d"


def card(m, label, xs, g, v, fmt=dur):
    """Headline card: p75 when graded (n>=20), else the median, labelled as such."""
    xs = [x for x in xs if x is not None]
    val = fmt(v) if v is not None else fmt(statistics.median(xs)) if xs else "N/A"
    m["cards"].append((f"{label} ({'p75' if v is not None else 'median'})", val, plural(len(xs), "PR"), g))


def stat(xs, key=None, fmt=dur, verb="within"):
    """Median/p75 with n, in words. n<10: raw values, ungraded. 10-19: median only. n>=20: p75 graded."""
    xs = sorted(x for x in xs if x is not None)
    n = len(xs)
    if n == 0: return "na", None, None
    if n < 10: return "na", f"{', '.join(fmt(x) for x in xs)} (only {plural(n, 'PR')}, too few to grade)", None
    half = f"half of {n} PRs {verb} {fmt(statistics.median(xs))}"
    if n < 20 or key is None: return "na", half, None
    p75 = statistics.quantiles(xs, n=4)[2]
    return grade(p75, *LIMIT[key]), f"{half}, 75% {verb} {fmt(p75)}", p75


def row(g, label, value, na="", about="", good=""):
    """One metric row. `about` and `good` are the plain-English line under the label in the HTML."""
    return {"g": g, "label": label, "value": value, "na": na, "about": about, "good": good}


# ---------- open queue ----------
def reviewer_name(r):
    if not r: return "hidden team"  # token can't read the org's teams
    return "team:" + r["slug"] if r.get("slug") else login(r)


def last_human_event(p):
    t = [ready_at(p), ts(last_commit(p).get("committedDate"))]
    t += [ts(r["submittedAt"]) for r in p["reviews"]["nodes"] if r["submittedAt"] and not is_ai(r["author"])]
    t += [ts(c["createdAt"]) for c in p["comments"]["nodes"] if not is_ai(c["author"])]
    t += [ts(n["createdAt"]) for n in p["timelineItems"]["nodes"] if n["__typename"] == "HeadRefForcePushedEvent"]
    return max(x for x in t if x)


def blocker(p):
    s, ci = p.get("mergeStateStatus"), ci_state(p)
    if s == "DIRTY": return "conflict"
    if ci in ("FAILURE", "ERROR"): return "CI red"
    if ci in ("PENDING", "EXPECTED"): return "CI pending"
    if s == "BEHIND": return "behind"
    if s == "BLOCKED":
        return {"REVIEW_REQUIRED": "needs review", "CHANGES_REQUESTED": "changes req"}.get(p["reviewDecision"], "blocked")
    if verdict(p) in ("reject", "review"): return f"classify: {verdict(p)}"
    return "clean" if s in ("CLEAN", "HAS_HOOKS", "UNSTABLE") else ""


def waiting_on(p, solo):
    """(kind, names): who has to act next. The point of the queue is to name a person."""
    hr, b = human_reviews(p), blocker(p)
    last = hr[-1] if hr else None
    on_head = bool(last and last.get("commit") and last["commit"]["oid"] == p["headRefOid"])
    if b in ("conflict", "CI red", "behind", "classify: reject") or p["reviewDecision"] == "CHANGES_REQUESTED" \
            or (on_head and last["state"] == "CHANGES_REQUESTED"):
        return "author", [login(p["author"])]
    reqs = sorted({reviewer_name(n["requestedReviewer"]) for n in p["reviewRequests"]["nodes"]},
                  key=lambda x: (" " in x or x.startswith("team:"), x))  # people before teams
    if reqs: return "reviewer", reqs
    if p["reviewDecision"] == "APPROVED" or (on_head and last["state"] == "APPROVED"):
        return "merger", []
    if last and not on_head:  # pushed since the last review
        return "reviewer", sorted({login(r["author"]) for r in hr})
    return ("author", [login(p["author"])]) if solo else ("nobody", [])


def open_queue(open_prs, solo):
    rows = []
    for p in open_prs:
        if p["isDraft"] or is_dep_bot(p): continue
        idle = bdays(last_human_event(p), NOW)
        kind, who = waiting_on(p, solo)
        rows.append({"p": p, "idle": idle, "age": hours(ready_at(p), NOW), "kind": kind, "who": who,
                     "blocker": blocker(p), "g": "r" if idle > 5 else "a" if idle > 1 else "g"})
    # Freshest red first: a PR idle 6 days can still be saved; one idle 200 days is a close-or-adopt call.
    rows.sort(key=lambda r: ({"r": 0, "a": 1, "g": 2}[r["g"]], r["idle"]))
    queue = {}
    for r in rows:
        events = r["p"]["timelineItems"]["nodes"]
        for n in r["p"]["reviewRequests"]["nodes"]:
            who = reviewer_name(n["requestedReviewer"])
            at = [ts(e["createdAt"]) for e in events if e["__typename"] == "ReviewRequestedEvent"
                  and reviewer_name(e.get("requestedReviewer")) == who]
            queue.setdefault(who, []).append(max(at) if at else ready_at(r["p"]))
    queue = sorted(((k, len(v), hours(min(v), NOW)) for k, v in queue.items()), key=lambda x: (-x[1], -x[2]))
    return rows, queue


# ---------- metrics ----------
def compute(owner, name, win, counts, fetched, open_prs, open_total, meta):
    start = NOW - timedelta(days=win)
    is_promo = lambda p: p["headRefName"] in PROMO_HEADS and p["baseRefName"] == meta["default"]
    in_win = [p for p in fetched if p["mergedAt"] and ts(p["mergedAt"]) >= start]
    merged = [p for p in in_win if not is_dep_bot(p) and not is_promo(p)]
    promos = [p for p in in_win if is_promo(p)]
    dep = [p for p in in_win if is_dep_bot(p)]
    closed = counts[f"c{win}"]

    authors = Counter(login(p["author"]) for p in merged + [p for p in open_prs if not p["isDraft"] and not is_dep_bot(p)])
    top_author, top_n = authors.most_common(1)[0] if authors else ("", 0)
    solo = bool(authors) and top_n / sum(authors.values()) >= 0.9 and not any(human_reviews(p) for p in merged)
    rows, queue = open_queue(open_prs, solo)

    m = {"repo": f"{owner}/{name}", "solo": solo, "solo_who": top_author, "solo_n": (top_n, sum(authors.values())),
         "win": win, "n": len(merged), "rows": rows, "queue": queue, "not_fetched": max(0, open_total - len(open_prs)),
         "unfetched_idle": bdays(min((ts(p["updatedAt"]) for p in open_prs), default=NOW), NOW),
         "sampled": (len(fetched), counts[f"m{win}"]) if counts[f"m{win}"] > len(fetched) else None,
         "drafts": counts["drafts"], "dep_open": sum(1 for p in open_prs if is_dep_bot(p)),
         "sections": [], "cards": [], "scatter": []}
    S = lambda title, rs: m["sections"].append((title, rs))  # rs: row() dicts; value None → listed as N/A
    red = [r for r in rows if r["g"] == "r"]
    m["cards"].append(("Open, ready for review", str(len(rows) + m["not_fetched"]),
                       f"{len(red)} idle >5 business days" + (f" · {m['not_fetched']} not fetched" if m["not_fetched"] else ""),
                       "r" if red else "a" if any(r["g"] == "a" for r in rows) else "g"))

    # Flow: cycle time hides PRs that never merge, which is why the open queue comes first.
    cyc = [hours(ready_at(p), ts(p["mergedAt"])) for p in merged]
    g, s, v = stat(cyc, "cycle", verb="merged within")
    flow = [row(g, "Time to merge", s, "no merged PRs", "cycle time: opened (or marked ready) → merged",
                f"75% within {dur(LIMIT['cycle'][0])}")]
    card(m, "Time to merge", cyc, g, v)
    pick, rev, mrg = [], [], []
    for p in merged:
        hr = sorted(human_reviews(p), key=lambda r: r["submittedAt"])
        if not hr: continue
        ra, first = ready_at(p), ts(hr[0]["submittedAt"])
        pick.append(max(0.0, hours(ra, first)))
        appr = [ts(r["submittedAt"]) for r in hr if r["state"] == "APPROVED"]
        if appr:
            rev.append(hours(first, max(appr))); mrg.append(max(0.0, hours(max(appr), ts(p["mergedAt"]))))
    if not solo:
        g, s, v = stat(pick, "pickup", verb="got a first review within")
        flow.append(row(g, "Wait for first review", s, "no human reviews",
                        "pickup: opened → first review by a person (bots don't count)", f"75% within {dur(LIMIT['pickup'][0])}"))
        card(m, "Wait for first review", pick, g, v)
        if pick:
            med = lambda xs: statistics.median(xs) if xs else 0
            st = {"waiting for review": med(pick), "in review": med(rev), "approved → merged": med(mrg)}
            flow.append(row("na", "Where the time goes", " / ".join(f"{k} {dur(x)}" for k, x in st.items())
                            + f" → slowest: **{max(st, key=st.get)}**", "",
                            f"medians over the {plural(len(pick), 'PR')} a person reviewed, so they need not add up to time to merge"))
    S("Flow", flow)

    # Review: human and AI kept apart; bots review in minutes and would make pickup look elite.
    if not solo:
        none_ = [p for p in merged if not human_reviews(p)]
        bot_only = [p for p in none_ if bot_reviews(p)]
        un = len(none_) / len(merged) if merged else None
        rv = Counter(l for p in merged for l in {login(r["author"]) for r in human_reviews(p)})
        reviewed = len(merged) - len(none_)
        depth = [len({login(r["author"]) for r in human_reviews(p)}) for p in merged if human_reviews(p)]
        rounds = [len({r["commit"]["oid"] for r in human_reviews(p) if r.get("commit")}) for p in merged if human_reviews(p)]
        ai = [p for p in merged if bot_reviews(p)]
        ai_appr = [p for p in merged if any(r["state"] == "APPROVED" for r in bot_reviews(p))
                   and not any(r["state"] == "APPROVED" for r in human_reviews(p))]
        rs = [row(grade(un, *LIMIT["unreviewed"]) if un is not None else "na", "Merged with no human review",
                  f"{len(none_)} of {len(merged)} ({pct(len(none_), len(merged))})"
                  + (f" · {len(bot_only)} of them had only a bot review" if bot_only else "") if merged else None,
                  "no merged PRs", "", f"under {LIMIT['unreviewed'][0]:.0%}"),
              row("na", "Review depth", f"typically {plural(statistics.median(depth), 'reviewer')} · "
                  f"{pct(sum(1 for x in rounds if x >= 2), len(rounds))} needed 2+ rounds" if depth else None,
                  "no human reviews", "over PRs a person reviewed; a new round = a review of newer commits")]
        if len(rv) >= 3:
            top, c = rv.most_common(1)[0]
            rs.append(row("r" if c / reviewed > .5 else "g", "Top reviewer's share", f"{pct(c, reviewed)} ({top}, {len(rv)} reviewers)",
                          "", "share of reviewed PRs that one person reviewed", "50% or less"))
        rs.append(row("a" if ai_appr else "na", "AI / bot review",
                      f"{pct(len(ai), len(merged))} of PRs · {len(ai_appr)} approved by bot only" + (f": {nums(ai_appr[:6])}" if ai_appr else "")
                      if ai else None, "no bot reviews", "kept apart from human review: bots answer in minutes and would hide slow pickup"))
        S("Review", rs)
        m["cards"].append(("Merged with no human review", pct(len(none_), len(merged)), f"{len(none_)} of {len(merged)} PRs", rs[0]["g"]))

    # Shape & risk: size explains slow PRs; never a target on its own.
    sizes = [size(p) for p in merged]
    g, s, v = stat(sizes, "size", fmt=lambda x: f"{x:.0f} lines", verb="changed at most")
    card(m, "PR size, lines", sizes, g, v, lambda x: f"{x:.0f}")
    bk = {}
    for p, c in zip(merged, cyc): bk.setdefault(bucket(size(p)), []).append(c)
    lo = dict(zip((b for _, b, _ in BUCKETS), (0,) + tuple(lim for lim, _, _ in BUCKETS)))
    by_size = " · ".join(f"{name} ({f'<{lim:g}' if lim < math.inf else f'{lo[b]:g}+'}): {plural(len(bk[b]), 'PR')}, "
                         f"{dur(statistics.median(bk[b]))}" for lim, b, name in BUCKETS if b in bk)
    xl_fast = sorted((p for p, c in zip(merged, cyc) if size(p) >= 1000 and c < 1), key=size, reverse=True)
    cis = [ci_state(p) for p in merged]
    red_ci = [p for p, c in zip(merged, cis) if c in ("FAILURE", "ERROR")]
    reverts = [p for p in merged if REVERT_RE.search(p["title"] + "\n" + (p["body"] or ""))]
    rr = len(reverts) / len(merged) if merged else 0
    m["scatter"] = [(size(p), c, p) for p, c in zip(merged, cyc)]
    shape = [row(g, "PR size", s, "no merged PRs", "lines added + deleted; explains slow PRs, never a target",
                 f"75% at most {LIMIT['size'][0]} lines"),
             row("na", "Time to merge by PR size", by_size or None, "", "median time to merge in each size group")]
    if xl_fast:
        shape.append(row("a", "1k+ lines merged in under 1h", ", ".join(f"#{p['number']} ({size(p)})" for p in xl_fast[:6]), "",
                         "too big to have been read that fast"))
    ci_g = grade(len(red_ci) / len(merged), *LIMIT["red_ci"]) if any(cis) else "na"
    shape += [row(ci_g, "Merged on red CI", f"{len(red_ci)} of {len(merged)}" + (f": {nums(red_ci[:6])}" if red_ci else "")
                  if any(cis) else None, "no CI checks", "a failing check on the PR's last commit", "none"),
              row(grade(rr, *LIMIT["reverts"]) if len(merged) >= 20 else "na", "Reverts", f"{len(reverts)} of {len(merged)}"
                  + (f": {nums(reverts[:6])}" if reverts else "") if merged else None, "no merged PRs",
                  "PRs that undo an earlier change", f"{LIMIT['reverts'][0]:.0%} or less"),
              row("na", "Closed without merge", str(closed) if closed else None, "none", f"closed unmerged in the last {win} days")]
    if dep or promos:
        shape.append(row("na", "Left out of the stats above",
                         f"{plural(len(promos), 'promotion PR')} ({meta['dev'] or PROMO_HEADS[0]} → {meta['default']}), "
                         f"{plural(len(dep), 'dependency-bot PR')}", "", "releases and bot updates would skew every number"))
    S("Shape & risk", shape)
    if any(cis):
        m["cards"].append(("Merged on red CI", f"{len(red_ci)}", f"of {len(merged)} PRs", ci_g))

    # Contribution workflow: /pr and /pr-classify only see changes that go through a PR.
    hist = [w for d, w in meta["history"] if ts(d) >= start]
    cov = sum(hist) / len(hist) if hist else None
    sampled = f" (latest 100 of {meta['history_total']})" if meta["history_total"] > 100 else ""
    with_body = [p for p in merged if "## Merge Danger" in (p["body"] or "") and DOOR_RE.search(p["body"] or "")]
    oneway = [p for p in with_body if DOOR_RE.search(p["body"]).group(1).lower() == "one"]
    verdicts = {p["number"]: verdict(p) for p in merged if verdict(p)}
    oneway_gap = [p for p in oneway if not human_reviews(p) and verdicts.get(p["number"]) != "safe"]
    cg, ca = LIMIT["coverage"]
    wf = [row("na" if cov is None else "g" if cov >= cg else "a" if cov >= ca else "r", "Changes that went through a PR",
              f"{pct(sum(hist), len(hist))} · {len(hist) - sum(hist)} of {len(hist)} commits on {meta['default']} were pushed directly{sampled}"
              if hist else None, "no commits in window", "PR coverage: a direct push skips review, /pr and /pr-classify",
              f"{cg:.0%} or more"),
          row("na", "/pr template use", f"{len(with_body)} of {len(merged)} merged PRs" if with_body else None,
              "no PR uses the /pr template", "merged PRs whose body follows the /pr template"),
          row("r" if oneway_gap else "na", "One-way doors", f"{len(oneway)} of {len(with_body)} one-way; merged with no review or safe verdict: "
              + (nums(oneway_gap) or "none") if with_body else None, "no /pr bodies",
              "changes the /pr body marks hard to undo", "each one reviewed or classified safe")]
    if verdicts:
        mix = Counter(verdicts.values())
        over = [p for p in merged if verdicts.get(p["number"]) == "reject"
                or (verdicts.get(p["number"]) == "review" and not human_reviews(p))]
        wf.append(row("r" if over else "g", "/pr-classify verdicts", f"{len(verdicts)} of {len(merged)} classified · "
                      + " ".join(f"{k} {mix[k]}" for k in ("safe", "review", "reject") if mix[k])
                      + (f" · merged against verdict: {nums(over)}" if over else ""), "",
                      "automatic triage: safe / review / reject", "nothing merged against its verdict"))
    else:
        wf.append(row("na", "/pr-classify verdicts", None, "none recorded as a `pr-classify` commit status"))
    if meta["dev"]:
        old = hours(ts(meta["promo_oldest"]), NOW) if meta.get("promo_oldest") else None
        wf.append(row("a" if old and old > 24 * 7 else "na", f"Promotion lag ({meta['dev']} → {meta['default']})",
                      f"{meta['promo_ahead']} commits waiting, oldest {dur(old)}" if meta["promo_ahead"] else "nothing waiting", "",
                      f"commits on {meta['dev']} not yet released to {meta['default']}", "oldest under 1 week"))
    else:
        wf.append(row("na", "Promotion lag", None, "no dev branch"))
    S("Contribution workflow", wf)
    if cov is not None:
        m["cards"].append(("Went through a PR", pct(sum(hist), len(hist)), f"{len(hist) - sum(hist)} direct pushes", wf[0]["g"]))

    m["snapshot"] = {"repo": m["repo"], "at": iso(NOW), "mode": "solo" if solo else "team", "window_days": win,
                     "merged": len(merged), "open": len(rows), "open_red": len(red),
                     "cycle_median_h": statistics.median(cyc) if cyc else None,
                     "cycle_p75_h": statistics.quantiles(cyc, n=4)[2] if len(cyc) >= 20 else None,
                     "pickup_p75_h": statistics.quantiles(pick, n=4)[2] if len(pick) >= 20 else None,
                     "size_p75": statistics.quantiles(sizes, n=4)[2] if len(sizes) >= 20 else None,
                     "unreviewed": (sum(1 for p in merged if not human_reviews(p)) / len(merged)) if merged else None,
                     "pr_coverage": cov, "classified": len(verdicts)}
    return m


# ---------- render: markdown ----------
def cell(s, n=None):
    s = s.replace("|", "/").replace("\n", " ")
    return s if not n or len(s) <= n else s[: n - 1] + "…"


def who_md(r):
    return {"author": "author", "merger": "merge", "nobody": "no reviewer"}.get(r["kind"]) or ",".join(r["who"])


def render_md(m, show_all):
    mode = f"solo ({m['solo_who']})" if m["solo"] else "team"
    smp = f" (newest {m['sampled'][0]} of {m['sampled'][1]})" if m["sampled"] else ""
    o = [f"## PR health — {m['repo']} · {mode} · last {m['win']}d · {m['n']} merged{smp} · {NOW:%Y-%m-%d}",
         "🟢 ok  🟡 watch  🔴 act  ⚪ not graded (under 20 PRs, or no benchmark)"]
    if m["solo"]:
        o.append(f"> Solo: {m['solo_n'][0]}/{m['solo_n'][1]} PRs by one author, 0 human reviews → pickup and review rows "
                 "hidden (every PR is a merge button, not a queue).")
    rows = m["rows"]
    fossils = [r for r in rows if r["idle"] > 30]
    live = rows if show_all else [r for r in rows if r["idle"] <= 30]
    hidden = [f"{m['drafts']} draft"] * bool(m["drafts"]) + [f"{m['dep_open']} dependency-bot"] * bool(m["dep_open"])
    total = len(rows) + m["not_fetched"]
    scope = f" · {len(rows)} most recently active fetched" if m["not_fetched"] else ""
    o += ["", f"### Now — {total} open" + (f" ({', '.join(hidden)} not counted)" if hidden else "") + scope
          + f" · 🔴 {sum(r['g'] == 'r' for r in rows)} idle >5 business days · 🟡 {sum(r['g'] == 'a' for r in rows)} idle >1"]
    if m["not_fetched"]:
        tail = m["unfetched_idle"]
        o.append(f"{'🔴' if tail > 5 else '🟡'} the other {m['not_fetched']} (not fetched, cap {OPEN_CAP}) are each idle ≥{tail:.0f} business days")
    if fossils and not show_all:
        o.append(f"🔴 {len(fossils)} idle >30 business days (close or adopt?): {nums(sorted((r['p'] for r in fossils), key=lambda p: p['number'])[:15])}"
                 + (" …" if len(fossils) > 15 else ""))
    if not rows:
        o.append("Queue empty.")
    elif live:
        shown = live if show_all else live[:MD_ROWS]
        o += ["| | # | title | waiting/idle | waiting on | blocker | lines |", "|-|--:|---|--:|---|---|--:|"]
        o += [f"|{ICON[r['g']]}|{r['p']['number']}|{cell(r['p']['title'], 32)}|{dur(r['age'])}/{r['idle']:.0f}bd|"
              f"{cell(who_md(r), 18)}|{r['blocker']}|{size(r['p'])}|" for r in shown]
        if len(live) > len(shown):
            o.append(f"… +{len(live) - len(shown)} more — `--all` or `--html` for the full queue")
    if m["queue"] and not m["solo"]:
        o.append("Reviewer queue: " + " · ".join(f"{k} {c} (oldest {dur(a)})" for k, c, a in m["queue"][:6])
                 + (f" · +{len(m['queue']) - 6} more" if len(m["queue"]) > 6 else ""))
    na = []
    for title, rs in m["sections"]:
        shown = [r for r in rs if r["value"] is not None]
        na += [f"{r['label']} ({r['na']})" for r in rs if r["value"] is None]
        if shown:
            o += ["", f"### {title}", "| | metric | value |", "|-|---|---|"]
            o += [f"| {ICON[r['g']]} | {r['label']} | {cell(r['value'])} |" for r in shown]
    if na:
        o += ["", "⚪ Not measurable here: " + " · ".join(na)]
    return "\n".join(o)


# ---------- render: html ----------
def link(text, repo):
    return re.sub(r"#(\d+)", rf'<a href="https://github.com/{repo}/pull/\1">#\1</a>', html.escape(text))


def scatter(pts):
    """Size vs time to merge, log-log. The shaded corner is big PRs merged fast: the ones nobody read."""
    pts = [(max(s, 1), max(h, 1 / 60), p) for s, h, p in pts if h is not None]
    if len(pts) < 10: return ""
    W, H, L, R, T, B = 680, 300, 72, 16, 12, 44
    xmax = max(3, math.ceil(math.log10(max(s for s, _, _ in pts))))
    ymin, ymax = math.log10(1 / 60), max(math.log10(24 * 7), math.log10(max(h for _, h, _ in pts)))
    X = lambda s: L + 10 + (W - R - L - 10) * math.log10(s) / xmax
    Y = lambda h: T + (H - B - T) * (1 - (math.log10(h) - ymin) / (ymax - ymin))
    zx, zy = X(1000), Y(1)
    o = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="PR size versus time to merge">']
    if W - R - zx > 60:
        o.append(f'<rect x="{zx:.0f}" y="{zy:.0f}" width="{W - R - zx:.0f}" height="{H - B - zy:.0f}" class="danger"/>'
                 f'<text x="{W - R - 6}" y="{H - B - 6}" class="zone" text-anchor="end">big + fast: unread?</text>')
    for s, lab in ((1, "1"), (10, "10"), (100, "100"), (1000, "1k"), (10000, "10k"), (100000, "100k")):
        if math.log10(s) <= xmax:
            o.append(f'<line x1="{X(s):.0f}" x2="{X(s):.0f}" y1="{T}" y2="{H - B}" class="grid"/>'
                     f'<text x="{X(s):.0f}" y="{H - B + 14}" class="tick" text-anchor="middle">{lab}</text>')
    for h, lab in ((1 / 60, "1 min"), (1, "1 hour"), (24, "1 day"), (168, "1 week"), (720, "30 days")):
        if math.log10(h) <= ymax:
            o.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(h):.0f}" y2="{Y(h):.0f}" class="grid"/>'
                     f'<text x="{L - 6}" y="{Y(h) + 4:.0f}" class="tick" text-anchor="end">{lab}</text>')
    xy = [(X(s), Y(h)) for s, h, _ in pts]
    # Label a dot with its PR number only where the label hits no other dot or label; hover still names every dot.
    boxes = [(x - 5, y - 5, x + 5, y + 5) for x, y in xy]
    for i, ((s, h, p), (cx, cy)) in enumerate(zip(pts, xy)):
        o.append(f'<a href="{html.escape(p["url"])}"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" class="dot">'
                 f'<title>#{p["number"]} {html.escape(p["title"])} — {s} lines, merged in {dur(h)}</title></circle>')
        right, w = cx < W - R - 40, 6 * len(str(p["number"])) + 8
        box = (cx + 6, cy - 6, cx + 6 + w, cy + 6) if right else (cx - 6 - w, cy - 6, cx - 6, cy + 6)
        if not any(j != i and box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for j, b in enumerate(boxes)):
            boxes.append(box)
            o.append(f'<text x="{cx + (7 if right else -7):.1f}" y="{cy + 4:.1f}" class="lbl" '
                     f'text-anchor="{"start" if right else "end"}">#{p["number"]}</text>')
        o.append("</a>")
    o.append(f'<text x="{(L + W - R) / 2:.0f}" y="{H - 6}" class="axis" text-anchor="middle">lines changed →</text>'
             f'<text transform="translate(14 {(T + H - B) / 2:.0f}) rotate(-90)" class="axis" text-anchor="middle">time to merge →</text></svg>')
    return "".join(o)


def waiting_text(r):
    who = ", ".join(r["who"])
    return {"author": f"waiting on {who} (author)", "merger": "approved, waiting to be merged",
            "nobody": "no reviewer assigned"}.get(r["kind"], f"waiting on {who}")


def takeaways(m):
    """The 'so what' for a reader with no agent beside them: open-queue red, then red rows, then amber; at most 3."""
    out, red = [], sorted((r for r in m["rows"] if r["g"] == "r"), key=lambda r: -r["idle"])
    if len(red) > 2:
        out.append(("r", f"{len(red)} open PRs idle over 5 business days; the longest, #{red[0]['p']['number']}, "
                         f"for {red[0]['idle']:.0f} business days."))
    for r in red if len(red) <= 2 else []:
        b = {"conflict": "merge conflict"}.get(r["blocker"], r["blocker"])
        out.append(("r", f"#{r['p']['number']} idle {r['idle']:.0f} business days"
                         + (f", {b}" if b not in ("", "clean") else "") + f", {waiting_text(r)}."))
    for want in ("r", "a"):
        out += [(want, f"{x['label']}: {x['value'].replace('**', '')}." + (f" Good: {x['good']}." if x["good"] else ""))
                for _, rs in m["sections"] for x in rs if x["g"] == want and x["value"]]
    return out[:3] or [("g", "Nothing needs action.")]


def render_html(m):
    E, repo = html.escape, m["repo"]
    take = takeaways(m)
    worst = next((g for g in ("r", "a") if any(t[0] == g for t in take)), "g")
    take_html = (f'<div class="take {worst}"><b>Takeaways</b><ul>'
                 + "".join(f'<li class="{g}">{link(t, repo)}</li>' for g, t in take) + "</ul></div>")
    cards = "".join(f'<div class="card {g}"><div class="lbl">{E(l)}</div><div class="val">{E(v)}</div><div class="sub">{E(s)}</div></div>'
                    for l, v, s, g in m["cards"])
    groups = [("nobody", "No reviewer — needs an owner"), ("reviewer", "Waiting on reviewer"),
              ("author", "Waiting on author"), ("merger", "Approved — waiting on merge")]
    q = []
    for kind, title in groups:
        rs = sorted((r for r in m["rows"] if r["kind"] == kind), key=lambda r: -r["idle"])
        if not rs: continue
        red = sum(r["g"] == "r" for r in rs)
        body = "".join(
            f'<tr class="{r["g"]}"><td><a href="{E(r["p"]["url"])}">#{r["p"]["number"]}</a></td>'
            f'<td class="t" title="{E(r["p"]["title"])}">{E(r["p"]["title"])}</td><td class="n">{dur(r["age"])}</td>'
            f'<td class="n idle">{r["idle"]:.1f}</td><td>{E(", ".join(r["who"]) or "—")}</td>'
            f'<td>{f"<span class=chip>{E(r["blocker"])}</span>" if r["blocker"] not in ("", "clean") else ""}</td>'
            f'<td class="n"><b class="sz">{bucket(size(r["p"]))}</b> {size(r["p"])}</td></tr>' for r in rs)
        q.append(f'<details{" open" if red or len(rs) <= 10 else ""}><summary><b>{title}</b> · {len(rs)}'
                 + (f' · <span class="r-t">{red} idle &gt;5 business days</span>' if red else "")
                 + '</summary><table class="open"><thead><tr><th>#</th><th>title</th><th>open for</th><th>idle (business days)</th>'
                 f'<th>waiting on</th><th>blocker</th><th>lines</th></tr></thead><tbody>{body}</tbody></table></details>')
    sec = [f'<section><h2>Now — open queue</h2>{"".join(q) or "<p class=muted>No open PRs ready for review.</p>"}</section>']
    if m["queue"] and not m["solo"]:
        sec.append("<section><h2>Reviewer queue</h2><table class='kv'>" + "".join(
            f"<tr><th>{E(k)}</th><td>{c} pending</td><td class='muted'>oldest {dur(a)}</td></tr>" for k, c, a in m["queue"]) + "</table></section>")
    na = []
    for title, rs in m["sections"]:
        na += [f"<b>{E(r['label'])}</b> ({E(r['na'])})" for r in rs if r["value"] is None]
        body = "".join(f'<tr><th><span class="dot-{r["g"]}"></span>{E(r["label"])}{about(r)}</th>'
                       f'<td>{link(r["value"].replace("**", ""), repo)}</td></tr>' for r in rs if r["value"] is not None)
        chart = scatter(m["scatter"]) if title == "Shape & risk" else ""
        extra = (f"<h3>PR size vs time to merge</h3>{chart}<p class='cap'>Each dot is one merged PR: hover for its title, click to "
                 "open it. Further right = bigger, higher = slower to merge. Shaded corner: 1k+ lines merged in under an hour, "
                 "probably not really reviewed.</p>") if chart else ""
        if body: sec.append(f"<section><h2>{E(title)}</h2><table class='kv'>{body}</table>{extra}</section>")
    banner = (f'<div class="banner">Solo repo: {m["solo_n"][0]}/{m["solo_n"][1]} PRs by <b>{E(m["solo_who"])}</b>, 0 human reviews. '
              "Pickup and review rows are hidden: every PR is a merge button, not a queue.</div>") if m["solo"] else ""
    tpl = open(os.path.join(HERE, "report.html")).read()
    meta = (f"{'Solo' if m['solo'] else 'Team'} repo · {plural(m['n'], 'PR')} merged in the last {m['win']} days · "
            f"{NOW:%Y-%m-%d %H:%M} UTC<br><span class='dot-g'></span>ok <span class='dot-a'></span>watch "
            "<span class='dot-r'></span>act <span class='dot-na'></span>not graded: too few PRs (needs 20) or no benchmark")
    rep = {"TITLE": E(repo), "META": meta, "TAKEAWAYS": take_html, "BANNER": banner, "CARDS": cards,
           "SECTIONS": "".join(sec), "NA": f'<p class="na-line">Not measurable here: {" · ".join(na)}</p>' if na else ""}
    return re.sub(r"\{\{(\w+)\}\}", lambda x: rep[x.group(1)], tpl)


def about(r):
    """The grey line under a metric label: what it measures and what good looks like."""
    t = " · ".join(x for x in (r["about"], r["good"] and f"good: {r['good']}") if x)
    return f'<div class="about">{html.escape(t)}</div>' if t else ""


# ---------- main ----------
def parse_repo(arg):
    if not arg:
        out = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], capture_output=True, text=True)
        if out.returncode: sys.exit("Not in a GitHub repo; pass OWNER/REPO. " + out.stderr.strip())
        arg = out.stdout.strip()
    m = re.search(r"(?:github\.com[/:])?([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", arg.strip())
    if not m: sys.exit(f"Can't read a repo from {arg!r}; pass OWNER/REPO.")
    return m.group(1), m.group(2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--html", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    owner, name = parse_repo(a.repo)
    repo = f"{owner}/{name}"
    win, counts = pick_window(repo)
    since = NOW - timedelta(days=win)
    with ThreadPoolExecutor(3) as ex:
        f_merged = ex.submit(search_prs, f"repo:{repo} is:pr is:merged merged:>={since:%Y-%m-%d} {NOT_DEPS} sort:created-desc", MERGED_CAP)
        f_open = ex.submit(search_prs, f"repo:{repo} is:pr is:open draft:false {NOT_DEPS} sort:updated-desc", OPEN_CAP)
        f_meta = ex.submit(fetch_meta, owner, name, since)
        (merged, _), (open_prs, open_total), meta = f_merged.result(), f_open.result(), f_meta.result()
    m = compute(owner, name, win, counts, merged, open_prs, open_total, meta)
    print(render_md(m, a.all))
    if a.json:
        with open(a.json, "w") as f: json.dump(m["snapshot"], f, indent=1)
    if a.html:
        path = os.path.join(os.path.expanduser("~/.cache/pr-report"), f"{owner}__{name}.html")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f: f.write(render_html(m))
        webbrowser.open("file://" + path)
        print(f"\nHTML: {path}")


if __name__ == "__main__":
    main()
