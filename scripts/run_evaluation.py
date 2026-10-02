"""Run frozen FinQA cases and save per-case predictions, metrics, and run metadata.

Reads sources for answering and evaluator-only labels for scoring; writes a new
timestamped results directory. Keyword mode makes no paid model calls.
"""
import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from src.data import ROOT, read_json, write_json, load_cases, load_document
from src.evaluation import annotate, summarize
from src.model import SYSTEM_PROMPT, MAX_TOKENS, REASONING_EFFORT
from src.pipeline import answer


def main():
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=["dev", "test"], default="dev")
    p.add_argument("--modes", nargs="+", choices=["keyword", "full", "rag"], default=["keyword"])
    p.add_argument("--backend", choices=["local", "opensearch"], default="local")
    p.add_argument("--limit", type=int)
    p.add_argument("--abstention", action="store_true", help="Five empty-evidence controls; not normal accuracy")
    args = p.parse_args()
    cases = load_cases(args.split)
    if args.limit:
        if args.split == "test":
            p.error("Formal test runs must use all 20 frozen cases")
        cases = cases[:args.limit]
    if args.abstention:
        cases = cases[:5]
        if "keyword" in args.modes:
            p.error("Abstention controls require full or rag mode")
    if not args.abstention and any(m != "keyword" for m in args.modes) and not (
            os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_MODEL")):
        p.error("Configure OPENROUTER_API_KEY and OPENROUTER_MODEL first")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "results" / run_id
    out.mkdir(parents=True)
    labels = read_json(ROOT / "data" / "labels" / f"{args.split}.json")
    if "rag" in args.modes and not args.abstention:
        from src.retrieval import encoder, embeddings
        encoder()  # Model startup is outside per-question latency.
        if args.backend == "local":
            for case in cases:
                embeddings(load_document(case["id"])["chunks"])
    source_hash = hashlib.sha256()
    for path in sorted((ROOT / "src").glob("*.py")):
        source_hash.update(path.name.encode() + path.read_bytes())
    write_json(out / "run.json", {"split": args.split, "modes": args.modes, "backend": args.backend,
        "abstention_control": args.abstention, "model": os.getenv("OPENROUTER_MODEL"),
        "experiment_version": "v2-iterative", "rag_core_k": 5,
        "max_tokens": MAX_TOKENS, "reasoning_effort": REASONING_EFFORT,
        "same_20_cases_previously_diagnosed": args.split == "test",
        "source_sha256": source_hash.hexdigest(), "prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        "cases": [c["id"] for c in cases], "data_manifest": read_json(ROOT / "eval" / "data_manifest.json")})
    summaries = {}
    for mode in args.modes:
        rows = []
        with (out / f"{mode}.jsonl").open("w", encoding="utf-8") as f:
            for case in cases:
                document = load_document(case["id"])
                if args.abstention:
                    # Guaranteed insufficient evidence, unlike merely deleting
                    # gold chunks whose numbers may be duplicated elsewhere.
                    document = dict(document, chunks=[])
                result = answer(case["question"], document, mode, args.backend)
                if args.abstention:
                    result["expected_status"] = "abstain"
                    result["control_passed"] = result["status"] == "abstain"
                else:
                    result = annotate(result, labels[case["id"]])
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
                f.flush()
                rows.append(result)
                print(mode, case["id"], result["status"])
        summary = summarize(rows)
        if args.abstention:
            summary["empty_evidence_control_pass_rate"] = sum(r["control_passed"] for r in rows) / len(rows)
        summaries[mode] = summary
        columns = ["case_id", "status", "value", "kind", "gold_answer", "correct", "evidence_recall",
                   "citation_gold_overlap", "latency_seconds", "cost_usd", "manual_citation_supported", "manual_notes"]
        with (out / f"{mode}.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    write_json(out / "summary.json", summaries)
    print("Saved", out)


if __name__ == "__main__":
    main()
