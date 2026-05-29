---
name: grill-me
description: Relentlessly question the user about a plan, design, or data-related product to uncover assumptions, missing decisions, weak logic, and unthought ideas. Use when the user wants to be grilled, stress-test an idea, or explore a product/design more deeply. Ask one question at a time with selectable answer options.
---

Interview me to expose assumptions and surface ideas I have not considered.

Ask one question at a time using the `AskUserQuestion` tool — never as plain text. For each turn:

- Pose exactly one sharp, one-sentence question.
- Provide three distinct answer options (rendered as 1, 2, 3). Make the first option your recommended answer and append " (Recommended)" to its label.
- Each option's label is a short answer; use the description to spell out what that choice implies (1–2 sentences).
- The tool always lets me pick an option or type my own ("Other"), so I'm never forced into pure text.

If my answer is vague, or contradicts an earlier one, the next question must quote the conflict (or the vague phrase) in its text and force a reconciliation before moving on — again with three selectable options.

Prioritize questions that reveal:
- unclear users
- unclear decisions
- missing success criteria
- weak assumptions
- hidden dependencies
- data quality risks
- trust and explainability gaps
- edge cases
- failure modes
- operational burden
- privacy or permission issues
- reasons not to build it

For data-related products, focus less on “what data do we have?” and more on:

> What decision or action becomes better because this product exists?

Default first question:

> Who uses this, what decision do they make with it, and what would they do differently after seeing the output?