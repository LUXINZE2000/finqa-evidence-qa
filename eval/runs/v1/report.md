# FinQA evaluation report

Split: test; model: deepseek/deepseek-v4.1-flash
Cases: 20; backend: local

| Method | Correct | Mean evidence recall | Median seconds | <=30s | Reported cost USD |
|---|---:|---:|---:|---:|---:|
| keyword | N/A (retrieval only) | 68.8% | 0.000 | 20/20 | 0.000000 |
| full | 12/20 (60%) | 100.0% | 4.749 | 20/20 | 0.022575 |
| rag | 8/20 (40%) | 71.2% | 3.418 | 20/20 | 0.013403 |

## Interpretation limits

- These are project numerical scores using the frozen policy, not official FinQA leaderboard scores.
- All cases stay in the accuracy denominator, including errors and abstentions.
- Gold-ID retrieval coverage is not semantic citation correctness. Manual citation/unit/formula review is pending unless explicitly completed.
- Latency is measured after embedding setup; indexing, downloads and UI startup are excluded.
- API costs are provider-reported. Local compute costs are excluded; missing costs remain missing in metrics.json.
- Small-sample descriptive results do not establish general superiority. See Wilson intervals in metrics.json.
- Empty-evidence guards are tested separately and do not demonstrate nuanced model abstention.

## Incorrect / unsuccessful model cases

- full · MRK/2013/page_125.pdf-4: answer; predicted=44.58333333333333333333333333 (percent), reference=-0.44583; 
- full · TFX/2015/page_89.pdf-3: invalid_output; predicted=None (None), reference=7989.0; Operand value does not occur in its source quote
- full · JPM/2018/page_90.pdf-3: answer; predicted=2229188 (number), reference=89167520.0; 
- full · PNC/2014/page_111.pdf-1: invalid_output; predicted=None (None), reference=0.0; Unknown answer status
- full · CDW/2015/page_93.pdf-1: invalid_output; predicted=None (None), reference=19.66667; Unknown answer status
- full · C/2008/page_44.pdf-1: invalid_output; predicted=None (None), reference=-0.51419; Unknown answer status
- full · SNA/2012/page_110.pdf-3: answer; predicted=34551.09 (number), reference=658.13; 
- full · AWK/2017/page_148.pdf-1: answer; predicted=8.352941176470588235294117647 (percent), reference=-0.08353; 
- rag · MRK/2013/page_125.pdf-4: answer; predicted=44.58333333333333333333333333 (percent), reference=-0.44583; 
- rag · TFX/2015/page_89.pdf-3: abstain; predicted=None (None), reference=7989.0; Insufficient evidence: no 2014 restructuring charge amount is provided to exclude prior years.
- rag · UNP/2009/page_42.pdf-3: abstain; predicted=None (None), reference=0.21981; The evidence provides operating leases total of 5312 and capital lease obligations total of 2975, but does not provide the total material obligations and commitments as of December 31, 2009, so the percentage cannot be computed without inferring missing figures.
- rag · JPM/2018/page_90.pdf-3: answer; predicted=2229188 (number), reference=89167520.0; 
- rag · PNC/2014/page_111.pdf-1: invalid_output; predicted=None (None), reference=0.0; Unknown answer status
- rag · CMCSA/2015/page_112.pdf-4: abstain; predicted=None (None), reference=0.19286; The evidence provides the federal net operating loss carryforward amount ($135 million) as of December 31, 2015, but does not provide a foreign taxes or foreign net operating loss carryforward amount for 2015, so the ratio cannot be computed.
- rag · C/2009/page_63.pdf-1: abstain; predicted=None (None), reference=2.22222; Evidence does not specify that the $160 million discretionary contributions are for non-US pension plans.
- rag · C/2008/page_44.pdf-1: invalid_output; predicted=None (None), reference=-0.51419; Unknown answer status
- rag · SNA/2012/page_110.pdf-3: abstain; predicted=None (None), reference=658.13; The evidence does not provide the total fair value of non-vested performance awards at the beginning of the year; it only includes end-of-year shares and fair value per share, and unrecognized compensation cost.
- rag · FBHS/2017/page_22.pdf-1: abstain; predicted=None (None), reference=4.90575; The supplied evidence does not provide 2017 sales for the doors segment, so the ratio of cabinets sales to doors cannot be calculated.
- rag · MRO/2006/page_93.pdf-1: abstain; predicted=None (None), reference=0.62329; The supplied evidence does not include the total liability amounts for asset retirement obligations for 2003 or 2005, so the percentage increase cannot be calculated.
- rag · AWK/2017/page_148.pdf-1: answer; predicted=8.352941176470588235294117647 (percent), reference=-0.08353; 
