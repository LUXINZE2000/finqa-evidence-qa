# Implementation status — v2

The primary backend is local MiniLM embeddings plus NumPy similarity, with BM25 as the
non-generative baseline. No search server is required. OpenSearch is an optional adapter
and was not integration-tested in this environment.

FinQA source chunks retain original IDs. RAG retrieves five core chunks and adds neighboring
text or same-table rows as separately citable context. A DeepSeek model proposes bounded
arithmetic, and Python checks quoted operands and executes it. The request uses structured
JSON, low reasoning effort, and 4096 output tokens; failures are not automatically retried.

Verified: 13 automated tests passed, including the Streamlit keyword path, cross-sentence
and cross-table context, signed numbers and percent parsing. Real DeepSeek calls completed on
10 development and the same 20 previously inspected test cases. The first test results are
kept; new results are an iterative comparison and not an independent holdout.

Known limits: quote presence does not prove the correct year or formula; some FinQA questions
or labels are inconsistent; only basic arithmetic is supported; no full-report PDF ingestion.
A preliminary review flags disputed cases. API usage cost excludes local compute.
