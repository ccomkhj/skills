---
name: pair-consult
description: "Second opinion from the other agent CLI before the user decides: you propose, a headless Codex or Claude reviewer critiques it cold over a bounded number of rounds, you synthesize and ask the user. Use for one question, proposal, or small change that deserves an independent review; not for multi-step implementation."
argument-hint: "[what the reviewer should judge, or a new question] [--number n] [--effort high|xhigh]"
---

# pair-consult

You are **A**, the live orchestrator. **B** is the other CLI, run headless for one round at a time. B never sees this chat. It knows only the repo and `.consult/`, and that independence is the point: a reviewer briefed with your conclusions returns them confirmed.

> Woken headless as the reviewer? Your whole brief is [reference/peer.md](reference/peer.md). Nothing below is for you.

## What the user typed

The text after `/pair-consult` is the **ask**: what the user wants settled. Copy it verbatim into `QUESTION.md`; it becomes B's mandate.

| Situation | R1 is | The ask tells B |
|---|---|---|
| You already proposed something in this conversation | that proposal, packaged for a cold reader | what to judge about it (`anything to remove before implementing?`) |
| No proposal yet | your answer to the ask (coding task: write the code, run the tests) | the question it must also answer |
| No text | your latest proposal | is it right, and what should be cut? |
| `.consult/STATE.md` exists | — | resume: see [Resume](#resume) |

Flags map to `consult_init`: `--number n` is the round cap, `--effort` is B's reasoning effort.

## Rounds

| Round | Actor | Kind | Writes |
|---|---|---|---|
| 1 | A | propose | `R1.md` |
| even | B | review: numbered critiques `C1…` | `R<n>.md` |
| odd, interior | A | respond: a verdict per critique | `R<n>.md` |
| cap − 1, when cap ≥ 5 | B | re-review: accept or double down, B's last word | `R<n>.md` |
| cap | A | synthesize, ask the user | `R<cap>.md` |

## Steps

State changes go through the helpers in `reference/handoff.sh`. **Source it, don't read it**: each helper checks its preconditions and prints what to do next.

```bash
source <skill-dir>/reference/handoff.sh
```

The files you write follow [reference/file-formats.md](reference/file-formats.md).

1. **Init.** `consult_init <you> <peer> [n] [effort]`, then `QUESTION.md` and `R1.md`. B starts cold and pays for every search, so fill every slot of the templates: cited lines let B verify instead of hunt, and evidence grades aim B at your weak claims. Copy scratch scripts into `.consult/`. Done when someone who never saw this chat could act on those two files alone.

2. **Hand off.** `consult_handoff`, then the wait it prints. The reviewer is detached, so that backgrounded wait is the only thing that wakes you: tell the user B is reviewing, and end your turn.

3. **Relay, then respond.** Put the digest `consult_wait` prints in chat, so the user follows the consult as a conversation. Check [early termination](#early-termination); otherwise respond to every critique. Verify B's claims the way B verified yours, and re-run the tests if you changed code. Answer any unaddressed note in `USER_NOTES.md` and mark it addressed. Back to step 2.

4. **Synthesize.** Write `R<cap>.md`, even on an early exit (name the skipped rounds), run `consult_close`, and present it. The user's go/no-go ends the consult.

Any user message mid-loop is a steer: act on it before continuing. If it invalidates the round B is working on, `consult_takeover`, fix what B will read, then `consult_resume`.

### Early termination

The cap is a maximum. Synthesize early when B's review has zero critiques, or when your response is all `agree` with no new code, claims, or reasoning. Otherwise run B's next round: regressions hide in what you just changed.

## Resume

`consult_status`, then by `STATUS`:

- `WAITING: <you>` → do round `ROUND`.
- `WAITING: <peer>` → reviewer running: `consult_wait`. Not running: `consult_handoff`.
- `AWAITING_USER` → show `R<cap>.md` and ask for the decision.
- `BLOCKED` → say what is blocked; `consult_resume` reruns B's round.

For the user in a second terminal: `consult_watch` tails the reviewer live, `consult_inject "<note>"` leaves a steer in `USER_NOTES.md`.
