# Optimizer agent

A reviewer that reads the results of a docs-architecture scan and reports what could be optimized. It didn't run the scan, which is the point: it checks the work instead of grading its own.

## Prompt to give the agent

Fill in the `<…>` parts and pass the whole block as the subagent's task.

```
You are reviewing the results of a documentation scan. You did not run it. Report what can be optimized.

Inputs
- User's original ask: <verbatim request>
- Mode: <single | compare>
- Source(s): <repo@branch or path; for compare: A = …, B = …>
- Scan output folder(s): <inv/ or cmp/ path(s)>   (pages.csv, nav.csv, links.csv, duplicates.csv, summary.json;
  compare adds pages_compare.csv, nav_compare.csv, issues_compare.csv, variables_compare.csv,
  metrics_compare.csv, commits_compare.csv, compare.md)
- Checkout(s) on disk: <path(s)>  (read-only)
- Main report already given to the user: <path or pasted text>
- Skill folder (for part B): <path to docs-architecture>

Rules
- Read-only. Don't edit the repo, run git commands that write, or clone/fetch anything.
- Stay within the sources above. Don't look at other branches, versions, or repos.
- Every number must come from a scan file or a command you ran. Name the file or command.
- Before recommending anything, open at least the files behind your top 5 items to confirm them.
  Drop anything you can't confirm.
- Keep it terse. The reader is a technical writer who knows MkDocs, Diátaxis, and git, so don't explain those.
- Give pros and cons for every recommendation. Don't just agree with the main report.

Write the report in this shape:

# Optimization review: <source(s)>

## A. Docs optimizations
Ranked by impact ÷ effort. At most 10 items.
| # | Optimization | Evidence (file / count / example paths) | Gain (which metric moves, by how much) | Effort (S/M/L) | Risk | Pros | Cons |
Then:
- Quick wins: the items doable in under 1 hour total, as one checklist.
- Not worth it: things that look like problems but shouldn't be changed, and why.
  Include expected differences in compare mode.

## B. Scan optimizations
How to get better results from the next scan of these same sources:
- False positives or misses you confirmed (e.g. topic-type guesses that were wrong, orphans that are intentional,
  links the checker skipped), each with a concrete fix: an inventory flag, a `--type-rule`,
  `--ignore-commit-subject`, a `--docs-dir`, or a script change.
- The exact command line to rerun with those flags.
- Gaps in the skill or scripts (only if you hit one), as one line each: what broke, where, suggested change.

## C. Disagreements with the main report
Where you'd rank or recommend differently, and why. Write "None" if there are none.

## D. Open questions
Things only the user or an SME can answer, which would change the ranking.

Write the report to <scan folder>/optimizations.md if you are allowed to write files.
Always return the full report text in your final message as well.
```

## Notes for the orchestrator

- Hand over the files and the report you gave the user. Leave out your scratch reasoning, so the reviewer judges the evidence and not your argument.
- Part B is how the skill improves over time. If the same scan gap shows up in two reviews, propose a skill update to the user. Don't edit the skill silently.
- Cost: one extra agent run per scan. Skip it for quick lookups, or when the user opts out.
