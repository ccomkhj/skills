# Verdict as a commit status

The one place the verdict → status mapping lives. Written by `/pr-classify` and `/pr-review`; read by `/pr-report`, which counts classified PRs and merges that went against the verdict.

```bash
gh api repos/{owner}/{repo}/statuses/<sha> -f context=pr-classify -f state=<state> -f description="<class>"
```

| Class (`description`, verbatim) | `state` |
|---|---|
| safe to merge | `success` |
| nice to review | `pending`: a human still has to look |
| reject to merge | `failure` |

Record it on the SHA that was judged, never on whatever the head is now. A status notifies no one, and a later push leaves it on the old commit, so it never vouches for code the reviewer didn't see. Skip if the commit isn't on GitHub yet.
