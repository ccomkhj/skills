---
type: regex
target: {source: file, path: .productbridge/PB-001/experiment.json}
match: not_contains
---
"status"\s*:\s*"approved"
