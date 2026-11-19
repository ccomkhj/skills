# Inline Standards review

One GitHub review, event `COMMENT`, with a comment on the diff line of each Standards finding. The author reads and answers a finding next to the code; the verdict stays in the summary comment.

`gh pr review` is blocked (it can approve), so post through the API:

```bash
gh api repos/<owner>/<repo>/pulls/<N>/reviews --input <run dir>/review.json
```

```json
{
  "commit_id": "<pinned head SHA>",
  "event": "COMMENT",
  "body": "pr-review · Standards findings on `<sha7>`. The verdict and full report are in the pr-review comment on this PR.",
  "comments": [
    {
      "path": "src/server/library.ts",
      "line": 42,
      "side": "RIGHT",
      "body": "**<hard violation | judgement call>: <short title>**\n\n<the finding in the reviewer's words, with the rule it cites>"
    }
  ]
}
```

- `commit_id` is the pinned head, so the comments stay on the code that was judged even if the branch moved.
- Every `line` must be inside a hunk of `git diff <base>...<head>`: a head-side line with `side: RIGHT`, or, when the finding is about removed code (a deleted export something still imports), the deleted line with `side: LEFT` and its line number in the base file. Add `start_line` for a range. GitHub rejects the whole review (422) if one line is outside the diff, so check each line before posting. A finding with no such line (missing test, a file the PR doesn't touch) stays in the summary comment only.
- Never `APPROVE` or `REQUEST_CHANGES`: report only.
- No Standards finding on a diff line → no review.
