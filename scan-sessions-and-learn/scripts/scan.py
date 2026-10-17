#!/usr/bin/env python3
"""Digest recent interactive Claude Code sessions for workflow and friction mining.

Prints a compact, redacted text digest to stdout and never writes a file:
a summary (selection, skills, recurring flows and phrases, friction) and one
block per session. Headless (`claude -p`/SDK) runs, scratchpad sessions,
sessions only reopened in the window, this session and earlier runs of this
skill are left out. `--grep`/`--errors` instead print the typed prompts, tool
results and Claude replies that match, redacted.

    scan.py [--days 7 | --sessions N] [--repo NAME|current]
            [--part all|summary|sessions] [--offset K] [--limit M]
            [--grep REGEX] [--errors] [--ids S12,1a2b3c4d]
"""
import argparse, collections, datetime as dt, functools, json, math, os, re, shlex, sqlite3, subprocess
from pathlib import Path

HOME = str(Path.home())
ROOT = Path(HOME) / ".claude" / "projects"
OWN = str(Path(__file__).resolve().parents[2])  # the skills repo this script lives in
SELF = "scan-sessions-and-learn"
TMP = re.compile(r"^(/private)?/(tmp|var/folders)/")
BUILTIN = {"clear", "compact", "model", "effort", "config", "exit", "resume", "login", "logout", "mcp", "status",
           "cost", "context", "permissions", "plugin", "rename", "help", "fast", "usage", "stats", "theme", "ide",
           "hooks", "memory", "doctor", "vim", "add-dir", "agents", "export", "release-notes", "init", "review",
           "rewind", "copy", "feedback", "upgrade", "terminal-setup", "output-style", "statusline", "todos", "tasks"}

# --- redaction: vendor prefixes, credentials in URLs/headers/assignments, then high-entropy leftovers

SECRET = re.compile(r"""(?xs)
  -----BEGIN[A-Z ]*PRIVATE\ KEY-----.*?(?:-----END[A-Z ]*PRIVATE\ KEY-----|\Z)
| \b[a-z][\w+.-]*://[^\s:/@'"]+:[^\s@/'"]+@
| (?i:[\w-]*(?:authorization|x-api-key|api[_-]?key|access[_-]?key|secret|token|passw(?:or)?d|pwd|credentials?|dsn)[\w-]*["']?\s*[:=]\s*["']?(?:bearer\s+|basic\s+)?)(?!\$|<|\{|None|null|true|false|os\.|env)[^\s"',;)]{6,}
| (?i:\bbearer\s+)[\w.~+/=-]{16,}
| \b(?:sk-(?:ant-|proj-)?|[rsp]k_(?:live|test)_)[A-Za-z0-9_-]{20,}
| (?i:--password|--passwd)(?:=|\s+)["']?(?!\$|<|\{)[^\s"']{4,}
| \b(?:gh[pousr]_\w{20,}|github_pat_\w{20,}|AKIA[0-9A-Z]{16}|AIza[\w-]{35}|xox[a-z]-[\w-]{10,}|xapp-[\w-]{10,}|glpat-[\w-]{20,})
| \beyJ[\w-]{10,}\.[\w-]{10,}(?:\.[\w-]+)?
""")
LONG_TOKEN = re.compile(r"(?<![\w/+=-])[A-Za-z0-9+/=_-]{32,}(?![\w/+=-])")


def _looks_random(s):
    if re.search(r"[a-z]{3,}/[a-z_.-]{3,}", s):  # a path, not a key
        return False
    counts = collections.Counter(s)
    entropy = -sum(v / len(s) * math.log2(v / len(s)) for v in counts.values())
    kinds = [sum(f(c) for c in s) for f in (str.isdigit, str.isupper, str.islower)]
    return min(kinds) >= 2 and entropy >= 4.0


def redact(text):
    text = SECRET.sub("[REDACTED]", text)
    return LONG_TOKEN.sub(lambda m: "[REDACTED]" if _looks_random(m[0]) else m[0], text)


def clip(text, n=300):
    text = re.sub(r"\s+", " ", redact(text)).strip()
    return text if len(text) <= n else text[:n] + "…"


# --- grouping worktrees under the repo they belong to

@functools.lru_cache(None)
def _superset_projects():
    found = {}
    for db in Path(HOME).glob(".superset/host/*/host.db"):
        try:
            with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as con:
                found.update(con.execute("select id, repo_path from projects"))
        except sqlite3.Error:
            pass
    return found


@functools.lru_cache(None)
def _git_root(d):
    try:
        out = subprocess.run(["git", "-C", d, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return str(Path(out).parent) if out.endswith("/.git") else None


WORKTREE = re.compile(r"^(?P<base>.*?)/(?P<kind>\.superset/worktrees|\.claude/worktrees|\.?worktrees)/(?P<name>[^/]+)")


@functools.lru_cache(None)
def repo_key(cwd, pr_repo=None):
    norm = lambda p: os.path.basename(p.rstrip("/")).lower().replace("_", "-") or "/"
    if not cwd or TMP.match(cwd):
        return "<tmp>"
    if os.path.isdir(cwd) and (root := _git_root(cwd)) and root != HOME:
        return norm(root)
    if m := WORKTREE.match(cwd):
        if m["kind"] == ".claude/worktrees":
            return norm(m["base"])
        if re.fullmatch(r"[0-9a-f-]{36}", m["name"]):
            path = _superset_projects().get(m["name"]) or pr_repo
            return norm(path) if path else f"<superset:{m['name'][:8]}>"
        return norm(m["name"])
    if pr_repo:
        return norm(pr_repo)
    return "~" if cwd.rstrip("/") == HOME else norm(cwd)


@functools.lru_cache(None)
def skill_home(name, roots=()):
    """own = lives in this skills repo (improve-skills can edit it); repo = in a project's .claude/skills, fixed
    in that repo; plugin/user/other cannot be edited from here."""
    if ":" in name:
        return "plugin"
    for base in (Path(HOME) / ".claude" / "skills", Path(HOME) / ".agents" / "skills"):
        if (base / name).exists():
            return "own" if str((base / name).resolve()).startswith(OWN + os.sep) else "user"
    if any((Path(r) / ".claude" / "skills" / name).exists() for r in roots):
        return "repo"
    return "other"


# --- action signatures: one short token per tool call, no arguments

WRAPPERS = {"env", "sudo", "time", "timeout", "nohup", "command", "exec", "do", "then", "else", "{",
            "if", "elif", "while", "until"}  # a loop's or branch's condition is a command too
SKIP_HEADS = {"cd", "export", "set", "setopt", "source", ".", ":", "true", "echo", "printf", "mkdir", "sleep", "date",
              "for", "fi", "done", "esac", "case", "local", "unset", "trap", "exit", "return", "break", "continue",
              "wait", "read", "shift", "}"}
SUBCOMMAND = {"git", "gh", "npm", "pnpm", "yarn", "bun", "uv", "poetry", "kubectl", "docker", "make", "terraform",
              "aws", "superset", "claude", "codex", "brew", "helm", "gcloud", "dbt", "airflow"}
RUNNERS = {"uv": "run", "poetry": "run", "conda": "run", "pnpm": "exec", "npx": None, "bunx": None}
VALUE_FLAGS = {"-C", "-c", "-n", "--name", "-p", "--prefix", "--with", "--from", "--project", "--directory", "-R", "--repo"}


HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n.*?\n\s*\2[ \t]*(?=\n|$)", re.S)
QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")


def _words(seg):
    try:
        return shlex.split(seg, comments=True)
    except ValueError:
        return seg.split()


def bash_sig(cmd):
    # multi-line commands: heredoc bodies, continuations and quoted SQL/Python are not commands of their own
    cmd = re.sub(r"\\\n", " ", HEREDOC.sub(r"\3", cmd))
    cmd = QUOTED.sub(lambda m: re.sub(r"[;|&\n]", " ", m[0]), cmd)
    for seg in re.split(r"&&|\|\||[;|&\n]", cmd):
        toks = _words(seg)
        if toks and re.match(r"^[A-Za-z_]\w*=\$\(", toks[0]):  # PY=$(conda run … which python) is setup
            continue
        while toks and (re.match(r"^[A-Za-z_]\w*=", toks[0]) or toks[0] in WRAPPERS or
                        re.fullmatch(r"\d+[smh]?|[\w-]+\(\)\{?", toks[0])):  # also drops a function's "q() {"
            toks.pop(0)
        if not toks or toks[0] in SKIP_HEADS or toks[0][0] in "#({$<>[-\\" or re.search(r"[()]", toks[0]):
            continue
        head, args = toks[0].rsplit("/", 1)[-1], toks[1:]
        # drop flags and their values (git -C <dir>, conda run -n <env>) so the subcommand survives
        rest = [a for i, a in enumerate(args) if not a.startswith("-") and not (i and args[i - 1] in VALUE_FLAGS)]
        if head in RUNNERS and rest and (RUNNERS[head] is None or rest[0] == RUNNERS[head]):
            rest = rest if RUNNERS[head] is None else rest[1:]
            if rest:
                head, rest = rest[0].rsplit("/", 1)[-1], rest[1:]
        if head.startswith("python"):
            return "Bash:python -m " + args[args.index("-m") + 1] if "-m" in args[:-1] else "Bash:python"
        if head == "gh" and len(rest) >= 2:
            return f"Bash:gh {rest[0]} {rest[1]}"
        return f"Bash:{head[:24]}" + (f" {rest[0][:20]}" if head in SUBCOMMAND and rest else "")
    return "Bash:?"


def tool_sig(block):
    name, inp = block.get("name") or "?", block.get("input") or {}
    if name == "Bash":
        return bash_sig(inp.get("command") or "")
    if name.startswith("mcp__"):
        parts = name.split("__")
        server = re.sub(r"^(plugin_[^_]+_|claude_ai_)", "", parts[1]).lower()
        return f"mcp:{server}.{parts[-1]}"
    if name == "Skill":
        return f"Skill:{inp.get('skill', '?')}"
    if name in ("Agent", "Task"):
        return f"Agent:{inp.get('subagent_type') or 'general-purpose'}"
    if name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        ext = Path(inp.get("file_path") or inp.get("notebook_path") or "").suffix.lstrip(".")
        return f"Edit:{ext or '?'}"
    return name


# Exploration steps say little about the workflow; landmarks are what is left.
NOISE = re.compile(r"^(Read|Grep|Glob|LS|ToolSearch|TodoWrite|Task(Create|Update|List|Get|Output)|"
                   r"Bash:(grep|rg|sed|cat|ls|head|tail|wc|find|awk|jq|tree|stat|file|which|pwd|diff|python|"
                   r"mv|cp|ln|rm|chmod|touch|\?)|"
                   r"Bash:git (status|diff|log|show|branch|rev-parse|remote))$")


def landmarks(seq):
    kept = [s for s in seq if not NOISE.match(s)]
    return [s for i, s in enumerate(kept) if i == 0 or s != kept[i - 1]]


# --- one session

class Session:
    def __init__(self, path):
        self.id, self.path = path.stem, path
        self.cwd = self.branch = self.title = self.pr_repo = None
        self.prs, self.entry = set(), collections.Counter()
        self.start = self.end = None
        self.agent_ms, self.assistant_lines = 0, 0
        self.prompts = []  # (marker, text, shingle_text)
        self.seq, self.skills = [], []
        self.errors, self.denials = collections.Counter(), collections.Counter()
        self.interrupts = self.rewinds = self.compacts = 0
        self.ran_self = False

    @property
    def day(self):  # last activity: the window selects on it, and long sessions span weeks
        return self.end.date().isoformat() if self.end else "?"

    @property
    def repo(self):
        return repo_key(self.cwd or "", self.pr_repo)


COMMAND = re.compile(r"<command-name>/?([^<\s]+)</command-name>")
ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)
PASTE = re.compile(r"<pasted_content[^>]*>.*?(?:</pasted_content[^>]*>|\Z)|\[Pasted text[^\]]*\]|\[Image #\d+\]", re.S)
INJECTED = ("<", "Caveat:", "[Request interrupted", "Another Claude session", "This session is being continued",
            "Stop hook feedback", "Base directory for this skill", "Help me fix these Claude Code settings issues")


def _when(e):
    try:
        return dt.datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
    except (KeyError, ValueError, AttributeError):
        return None


def parse(path):
    s = Session(path)
    sig_of, first_prompt_under = {}, {}
    after_interrupt = False
    for raw in path.open(errors="replace"):
        try:
            e = json.loads(raw)
        except ValueError:
            continue
        kind = e.get("type")
        if e.get("isSidechain"):
            continue
        if e.get("entrypoint"):
            s.entry[e["entrypoint"]] += 1
        if kind == "ai-title" and not s.title:
            s.title = e.get("aiTitle")
        elif kind == "custom-title":
            s.title = e.get("customTitle") or s.title
        elif kind == "pr-link":
            s.prs.add(e.get("prNumber"))
            s.pr_repo = s.pr_repo or e.get("prRepository")
        elif kind == "system":
            if e.get("subtype") == "turn_duration":
                s.agent_ms += e.get("durationMs") or 0
            elif e.get("subtype") == "compact_boundary":
                s.compacts += 1
        if kind not in ("user", "assistant"):
            continue
        if (t := _when(e)):
            s.start, s.end = min(s.start or t, t), max(s.end or t, t)
        s.cwd = s.cwd or e.get("cwd")
        s.branch = e.get("gitBranch") or s.branch
        content = (e.get("message") or {}).get("content")

        if kind == "assistant":
            s.assistant_lines += 1
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    sig = sig_of[b.get("id")] = tool_sig(b)
                    s.seq.append(sig)
                    if sig.startswith("Skill:"):
                        s.skills.append(sig[6:])
                        s.ran_self |= sig.endswith(SELF)
            continue

        if isinstance(content, list):
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and b.get("text", "").startswith("[Request interrupted"):
                    s.interrupts += 1
                    after_interrupt = True
                elif b.get("type") == "tool_result":
                    sig = sig_of.get(b.get("tool_use_id"), "?")
                    if e.get("toolDenialKind"):
                        s.denials[e["toolDenialKind"]] += 1
                        if e.get("userFeedback"):
                            s.prompts.append(("✗", f"rejected {sig}: {clip(e['userFeedback'], 200)}", e["userFeedback"]))
                    elif b.get("is_error"):
                        s.errors[sig] += 1
            continue
        if not isinstance(content, str) or e.get("isMeta") or e.get("isCompactSummary"):
            continue
        source, origin = e.get("promptSource"), (e.get("origin") or {}).get("kind")
        if source in ("system", "sdk") or (origin and origin != "human"):
            continue

        if content.startswith("[Request interrupted"):
            s.interrupts += 1
            after_interrupt = True
            continue
        if (m := COMMAND.search(content)) or re.match(r"/[\w:-]+(\s|$)", content):
            if m:
                name, found = m[1], ARGS.search(content)
                args = found[1] if found else ""
            else:  # a typed "/compact keep the plan" arrives as plain text
                name, _, args = content[1:].partition(" ")
            args = PASTE.sub("[paste]", args).strip()
            short = name.split(":")[-1]
            s.ran_self |= short == SELF
            if short in BUILTIN:
                continue
            s.skills.append(name)
            s.seq.append("/" + name)
            text = f"/{name} {clip(args)}".strip()
        else:
            body = PASTE.sub("[paste]", content).strip()
            if not body or body.startswith(INJECTED):
                continue
            text, args = clip(body), body

        marker = "»" if source == "suggestion_accepted" else "⏹" if after_interrupt else ""
        parent = e.get("parentUuid")
        if parent in first_prompt_under:  # same parent as an earlier prompt: the user rewound and rewrote it
            s.rewinds += 1
            marker = f"↺{first_prompt_under[parent]}"
        else:
            first_prompt_under[parent] = len(s.prompts) + 1
        after_interrupt = False
        s.prompts.append((marker, text, "" if marker == "»" else args))
    return s


# --- selection

def select(args, current_id):
    skipped, kept = collections.Counter(), []
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)
    files = sorted(ROOT.glob("*/*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    oldest = min((f.stat().st_mtime for f in files), default=None)
    want_repo = repo_key(os.getcwd()) if args.repo == "current" else args.repo
    for f in files:
        if not args.sessions and dt.datetime.fromtimestamp(f.stat().st_mtime, dt.timezone.utc) < since:
            break
        if f.stem == current_id:
            skipped["this session"] += 1
            continue
        s = parse(f)
        reason = ("headless run" if s.entry["sdk-cli"] > s.entry["cli"] else
                  "scratchpad/tmp" if TMP.match(s.cwd or "/tmp/") else
                  "no typed prompt" if not s.prompts or not s.assistant_lines else
                  # reopening an old session appends metadata and bumps mtime without new work
                  "reopened, inactive in window" if not args.sessions and s.end and s.end < since else
                  "ran this skill" if s.ran_self else
                  "other repo" if want_repo and s.repo != want_repo.lower().replace("_", "-") else None)
        if reason:
            skipped[reason] += 1
            continue
        kept.append(s)
        if args.sessions and len(kept) >= args.sessions:
            break
    kept.sort(key=lambda s: s.end or dt.datetime.min.replace(tzinfo=dt.timezone.utc))
    merge_skill_names(kept)
    return kept, skipped, oldest, want_repo


@functools.lru_cache(None)
def installed_plugin_skills():
    """bare name -> {plugin:name} for every installed plugin's skills and commands."""
    found = collections.defaultdict(set)
    try:
        plugins = json.loads(Path(HOME, ".claude", "plugins", "installed_plugins.json").read_text())["plugins"]
    except (OSError, ValueError, KeyError):
        return found
    for key, installs in plugins.items():
        plugin = key.split("@")[0]
        for inst in installs:
            root = Path(inst.get("installPath") or "/nonexistent")
            # cache/<marketplace>/<plugin>/<version>: older versions hold skills used before an update dropped them
            versions = root.parent.glob("*") if root.parent.name == plugin else [root]
            for v in versions:
                for f in [*v.glob("**/skills/**/SKILL.md"), *v.glob("commands/*.md")]:
                    name = f.parent.name if f.name == "SKILL.md" else f.stem
                    found[name].add(f"{plugin}:{name}")
    return found


def merge_skill_names(sessions):
    """The agent often calls a plugin skill by its bare name (tdd for mattpocock-skills:tdd); count them as one."""
    full = collections.defaultdict(set)
    for s in sessions:
        for name in s.skills:
            if ":" in name:
                full[name.split(":")[-1]].add(name)
    for s in sessions:  # a narrow window may never show the namespaced form; fall back to what is installed
        for name in s.skills:
            if ":" not in name and name not in full:
                full[name] = installed_plugin_skills().get(name, set())
    alias = {short: min(names) for short, names in full.items() if len(names) == 1 and skill_home(short) == "other"}
    for s in sessions:
        s.skills = [alias.get(n, n) for n in s.skills]
        s.seq = [re.sub(r"^(Skill:|/)([\w-]+)$", lambda m: m[1] + alias.get(m[2], m[2]), x) for x in s.seq]


def last_handoff(sessions, label):
    """Earlier runs leave findings that may still be pending; a re-run should build on them, not re-derive them."""
    prev = max(Path(OWN, ".inspect").glob("sessions*handoff.md"), key=lambda f: f.stat().st_mtime, default=None)
    if not prev:
        return "Last handoff: none."
    at = dt.datetime.fromtimestamp(prev.stat().st_mtime, dt.timezone.utc)
    newer = [label[s.id] for s in sessions if s.end and s.end > at]  # sessions sort by last activity: the tail
    return (f"Last handoff: {str(prev).replace(HOME, '~')} ({at.astimezone():%Y-%m-%d %H:%M}); "
            f"{len(newer)} kept sessions active since" +
            (f" ({support_list(newer)}); --offset {len(sessions) - len(newer)} reads only those." if newer else "."))


# --- output

STOP = set("a an the to of in on for and or is are be it this that with as at by from i you we me my our your "
           "can could should would do does did not no yes if so but then there here what how why when which "
           "please just also all any some let lets let's s t n".split())


def shingles(text, k=3):
    text = re.sub(r"https?://\S+|\S*/\S+|\[paste\]|\[REDACTED\]|\b[A-Z]{2,}-\d+\b", " ", text)
    words = re.findall(r"[a-z\uac00-\ud7a3']+|\d+", text.lower())
    words = ["n" if w.isdigit() else w for w in words]
    found = {" ".join(g) for g in (words[i:i + k] for i in range(len(words) - k + 1))
             if sum(len(w) >= 3 and w not in STOP for w in g) >= 2}
    if 0 < len(words) <= 5:  # short whole prompts ("what's next?", "go") recur as a habit, not a phrase
        found.add(" ".join(words))
    return found


def support_list(labels, cap=8):
    labels = sorted(labels, key=lambda x: int(x[1:]))
    return ",".join(labels[:cap]) + (f",+{len(labels) - cap}" if len(labels) > cap else "")


def contains(longer, shorter):
    n = len(shorter)
    return any(longer[i:i + n] == shorter for i in range(len(longer) - n + 1))


# tokens. Above READ_ALONE, subagents read ~BATCH each: their fixed overhead dwarfs a small batch, and a
# bigger one lets them see what recurs. Below it, read ~PAGE at a time: a larger tool output is saved to a
# file instead of shown, which costs a second read.
READ_ALONE, BATCH, PAGE = 25_000, 10_000, 7_000


def batch_plan(sizes, target):
    """[offset, limit] slices of about target tokens each."""
    plan, start, acc = [], 0, 0
    for i, n in enumerate(sizes):
        acc += n
        if acc >= target:
            plan.append([start, i + 1 - start])
            start, acc = i + 1, 0
    if start < len(sizes):
        if plan and acc < target / 2:  # fold a small tail into the last slice
            plan[-1][1] += len(sizes) - start
        else:
            plan.append([start, len(sizes) - start])
    return plan


def summary(sessions, skipped, oldest, args, want_repo, block_sizes):
    label = {s.id: f"S{i}" for i, s in enumerate(sessions, 1)}
    out = []
    window = f"newest {args.sessions} sessions" if args.sessions else f"last {args.days:g} days"
    out.append(f"# Session digest — {window}" + (f", repo {want_repo}" if want_repo else ", all repos"))
    if oldest:
        first = dt.datetime.fromtimestamp(oldest).date()
        out.append(f"Transcripts on disk reach back to {first} (Claude Code prunes after cleanupPeriodDays, default 30).")
    if sessions:
        out.append(f"Kept {len(sessions)} sessions, {sessions[0].day} → {sessions[-1].day}. "
                   f"Skipped: {', '.join(f'{k} {v}' for k, v in skipped.most_common()) or 'none'}.")
    else:
        out.append("No sessions matched.")
        return out
    total = sum(block_sizes)
    if total <= READ_ALONE:
        out.append(f"Session blocks: ~{total} tokens; read them yourself, --part sessions with the same window "
                   f"flags, one page per call: " +
                   " · ".join(f"--offset {o} --limit {n}" for o, n in batch_plan(block_sizes, PAGE)))
    else:
        plan = batch_plan(block_sizes, BATCH)
        out.append(f"Session blocks: ~{total} tokens, too many for one context. One subagent per batch, each "
                   f"--part sessions with the same window flags: " +
                   " · ".join(f"--offset {o} --limit {n}" for o, n in plan))
    out.append(last_handoff(sessions, label))
    repos = collections.Counter(s.repo for s in sessions)
    out.append("Repos: " + ", ".join(f"{r} {n}" for r, n in repos.most_common()))

    out.append("\n## Skills and commands (sessions using it · home: own = editable in this skills repo)")
    used, roots = collections.defaultdict(set), collections.defaultdict(set)
    for s in sessions:
        for name in s.skills:
            used[name].add(label[s.id])
            roots[name].add(_git_root(s.cwd) if s.cwd and os.path.isdir(s.cwd) else None)
    for name, where in sorted(used.items(), key=lambda kv: -len(kv[1]))[:25]:
        out.append(f"- {name} · {len(where)} · {skill_home(name, tuple(sorted(filter(None, roots[name]))))}")

    def recurring(seqs, nmin, nmax, floor):
        grams = collections.defaultdict(set)
        for sid, seq in seqs:
            for n in range(nmin, nmax + 1):
                for i in range(len(seq) - n + 1):
                    grams[tuple(seq[i:i + n])].add(sid)
        good = sorted((g for g, w in grams.items() if len(w) >= floor), key=lambda g: (-len(grams[g]), -len(g)))
        chosen = []
        for g in good:  # skip a sub-sequence of an already chosen, equally supported sequence
            if not any(grams[c] == grams[g] and contains(c, g) for c in chosen):
                chosen.append(g)
        return [(g, grams[g]) for g in chosen[:12]]

    out.append("\n## Recurring skill chains (≥2 sessions)")
    chains = [(label[s.id], [k for i, k in enumerate(s.skills) if i == 0 or k != s.skills[i - 1]]) for s in sessions]
    out += [f"- {' > '.join(g)} · {len(w)} sessions ({support_list(w)})" for g, w in recurring(chains, 2, 4, 2)] or ["- none"]

    out.append("\n## Recurring flows (landmark tool sequences, ≥3 sessions)")
    flows = [(label[s.id], landmarks(s.seq)) for s in sessions]
    out += [f"- {' > '.join(g)} · {len(w)} sessions ({support_list(w)})" for g, w in recurring(flows, 2, 4, 3)] or ["- none"]

    out.append("\n## Recurring phrases in typed prompts (≥3 sessions on ≥2 days)")
    where, days = collections.defaultdict(set), collections.defaultdict(set)
    for s in sessions:
        for _, _, raw in s.prompts:
            for sh in shingles(raw):
                where[sh].add(label[s.id])
                days[sh].add(s.day)
    phrases = sorted((p for p in where if len(where[p]) >= 3 and len(days[p]) >= 2), key=lambda p: -len(where[p]))
    shown = []
    for p in phrases:
        if not any(where[q] == where[p] and set(p.split()) & set(q.split()) for q in shown):
            shown.append(p)
    out += [f"- \"{p}\" · {len(where[p])} sessions ({support_list(where[p])})" for p in shown[:15]] or ["- none"]

    out.append("\n## Friction (sessions affected)")
    def hit(pred):
        w = [label[s.id] for s in sessions if pred(s)]
        return f"{len(w)} ({support_list(w)})" if w else "0"
    out.append(f"- rewound and rewrote a prompt (↺): {hit(lambda s: s.rewinds)}")
    out.append(f"- interrupted the agent (⏹): {hit(lambda s: s.interrupts)}")
    for kind in sorted({k for s in sessions for k in s.denials}):
        out.append(f"- tool call denied, {kind}: {hit(lambda s, k=kind: s.denials[k])}")
    out.append(f"- context compacted: {hit(lambda s: s.compacts)}")
    repeated = collections.defaultdict(set)
    for s in sessions:
        for sig, n in s.errors.items():
            if n >= 2 and not NOISE.match(sig):  # a failed cat or grep is exploration, mostly a compound command
                repeated[sig].add(label[s.id])
    for sig, w in sorted(repeated.items(), key=lambda kv: -len(kv[1]))[:8]:
        out.append(f"- same tool failed ≥2× in a session, {sig}: {len(w)} ({support_list(w)})")
    return out


def session_block(i, s):
    mins = lambda ms: f"{ms / 60000:.0f}m"
    span = (s.end - s.start).total_seconds() * 1000 if s.start and s.end else 0
    head = (f"## S{i} {s.day} {s.repo}" + (f" @{s.branch}" if s.branch and s.branch != "HEAD" else "") +
            f" · agent {mins(s.agent_ms)} / span {mins(span)} · {len(s.prompts)} prompts" +
            (f" · PR {'/'.join(str(p) for p in sorted(s.prs, key=str))}" if s.prs else "") + f" · id {s.id[:8]}")
    out = [head]
    if s.title:
        out.append(f"title: {clip(s.title, 100)}")
    flow = landmarks(s.seq)
    if len(flow) > 30:
        flow = flow[:20] + [f"…{len(flow) - 28}…"] + flow[-8:]
    out.append("flow: " + (" > ".join(flow) or "-"))
    friction = [f"{n} {what}" for n, what in ((s.rewinds, "rewrites ↺"), (s.interrupts, "interrupts ⏹"),
                                             (sum(s.denials.values()), "denied"), (s.compacts, "compactions")) if n]
    friction += [f"{sig} failed ×{n}" for sig, n in s.errors.most_common() if n >= 2 and not NOISE.match(sig)]
    if friction:
        out.append("friction: " + " · ".join(friction))
    keep = range(len(s.prompts))
    if len(s.prompts) > 25:  # long sessions: keep marked prompts plus the opening and the ending
        keep = sorted({j for j, p in enumerate(s.prompts) if p[0]} | set(range(12)) | set(range(len(s.prompts) - 8, len(s.prompts))))
    seen, last = set(), -1
    for j in keep:
        marker, text, _ = s.prompts[j]
        if text[:80].lower() in seen:
            continue
        seen.add(text[:80].lower())
        if j > last + 1:
            out.append(f"  … {j - last - 1} prompts omitted")
        out.append(f"  [{j + 1}]{marker} {text}")
        last = j
    return out


def grep(sessions, pattern, wanted, errors_only=False, cap=10):
    """Drill-down: the user's own prompts, then the error, denied call or Claude reply behind a marker, redacted.
    errors_only keeps failed and denied tool results, so bulk text that matches can't use up the cap."""
    pat = re.compile(pattern, re.I)
    for i, s in enumerate(sessions, 1):
        if wanted and f"S{i}" not in wanted and not any(s.id.startswith(w) for w in wanted):
            continue
        sig_of, hits = {}, 0
        for j, (marker, text, _) in enumerate(s.prompts if not errors_only else [], 1):
            if pat.search(text):
                hits += 1
                if hits <= cap:
                    print(f"S{i} {s.id[:8]} {s.day} {s.repo} you [{j}]{marker}: {text}")
        for raw in s.path.open(errors="replace"):
            try:
                e = json.loads(raw)
            except ValueError:
                continue
            content = (e.get("message") or {}).get("content")
            if e.get("type") not in ("user", "assistant") or e.get("isSidechain") or not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    sig_of[b.get("id")] = tool_sig(b)
                    continue
                if b.get("type") == "text" and e["type"] == "assistant" and not errors_only:
                    where, text = "claude", b.get("text") or ""
                elif b.get("type") == "tool_result" and (not errors_only or e.get("toolDenialKind") or b.get("is_error")):
                    where = sig_of.get(b.get("tool_use_id"), "?") + (
                        " denied" if e.get("toolDenialKind") else " ✗" if b.get("is_error") else "")
                    text = b.get("content") or ""
                    if isinstance(text, list):
                        text = " ".join(x.get("text") or "" for x in text if isinstance(x, dict))
                else:
                    continue
                if not (m := pat.search(text)):
                    continue
                hits += 1
                if hits <= cap:
                    print(f"S{i} {s.id[:8]} {where}: {clip(text[max(0, m.start() - 150):m.end() + 150], 400)}")
        if hits > cap:
            print(f"S{i} {s.id[:8]} … {hits - cap} more hits")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--days", type=float, default=7, help="sessions active in the last N days (default 7)")
    p.add_argument("--sessions", type=int, help="newest N kept sessions instead of a day window")
    p.add_argument("--repo", help="only this repo key, or 'current' for the cwd's repo")
    p.add_argument("--part", choices=("all", "summary", "sessions"), default="all")
    p.add_argument("--offset", type=int, default=0, help="first session block to print (0-based)")
    p.add_argument("--limit", type=int, help="number of session blocks to print")
    p.add_argument("--grep", help="regex: print matching typed prompts, tool results and Claude replies, redacted")
    p.add_argument("--errors", action="store_true", help="only failed or denied tool results (with or without --grep)")
    p.add_argument("--ids", help="with --grep/--errors: session labels (S12) or id prefixes, comma-separated")
    a = p.parse_args()

    sessions, skipped, oldest, want_repo = select(a, os.environ.get("CLAUDE_CODE_SESSION_ID"))
    if a.grep or a.errors:
        grep(sessions, a.grep or ".", {w.strip() for w in (a.ids or "").split(",") if w.strip()}, a.errors)
        return
    blocks = [session_block(i, s) for i, s in enumerate(sessions, 1)]
    head = summary(sessions, skipped, oldest, a, want_repo, [len("\n".join(b)) // 4 for b in blocks])
    if a.part in ("all", "summary"):
        print("\n".join(head))
    if a.part in ("all", "sessions"):
        end = None if a.limit is None else a.offset + a.limit
        for b in blocks[a.offset:end]:
            print("\n" + "\n".join(b))


if __name__ == "__main__":
    main()
