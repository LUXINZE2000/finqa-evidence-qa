# Frozen evaluation policy — v1

- 10 development questions from FinQA dev; 20 formal questions from public test.
- Fixed random seed 6201, sampled without looking at answers or system performance.
- Keep IDs unchanged. Use dev only for prompt/chunk changes; log changes after any formal run.
- Source scope: the corresponding FinQA excerpt, not an entire annual report or cross-report search.
- Main metric: all 20 questions in denominator. Abstentions, API errors and invalid outputs count incorrect.
- Use FinQA `exe_ans` as numerical reference. Decimal tolerance: max(0.0001 absolute,
  0.0001 × absolute reference). This is a project convention, not the official leaderboard metric.
- Percent predictions explicitly declare `kind=percent` and contain percentage points; divide by
  100 before comparison. Never try both x100 and /100 and accept whichever matches.
- Monetary numbers retain the units asked for; conversion must appear in the arithmetic steps.
  Unit labels and semantic equivalence require manual review. Numerical scoring alone does not prove units correct.
- No automatic acceptance of non-numerical answers. Report such cases without replacing them.
- Retrieval: gold evidence recall and whether all gold IDs appear in top three; full-context gets all sources.
- Citation/gold overlap is only a proxy. Manually fill CSV `manual_citation_supported` with yes/no
  and notes after reviewing data selection, formula, units and supporting citations.
- Report median end-to-end latency and fraction <=30 seconds separately from accuracy.
  The evaluator loads the encoder and prepares local embeddings before the question loop.
  Prebuild OpenSearch indices separately. Record warm/cold conditions; setup cost is separate.
- Log reported API costs; null means unavailable, never free. No automatic paid retries.
- Five empty-evidence controls verify the deterministic no-evidence guard only. They are NOT evidence
  that the model detects subtly insufficient context. Do not combine them with normal accuracy.
- Report normal abstention frequency and manually inspect each abstained case. Whether it *would*
  have answered incorrectly requires a separate counterfactual experiment; do not infer it from abstention.
- 70% = 14/20, a project target rather than a course pass mark. One case changes accuracy by 5 points.

## v2 iterative comparison (2026-09-28 onward)

- The original v1 20-case results are preserved. The same cases were reviewed during diagnosis,
  so v2 is an iterative comparison on a seen test set, not a new independent holdout.
- RAG uses five core hits plus separately identified adjacent text and same-table rows.
  Report core-only and expanded evidence coverage separately.
- Numerical scoring against exe_ans remains unchanged for direct comparability.
  Signed percentage change is required; verbal positive decrease magnitudes are displayed
  only as an explanation alongside the signed result.
- Suspected gold answer/program inconsistencies are recorded in a separate adjudication
  table with source evidence. Original exe_ans scores are never overwritten.
- Manual review must assess cited source, year, number, units and formula, not just an ID match.
