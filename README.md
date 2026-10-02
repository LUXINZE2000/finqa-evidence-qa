# FinQA Evidence QA

A PE6201 prototype that answers numerical questions about **FinQA financial-report excerpts**, showing cited evidence and Python-checked arithmetic. The default retrieval backend is local MiniLM + NumPy; no database or Docker is needed. It does **not** ingest whole annual-report PDFs. Start with the [product overview](docs/product_overview.md), [data explainer](data/README.md), and [evaluation records](eval/README.md).

## Run from a fresh checkout (Windows PowerShell)

Use Python 3.12 and run these commands in the repository root. Internet access is needed for package installation and the first MiniLM download; the selected data are already checked in.

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit prints a local URL (usually `http://localhost:8501`). Open it, choose a development excerpt, and enter a question. **Keyword evidence only** works without an API key and displays retrieved source chunks, not a generated numerical answer. The UI intentionally does not show test questions. To use **RAG** or **Full context**, copy `.env.example` to `.env` and fill in your own OpenRouter key and model ID:

```powershell
Copy-Item .env.example .env
```

Set `OPENROUTER_API_KEY` and `OPENROUTER_MODEL=deepseek/deepseek-v4.1-flash` in `.env` to reproduce the recorded model choice, provided that model remains available to your account. Never commit `.env`. The first RAG call downloads and caches `sentence-transformers/all-MiniLM-L6-v2`; full context does not require embeddings. Each generated answer uses one paid API call, with no automatic retry. The returned answer includes its number/unit, citation IDs, calculation steps, source text, elapsed time, and reported API cost; it can also abstain or show an invalid-output error.

## Reproduce checks and create new evaluation runs

```powershell
# No API key: evaluate BM25 evidence retrieval on the 10 development questions
.\.venv\Scripts\python.exe -m scripts.run_evaluation --split dev --modes keyword
# Optional paid smoke test: two development questions with each answer method
.\.venv\Scripts\python.exe -m scripts.run_evaluation --split dev --modes full rag --limit 2
# Optional paid full 20-question test, after reviewing cost and settings
.\.venv\Scripts\python.exe -m scripts.run_evaluation --split test --modes keyword full rag
```

The script prints the path of a new timestamped `results/` directory. It saves `run.json` (settings and hashes), mode-specific JSONL and CSV, and `summary.json`. For expanded metrics and one combined per-case CSV, run `python -m scripts.summarize_run results/<run-id>` with the virtualenv Python. New ad hoc outputs are Git-ignored. The original v1 and v2 test records are already included in [`eval/runs/`](eval/runs/), so **you do not need to rerun paid calls to inspect the submitted results**. The original `exe_ans` labels and result files are unchanged. See [scoring rules](eval/scoring_rules.md) before interpreting accuracy or citations.

`python -m scripts.prepare_data` optionally re-downloads the pinned FinQA dev/test JSON and regenerates the selected data and manifest; a fresh checkout does not need this. `python -m scripts.build_index --split dev` optionally warms the local embedding cache before a RAG run. The default local backend is enough for this corpus; optional OpenSearch setup is documented in [`requirements-opensearch.txt`](requirements-opensearch.txt) and [`compose.yaml`](compose.yaml), but is not required or validated as part of the submitted results.

## Results and boundaries

The project target is **14/20** numerically correct test answers. The first test gave full context **12/20** and RAG **8/20**. After evidence and output fixes, the **same 20 already-inspected cases** gave full context **17/20** and RAG **16/20**. This is an iterative comparison, not an independent holdout. The v2 RAG median latency was **4.15 s**, all **20/20** completed within 30 seconds, and the reported API cost for 20 RAG answers was **$0.015483**; local compute and indexing costs are excluded. Citation review has disputed cases and is reported separately. [The product overview](docs/product_overview.md) gives the full comparison and limitations.

## If something fails

- `ModuleNotFoundError`: use `.\.venv\Scripts\python.exe` from the repository root and install `requirements.txt` in that environment.
- Missing OpenRouter configuration: check the two `.env` fields, then restart Streamlit; keyword mode can still run without them.
- MiniLM download error: check network access and retry the RAG mode or optional `build_index`; full-context and keyword modes do not need the encoder.
- Missing selected data: verify `data/processed/documents.json` is present in the checkout; `python -m scripts.prepare_data` can regenerate it with network access.
- API failure or changed model availability: inspect `OPENROUTER_MODEL`, account access, and the displayed error. Failed calls count as incorrect in an evaluation run; the runner does not retry or silently exclude them.

Code entry points are `app.py` (demo), `src/pipeline.py` (question flow), `src/retrieval.py` (evidence), `src/model.py` (API), `src/calculator.py` (validation and arithmetic), and `src/evaluation.py` (scoring). The `scripts/` directory prepares data, warms indices, runs cases and summarizes results. Source and evaluation labels are intentionally separate. This implementation used AI assistance; the student should review the work and disclose assistance according to course instructions.
