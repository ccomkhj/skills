# Batch prompt (step 1)

Give each subagent one batch line from the digest, with the user's window flags, and this prompt. The subagent sees no summary and no other batch, so the prompt has to carry the marker meanings and the habit/friction line.

```text
Read one batch of a redacted digest of the user's recent Claude Code sessions, for a retrospective on recurring workflows and friction. Read only; edit nothing.

Run from ~/personal/skills:
  python3 -I scan-sessions-and-learn/scripts/scan.py <window flags> --part sessions --offset <K> --limit <M>

Each block is one session: label, last-active date, repo, branch, agent/span minutes, id prefix, the landmark tool flow, friction counts, and the user's typed prompts only. Markers: ↺N the user rewound and rewrote prompt N; ⏹ sent right after an interrupt; ✗ a rejected tool call with the user's reason; » an accepted suggestion (Claude's wording, not the user's).

A workflow recurs across ≥2 sessions in the batch. Friction is where the user corrected Claude, re-explained something, or lost turns to a detour or a failing tool. Group the same friction across sessions into one item listing every label. Short approvals ("go", "what's next") and routine requests are habits unless something went wrong around them. Say what you saw, not what you infer: the main agent checks each claim against the prompts before using it.

Return JSON only, at most ~1k tokens, paraphrased (no quoted prompts, client names, pasted data or query numbers):
{"workflows": [{"name": "", "trigger": "", "chain": "", "sessions": ["S12"]}],
 "friction": [{"what": "", "kind": "correction|re-explanation|detour|failure|habit", "sessions": ["S12"], "cost": ""}]}
```
