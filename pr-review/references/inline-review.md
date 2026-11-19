# Inline issues

One GitHub review, event `COMMENT`, with a comment on the diff line of each issue (a candidate that survived [verification](../../pr-classify/references/verdict.md)). The author reads and answers an issue next to the code; the verdict stays in the summary comment.

`gh pr review` is blocked (it can approve), so post through the API:

```bash
gh api repos/<owner>/<repo>/pulls/<N>/reviews --input <run dir>/review.json
```

```json
{
  "commit_id": "<pinned head SHA>",
  "event": "COMMENT",
  "body": "pr-review · issues on `<sha7>`, each with its evidence. The verdict is in the pr-review comment on this PR.",
  "comments": [
    {
      "path": "src/server/library.ts",
      "line": 42,
      "side": "RIGHT",
      "body": "**<risk> risk: <short title>**\n\n<what is wrong> → <what it does to this service>\n\n**Evidence:** <reproduction, contradiction or trace>"
    }
  ]
}
```

- `commit_id` is the pinned head, so the comments stay on the code that was judged even if the branch moved.
- Every `line` must be inside a hunk of `git diff <base>...<head>`: a head-side line with `side: RIGHT`, or, when the issue is about removed code (a deleted export something still imports), the deleted line with `side: LEFT` and its line number in the base file. Add `start_line` for a range. GitHub rejects the whole review (422) if one line is outside the diff, so check each line before posting. An issue with no such line stays in the summary comment only.
- Never `APPROVE` or `REQUEST_CHANGES`: report only.
- No issue on a diff line → no review.
