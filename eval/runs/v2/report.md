# FinQA evaluation report

Split: test; model: deepseek/deepseek-v4.1-flash
Cases: 20; backend: local

| Method | Correct | Mean evidence recall | Median seconds | <=30s | Reported cost USD |
|---|---:|---:|---:|---:|---:|
| keyword | N/A (retrieval only) | 68.8% | 0.001 | 20/20 | 0.000000 |
| full | 17/20 (85%) | 100.0% | 3.956 | 20/20 | 0.018767 |
| rag | 16/20 (80%) | 90.0% | 4.146 | 20/20 | 0.015483 |

## Interpretation limits

- These are project numerical scores using the frozen policy, not official FinQA leaderboard scores.
- All cases stay in the accuracy denominator, including errors and abstentions.
- Gold-ID retrieval coverage is not semantic citation correctness. Manual citation/unit/formula review is pending unless explicitly completed.
- Latency is measured after embedding setup; indexing, downloads and UI startup are excluded.
- API costs are provider-reported. Local compute costs are excluded; missing costs remain missing in metrics.json.
- Small-sample descriptive results do not establish general superiority. See Wilson intervals in metrics.json.
- Empty-evidence guards are tested separately and do not demonstrate nuanced model abstention.

## Incorrect / unsuccessful model cases

- full · JPM/2018/page_90.pdf-3: answer; predicted=2229188 (number), reference=89167520.0; 
- full · PNC/2014/page_111.pdf-1: answer; predicted=0.044 (number), reference=0.0; 
- full · SNA/2012/page_110.pdf-3: answer; predicted=34551.09 (number), reference=658.13; 
- rag · JPM/2018/page_90.pdf-3: answer; predicted=2229188 (number), reference=89167520.0; 
- rag · PNC/2014/page_111.pdf-1: answer; predicted=0.044 (number), reference=0.0; 
- rag · SNA/2012/page_110.pdf-3: answer; predicted=34551.09 (number), reference=658.13; 
- rag · MRO/2006/page_93.pdf-1: abstain; predicted=None (None), reference=0.62329; The evidence does not provide the total amount of the liability for asset retirement obligations for 2003 or 2005, so the percentage increase cannot be calculated.
